"""Durable queue, dispatcher, scheduler, and official SIWC guard tests."""

from __future__ import annotations

import json
import base64
import hashlib
import io
import os
import tempfile
import threading
import unittest
from argparse import Namespace
from contextlib import closing
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen
from unittest.mock import patch

from motor_editorial.db import SCHEMA_VERSION, Store
from motor_editorial.orchestration import (
    AgentProfile,
    AgentQueue,
    SimulatedExecutor,
    TaskDispatcher,
    TaskFailure,
    VALIDATION_PROFILE,
    run_simulated_chain,
)
from motor_editorial.orchestration_cli import PLUS_SCHEDULE_CONFIRMATION, _handle_scheduler
from motor_editorial.siwc import (
    API_BASE,
    AUTHORIZATION_ENDPOINT,
    CredentialStore,
    SIWCError,
    SIWCClient,
    SIWCExecutor,
    SIWC_PROBE_PROFILE,
    SIWC_PROBE_TASK_TYPE,
    TaskExecutionContext,
    _CallbackListener,
    _provider_code_failure,
    create_authorization_attempt,
    begin_login,
)


class FailOnceExecutor:
    executor_id = "fail-once"

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, task, profile, context):
        self.calls += 1
        if self.calls == 1:
            raise TaskFailure("temporary", "Falha transitória simulada.", retryable=True, retry_after_seconds=1)
        return {"ok": True, "attempt": self.calls}


class AlwaysTemporaryExecutor:
    executor_id = "always-temporary"

    def execute(self, task, profile, context):
        raise TaskFailure("temporary", "Falha transitória simulada.", retryable=True, retry_after_seconds=1)


class AgentOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = Store(self.root / "motor.sqlite3", self.root / "artifacts")
        self.queue = AgentQueue(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def enqueue(self, key="task-1", *, executor="simulated", profile=VALIDATION_PROFILE,
                available_at=None, **options):
        return self.queue.enqueue(
            task_type="validation.research", payload={"role": "researcher"},
            profile=profile, executor_id=executor, idempotency_key=key,
            available_at=available_at, **options,
        )

    def test_schema_v4_adds_queue_scheduler_and_event_tables(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 4)
        with closing(self.store.connect()) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row["name"] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        self.assertEqual(version, 4)
        self.assertTrue({"agent_tasks", "agent_task_events", "agent_schedules"}.issubset(tables))

    def test_simulated_chain_runs_rejection_correction_and_approval_without_network(self) -> None:
        with patch("socket.socket", side_effect=AssertionError("simulated chain attempted network I/O")):
            result = run_simulated_chain(self.queue)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["external_calls"], 0)
        self.assertEqual(len(result["task_ids"]), 5)
        self.assertEqual(result["profile"]["id"], VALIDATION_PROFILE.profile_id)
        self.assertEqual(result["profile"]["version"], VALIDATION_PROFILE.version)
        self.assertEqual(result["steps"][2]["approved"], False)
        self.assertEqual(result["steps"][4]["approved"], True)
        self.assertEqual([task.state for task in self.queue.list_tasks()], ["succeeded"] * 5)
        for task_id in result["task_ids"]:
            task = self.queue.get(task_id)
            self.assertEqual(task.profile_hash, VALIDATION_PROFILE.content_hash)
            self.assertEqual([event["action"] for event in self.queue.events(task_id)], [
                "enqueued", "claimed", "succeeded",
            ])

    def test_idempotency_returns_same_task_and_rejects_changed_payload(self) -> None:
        task_id = self.enqueue()
        self.assertEqual(self.enqueue(), task_id)
        with self.assertRaisesRegex(ValueError, "conteúdo diferente"):
            self.queue.enqueue(
                task_type="validation.research", payload={"role": "writer"},
                profile=VALIDATION_PROFILE, executor_id="simulated", idempotency_key="task-1",
            )

    def test_task_and_result_survive_reopening_sqlite_store(self) -> None:
        task_id = self.enqueue(key="persist-across-store")
        first_dispatcher = TaskDispatcher(
            self.queue,
            executors={"simulated": SimulatedExecutor()},
            profiles={(VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE},
        )
        self.assertEqual(first_dispatcher.dispatch_one(task_id).state, "succeeded")
        reopened_store = Store(self.root / "motor.sqlite3", self.root / "artifacts")
        persisted = AgentQueue(reopened_store).get(task_id)
        self.assertEqual(persisted.state, "succeeded")
        self.assertEqual(persisted.result["fictional"], True)
        self.assertEqual(persisted.profile_hash, VALIDATION_PROFILE.content_hash)

    def test_queue_rejects_structured_or_bearer_credentials_in_payloads(self) -> None:
        with self.assertRaisesRegex(ValueError, "Campo de credencial"):
            self.queue.enqueue(
                task_type="validation.research", payload={"access_token": "fixture"},
                profile=VALIDATION_PROFILE, executor_id="simulated", idempotency_key="secret-field",
            )
        with self.assertRaisesRegex(ValueError, "formato de credencial"):
            self.queue.enqueue(
                task_type="validation.research",
                payload={"context": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345"},
                profile=VALIDATION_PROFILE, executor_id="simulated", idempotency_key="secret-value",
            )

    def test_profile_version_hash_mismatch_blocks_dispatch(self) -> None:
        task_id = self.enqueue()
        altered = AgentProfile(
            profile_id=VALIDATION_PROFILE.profile_id,
            version=VALIDATION_PROFILE.version,
            instructions="Instruções diferentes para a mesma versão.",
        )
        dispatcher = TaskDispatcher(
            self.queue,
            executors={"simulated": SimulatedExecutor()},
            profiles={(altered.profile_id, altered.version): altered},
        )
        outcome = dispatcher.dispatch_one(task_id)
        self.assertEqual(outcome.state, "blocked")
        self.assertEqual(outcome.error_code, "profile_unavailable")
        self.assertEqual(self.queue.get(task_id).attempts, 1)

    def test_retryable_failure_waits_then_resumes_with_next_attempt(self) -> None:
        task_id = self.enqueue(key="retry", executor="fail-once")
        flaky = FailOnceExecutor()
        dispatcher = TaskDispatcher(
            self.queue,
            executors={"fail-once": flaky},
            profiles={(VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE},
        )
        first = dispatcher.dispatch_one(task_id)
        self.assertEqual(first.state, "retry_wait")
        persisted = self.queue.get(task_id)
        self.assertEqual(persisted.attempts, 1)
        self.assertEqual(dispatcher.dispatch_one(task_id).state, "idle")
        second = dispatcher.dispatch_one(task_id, now=persisted.available_at)
        self.assertEqual(second.state, "succeeded")
        self.assertEqual(self.queue.get(task_id).attempts, 2)
        self.assertEqual(self.queue.get(task_id).result, {"ok": True, "attempt": 2})

    def test_retry_limit_stops_the_durable_task(self) -> None:
        task_id = self.enqueue(key="retry-limit", executor="always-temporary", max_attempts=2)
        dispatcher = TaskDispatcher(
            self.queue,
            executors={"always-temporary": AlwaysTemporaryExecutor()},
            profiles={(VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE},
        )
        self.assertEqual(dispatcher.dispatch_one(task_id).state, "retry_wait")
        available_at = self.queue.get(task_id).available_at
        self.assertEqual(dispatcher.dispatch_one(task_id, now=available_at).state, "failed")
        persisted = self.queue.get(task_id)
        self.assertEqual(persisted.attempts, 2)
        self.assertEqual(persisted.state, "failed")

    def test_expired_lease_before_external_call_is_requeued_across_restart(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        task_id = self.enqueue(key="lease-safe", available_at=start)
        task = self.queue.claim_next(task_id=task_id, lease_seconds=10, now=start)
        self.assertEqual(task.state, "running")
        resumed = self.queue.claim_next(
            task_id=task_id, lease_seconds=10, now=start + timedelta(seconds=11)
        )
        self.assertEqual(resumed.state, "running")
        self.assertEqual(resumed.attempts, 2)
        self.assertEqual(self.queue.events(task_id)[-2]["action"], "lease_expired_requeued")

    def test_only_one_concurrent_worker_can_claim_a_ready_task(self) -> None:
        task_id = self.enqueue(key="single-claim")
        barrier = threading.Barrier(4)
        claimed: list[str | None] = []

        def worker() -> None:
            barrier.wait()
            task = self.queue.claim_next(task_id=task_id)
            claimed.append(task.task_id if task else None)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=5)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(claimed.count(task_id), 1)
        self.assertEqual(claimed.count(None), 2)

    def test_expired_lease_after_external_call_becomes_uncertain_and_is_not_replayed(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        task_id = self.enqueue(key="lease-uncertain", available_at=start)
        self.queue.claim_next(task_id=task_id, lease_seconds=5, now=start)
        self.queue.mark_external_started(task_id)
        next_task = self.queue.claim_next(now=start + timedelta(seconds=6))
        self.assertIsNone(next_task)
        task = self.queue.get(task_id)
        self.assertEqual(task.state, "uncertain")
        self.assertTrue(task.external_request_started)
        self.assertEqual(self.queue.events(task_id)[-1]["action"], "lease_expired_uncertain")

    def test_schedule_is_disabled_by_default_and_run_once_catches_up_once(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.queue.create_schedule(
            schedule_id="nightly", task_type="validation.research",
            payload={"role": "researcher"}, profile=VALIDATION_PROFILE,
            executor_id="simulated", interval_seconds=10,
            timezone_name="UTC", misfire_policy="run_once", start_at=base,
        )
        self.assertFalse(self.queue.list_schedules()[0]["enabled"])
        self.assertEqual(self.queue.scheduler_tick(now=base + timedelta(seconds=100)), [])
        self.queue.set_schedule_enabled("nightly", True, now=base)
        due = self.queue.scheduler_tick(now=base + timedelta(seconds=35))
        self.assertEqual(len(due), 1)
        self.assertEqual(self.queue.get(due[0]).schedule_id, "nightly")
        self.assertEqual(self.queue.scheduler_tick(now=base + timedelta(seconds=35)), [])
        self.assertEqual(self.queue.list_schedules()[0]["next_run_at"], "2026-01-01T00:00:40+00:00")

    def test_skip_misfire_advances_schedule_without_creating_task(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.queue.create_schedule(
            schedule_id="skip-late", task_type="validation.research",
            payload={"role": "researcher"}, profile=VALIDATION_PROFILE,
            executor_id="simulated", interval_seconds=10, misfire_policy="skip",
            enabled=True, start_at=base,
        )
        self.assertEqual(self.queue.scheduler_tick(now=base + timedelta(seconds=35)), [])
        self.assertEqual(self.queue.list_tasks(), [])
        self.assertEqual(self.queue.list_schedules()[0]["next_run_at"], "2026-01-01T00:00:40+00:00")

    def test_plus_schedule_requires_explicit_confirmation_and_worker_gate(self) -> None:
        self.queue.create_schedule(
            schedule_id="plus-probe", task_type=SIWC_PROBE_TASK_TYPE,
            payload={"model": "model-fixture"}, profile=SIWC_PROBE_PROFILE,
            executor_id="siwc-responses", interval_seconds=3600,
        )
        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaisesRegex(ValueError, "chamadas Plus recorrentes"):
                _handle_scheduler(Namespace(
                    scheduler_command="enable", schedule_id="plus-probe", confirm="",
                ), self.queue)
        self.assertFalse(self.queue.list_schedules()[0]["enabled"])
        with redirect_stdout(output):
            _handle_scheduler(Namespace(
                scheduler_command="enable", schedule_id="plus-probe",
                confirm=PLUS_SCHEDULE_CONFIRMATION,
            ), self.queue)
        self.assertTrue(self.queue.list_schedules()[0]["enabled"])
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "MOTOR_EDITORIAL_ALLOW_PLUS_SCHEDULING"):
                _handle_scheduler(Namespace(
                    scheduler_command="run", poll_seconds=1.0, max_cycles=0,
                ), self.queue)


class SIWCContractTests(unittest.TestCase):
    def test_pkce_authorization_url_uses_openai_official_endpoints_and_no_api_key(self) -> None:
        attempt = create_authorization_attempt(
            client_id="dynamic_agent_client", host_id="urn:uuid:01234567-89ab-cdef-0123-456789abcdef",
            redirect_uri="http://127.0.0.1:1455/auth/callback", is_new_registration=True,
        )
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(attempt.authorization_url())
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", AUTHORIZATION_ENDPOINT)
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["redirect_uri"], [attempt.redirect_uri])
        self.assertEqual(query["client_id"], ["dynamic_agent_client"])
        self.assertEqual(query["ext_agent_host_id"], [attempt.host_id])
        self.assertEqual(
            set(query["scope"][0].split()),
            {"openid", "profile", "email", "offline_access", "resource.invoke", "chatgpt.tokens.use.direct"},
        )
        self.assertNotIn("api_key", attempt.authorization_url())
        self.assertNotIn("client_secret", query)
        self.assertEqual(len(attempt.code_verifier), 64)
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(attempt.code_verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")
        self.assertEqual(query["code_challenge"], [expected_challenge])

    def test_credential_store_round_trip_and_private_file_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "tokens.bin"
            credentials = CredentialStore(path)
            with credentials.lock():
                credentials.save({"access_token": "fixture", "scopes": ["test"]})
                saved = credentials.load()
            self.assertEqual(saved["access_token"], "fixture")
            raw = path.read_bytes()
            if os.name == "nt":
                self.assertNotIn(b"fixture", raw)
            elif os.name == "posix":
                self.assertIn(b'"access_token":"fixture"', raw)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_expired_access_token_refreshes_serially_and_replaces_rotating_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            credentials = CredentialStore(Path(directory) / "tokens.bin")
            with credentials.lock():
                credentials.save({
                    "client_id": "oaiapp_fixture", "host_id": "urn:uuid:fixture",
                    "access_token": "old-access", "refresh_token": "old-refresh",
                    "id_token": "old-id", "expires_at": 1,
                    "scopes": ["chatgpt.tokens.use.direct", "offline_access"],
                })
            client = SIWCClient(credentials)

            def refresh(endpoint, fields, *, timeout=30):
                self.assertEqual(endpoint, "https://auth.openai.com/api/accounts/oauth/token")
                self.assertEqual(fields, {
                    "grant_type": "refresh_token", "client_id": "oaiapp_fixture",
                    "refresh_token": "old-refresh", "resource": "https://api.openai.com/v1",
                })
                return {
                    "access_token": "new-access", "refresh_token": "rotated-refresh",
                    "expires_in": 3600,
                }

            with patch("motor_editorial.siwc._post_form", side_effect=refresh):
                self.assertEqual(client.access_token(), "new-access")
            updated = credentials.load()
            self.assertEqual(updated["refresh_token"], "rotated-refresh")
            self.assertEqual(updated["id_token"], "old-id")

    def test_siwe_profile_is_internal_and_non_editorial(self) -> None:
        self.assertEqual(SIWC_PROBE_PROFILE.profile_id, "internal-siwc-integration-probe")
        self.assertIn("Não representa persona pública", SIWC_PROBE_PROFILE.instructions)
        self.assertEqual(SIWC_PROBE_TASK_TYPE, "siwc.integration_probe")
        self.assertTrue(API_BASE.startswith("https://api.openai.com/v1"))

    def test_plus_limit_and_ineligible_responses_are_blocked_not_retried(self) -> None:
        limit = _provider_code_failure("subscription_sharing_usage_limit_exceeded", status=429)
        self.assertTrue(limit.blocked)
        self.assertFalse(limit.retryable)
        ineligible = _provider_code_failure("subscription_sharing_user_not_eligible", status=403)
        self.assertTrue(ineligible.blocked)
        self.assertFalse(ineligible.retryable)
        unavailable = _provider_code_failure("subscription_sharing_usage_unavailable", status=503)
        self.assertTrue(unavailable.retryable)
        self.assertFalse(unavailable.blocked)

    def test_credential_store_does_not_accept_unrecognized_file_ciphertext(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokens.bin"
            path.write_bytes(b"not-an-siwc-file")
            with self.assertRaises(SIWCError):
                CredentialStore(path).load()

    def test_oauth_callback_requires_state_and_exchange_uses_returned_client_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            credentials = CredentialStore(Path(directory) / "siwc" / "tokens.bin")
            shown_url: list[str] = []
            outcome: dict[str, object] = {}
            failure: list[BaseException] = []

            def login_thread() -> None:
                try:
                    outcome.update(begin_login(
                        credentials, show_authorization_url=shown_url.append,
                        timeout_seconds=10,
                    ))
                except BaseException as error:
                    failure.append(error)

            def exchange(endpoint, fields, *, timeout=30):
                self.assertEqual(endpoint, "https://auth.openai.com/api/accounts/oauth/token")
                self.assertEqual(fields["grant_type"], "authorization_code")
                self.assertEqual(fields["client_id"], "oaiapp_test-client-id")
                self.assertEqual(fields["code"], "one-time-code")
                self.assertIn("code_verifier", fields)
                self.assertEqual(fields["redirect_uri"].split("/")[2].split(":")[0], "127.0.0.1")
                self.assertEqual(fields["resource"], "https://api.openai.com/v1")
                return {
                    "scope": "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct",
                    "access_token": "access-fixture", "refresh_token": "refresh-fixture",
                    "id_token": "signed-fixture", "expires_in": 3600,
                }

            thread = threading.Thread(target=login_thread, daemon=True)
            with patch("motor_editorial.siwc._post_form", side_effect=exchange), patch(
                "motor_editorial.siwc._validate_id_token", return_value={"sub": "subject-fixture"}
            ):
                thread.start()
                deadline = __import__("time").monotonic() + 5
                while not shown_url and __import__("time").monotonic() < deadline:
                    __import__("time").sleep(0.01)
                self.assertTrue(shown_url, "login did not provide its authorization URL")
                query = parse_qs(urlparse(shown_url[0]).query)
                redirect = urlparse(query["redirect_uri"][0])
                callback_url = (
                    f"http://{redirect.netloc}{redirect.path}?code=one-time-code"
                    f"&state={query['state'][0]}&client_id=oaiapp_test-client-id"
                )
                with urlopen(callback_url, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(failure, [])
            self.assertTrue(outcome["authenticated"])
            self.assertTrue(outcome["granted_direct_usage"])
            stored = credentials.load()
            self.assertEqual(stored["client_id"], "oaiapp_test-client-id")
            self.assertEqual(stored["subject"], "subject-fixture")
            self.assertNotIn("email", stored)

    def test_responses_executor_sends_only_supported_nonstored_stream_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = SIWCClient(CredentialStore(Path(directory) / "tokens.bin"))
            with patch.object(client, "access_token", return_value="oauth-fixture-token"):
                queue_store = Store(Path(directory) / "motor.sqlite3", Path(directory) / "artifacts")
                queue = AgentQueue(queue_store)
                task_id = queue.enqueue(
                    task_type=SIWC_PROBE_TASK_TYPE,
                    payload={"model": "model-fixture"},
                    profile=SIWC_PROBE_PROFILE, executor_id="siwc-responses",
                    idempotency_key="siwc-contract-probe", max_attempts=1,
                )
                task = queue.claim_next(task_id=task_id)
                context = TaskExecutionContext(queue, task_id)

                class FakeResponse:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        return False

                    def __iter__(self):
                        fragments = [
                            '{"status":"ok","message":"teste de integra',
                            'ção aprovado"}',
                        ]
                        rows = [
                            "data: " + json.dumps({
                                "type": "response.output_text.delta", "delta": fragment,
                            }, ensure_ascii=False) + "\n"
                            for fragment in fragments
                        ]
                        rows.append("data: " + json.dumps({
                            "type": "response.completed",
                            "response": {"id": "resp_fixture", "usage": {"total_tokens": 7}},
                        }) + "\n")
                        return iter(row.encode("utf-8") for row in rows)

                def fake_urlopen(request, timeout):
                    self.assertEqual(request.full_url, f"{API_BASE}/responses")
                    self.assertEqual(request.get_header("Authorization"), "Bearer oauth-fixture-token")
                    body = json.loads(request.data.decode("utf-8"))
                    self.assertEqual(body["model"], "model-fixture")
                    self.assertFalse(body["store"])
                    self.assertTrue(body["stream"])
                    self.assertEqual(body["input"][0]["role"], "user")
                    self.assertNotIn("max_output_tokens", body)
                    self.assertNotIn("tools", body)
                    return FakeResponse()

                with patch("motor_editorial.siwc.urllib.request.urlopen", side_effect=fake_urlopen):
                    result = SIWCExecutor(client, model=None).execute(
                        task, SIWC_PROBE_PROFILE, context
                    )
                self.assertTrue(context.external_request_started)
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["response_id"], "resp_fixture")

    def test_responses_transport_failure_is_uncertain_and_never_auto_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = SIWCClient(CredentialStore(Path(directory) / "tokens.bin"))
            with patch.object(client, "access_token", return_value="oauth-fixture-token"):
                context = type("Context", (), {"mark_external_started": lambda self: setattr(self, "started", True)})()
                with patch("motor_editorial.siwc.urllib.request.urlopen", side_effect=OSError("private transport detail")):
                    with self.assertRaises(TaskFailure) as raised:
                        client.inference_stream("model-fixture", context)
                self.assertTrue(raised.exception.uncertain)
                self.assertFalse(raised.exception.retryable)
                self.assertNotIn("private transport detail", raised.exception.summary)

    def test_signed_id_token_verification_checks_audience_issuer_and_nonce(self) -> None:
        try:
            import jwt
            from cryptography.hazmat.primitives.asymmetric import rsa
        except ImportError:
            self.skipTest("PyJWT[crypto] opcional ainda não está instalado")
        from motor_editorial.siwc import _validate_id_token

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode({
            "iss": "https://auth.openai.com", "aud": "oaiapp_test-client-id",
            "sub": "subject-fixture", "nonce": "nonce-fixture",
            "iat": int(__import__("time").time()), "exp": int(__import__("time").time()) + 300,
        }, private_key, algorithm="RS256", headers={"kid": "fixture-key"})
        public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
        public_jwk["kid"] = "fixture-key"

        class FakeSigningKey:
            key = private_key.public_key()

        class FakeJwks:
            def __init__(self, uri, timeout=0):
                self.uri = uri

            def get_signing_key_from_jwt(self, value):
                self_test.assertEqual(self.uri, "https://auth.openai.com/.well-known/jwks.json")
                return FakeSigningKey()

        self_test = self
        with patch("jwt.PyJWKClient", FakeJwks):
            claims = _validate_id_token(token, "oaiapp_test-client-id", "nonce-fixture")
            self.assertEqual(claims["sub"], "subject-fixture")
            with self.assertRaises(SIWCError):
                _validate_id_token(token, "oaiapp_test-client-id", "different-nonce")


if __name__ == "__main__":
    unittest.main()
