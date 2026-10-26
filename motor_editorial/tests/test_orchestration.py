"""Durable queue, dispatcher, scheduler, and official SIWC guard tests."""

from __future__ import annotations

import json
import base64
import hashlib
import io
import os
import sqlite3
import tempfile
import threading
import time
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
from motor_editorial.cli import _build_parser
from motor_editorial.orchestration import (
    AgentProfile,
    AgentQueue,
    SchedulerWorker,
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
    SIWC_REASONING_EFFORTS,
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

    def test_task_dependencies_wait_for_success_and_do_not_block_independent_work(self) -> None:
        parent_id = self.enqueue(key="dependency-parent")
        child_id = self.queue.enqueue(
            task_type="validation.child", payload={"role": "writer"},
            profile=VALIDATION_PROFILE, executor_id="simulated",
            idempotency_key="dependency-child", dependencies=(parent_id,),
        )
        independent_id = self.enqueue(key="dependency-independent")

        self.assertEqual(self.queue.dependencies(child_id), (parent_id,))
        self.assertIsNone(self.queue.claim_next(task_id=child_id))
        independent = self.queue.claim_next(task_id=independent_id)
        self.assertIsNotNone(independent)
        self.assertTrue(self.queue.complete(
            independent.task_id, independent.lease_owner, independent.lease_generation,
            {"ok": True},
        ))
        parent = self.queue.claim_next(task_id=parent_id)
        self.assertIsNotNone(parent)
        self.assertTrue(self.queue.complete(
            parent.task_id, parent.lease_owner, parent.lease_generation, {"ok": True},
        ))
        child = self.queue.claim_next(task_id=child_id)
        self.assertIsNotNone(child)
        self.assertEqual(child.state, "running")

    def test_failed_dependency_blocks_child_but_preserves_independent_task(self) -> None:
        parent_id = self.enqueue(key="failed-dependency-parent")
        child_id = self.queue.enqueue(
            task_type="validation.child", payload={"role": "writer"},
            profile=VALIDATION_PROFILE, executor_id="simulated",
            idempotency_key="failed-dependency-child", dependencies=(parent_id,),
        )
        independent_id = self.enqueue(key="failed-dependency-independent")
        parent = self.queue.claim_next(task_id=parent_id)
        self.assertEqual(self.queue.fail(
            parent_id, parent.lease_owner, parent.lease_generation,
            TaskFailure("fixture_blocked", "fixture blocked", blocked=True),
        ), "blocked")

        self.assertIsNone(self.queue.claim_next(task_id=child_id))
        self.assertEqual(self.queue.get(child_id).state, "blocked")
        self.assertEqual(self.queue.events(child_id)[-1]["action"], "dependency_blocked")
        independent = self.queue.claim_next(task_id=independent_id)
        self.assertIsNotNone(independent)

    def test_completed_external_response_can_be_adopted_without_retry_after_envelope_bug(self) -> None:
        task_id = self.enqueue(key="recover-completed-provider-output", max_attempts=1)
        claimed = self.queue.claim_next(task_id=task_id)
        self.assertIsNotNone(claimed)
        self.assertTrue(self.queue.mark_external_started(task_id, claimed.lease_owner, claimed.lease_generation))
        self.assertEqual(self.queue.fail(
            task_id, claimed.lease_owner, claimed.lease_generation,
            TaskFailure("siwc_result_envelope_invalid", "Local envelope adapter rejected a completed response.", blocked=True),
        ), "blocked")
        response_hash = "d" * 64
        result = {
            "artifact_ref": {"ref": "private://response.json", "sha256": response_hash},
            "output_hash": response_hash,
            "status": "completed",
        }

        self.assertTrue(self.queue.recover_completed_external_output(
            task_id, result, response_sha256=response_hash,
        ))
        recovered = self.queue.get(task_id)
        self.assertEqual(recovered.state, "succeeded")
        self.assertEqual(recovered.attempts, 1)
        self.assertEqual(recovered.result, result)
        event = self.queue.events(task_id)[-1]
        self.assertEqual(event["action"], "external_output_recovered")
        self.assertEqual(event["detail"]["response_sha256"], response_hash)
        child_id = self.queue.enqueue(
            task_type="validation.child", payload={"role": "writer"},
            profile=VALIDATION_PROFILE, executor_id="simulated",
            idempotency_key="recover-completed-provider-child", dependencies=(task_id,),
        )
        self.assertIsNotNone(self.queue.claim_next(task_id=child_id))

    def test_completed_external_output_recovery_requires_exact_response_hash(self) -> None:
        response_hash = "e" * 64
        with self.assertRaisesRegex(ValueError, "hash exato"):
            self.queue.recover_completed_external_output(
                "missing-task", {"artifact_ref": {"ref": "private://x", "sha256": response_hash},
                                 "output_hash": "f" * 64},
                response_sha256=response_hash,
            )

    def test_dependency_idempotency_missing_edges_and_cycle_guard(self) -> None:
        first_id = self.enqueue(key="dependency-cycle-first")
        second_id = self.queue.enqueue(
            task_type="validation.child", payload={"role": "writer"},
            profile=VALIDATION_PROFILE, executor_id="simulated",
            idempotency_key="dependency-cycle-second",
        )
        self.assertTrue(self.queue.add_dependency(second_id, first_id))
        self.assertFalse(self.queue.add_dependency(second_id, first_id))
        self.assertEqual(self.queue.dependencies(second_id), (first_id,))
        with self.assertRaisesRegex(ValueError, "ciclo"):
            self.queue.add_dependency(first_id, second_id)
        with self.assertRaisesRegex(ValueError, "si mesma"):
            self.queue.add_dependency(first_id, first_id)
        with self.assertRaisesRegex(ValueError, "ausente"):
            self.queue.add_dependency(first_id, "missing-task")
        self.assertEqual(self.queue.enqueue(
            task_type="validation.child", payload={"role": "writer"},
            profile=VALIDATION_PROFILE, executor_id="simulated",
            idempotency_key="dependency-cycle-second", dependencies=(first_id,),
        ), second_id)
        with self.assertRaisesRegex(ValueError, "dependências diferentes"):
            self.queue.enqueue(
                task_type="validation.child", payload={"role": "writer"},
                profile=VALIDATION_PROFILE, executor_id="simulated",
                idempotency_key="dependency-cycle-second",
            )

    def test_schema_v7_adds_durable_task_dependencies_to_existing_queue(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 7)
        with closing(self.store.connect()) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row["name"] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        self.assertEqual(version, 7)
        with closing(self.store.connect()) as connection:
            task_columns = {
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(agent_tasks)"
                ).fetchall()
            }
        self.assertTrue({"agent_tasks", "agent_task_events", "agent_task_dependencies", "agent_schedules"}.issubset(tables))
        self.assertTrue({"lease_owner", "lease_generation"}.issubset(task_columns))
        with closing(self.store.connect()) as connection:
            schedule_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(agent_schedules)")
            }
        self.assertTrue({
            "schedule_group_id", "schedule_kind", "local_time", "misfire_grace_seconds",
            "domain_quotas_json", "dry_run",
        }.issubset(schedule_columns))

    def test_v4_database_is_migrated_with_lease_fence_columns(self) -> None:
        legacy_path = self.root / "schema-v4.sqlite3"
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.execute("""CREATE TABLE agent_tasks (
                id TEXT PRIMARY KEY, task_type TEXT NOT NULL, payload_json TEXT NOT NULL,
                profile_id TEXT NOT NULL, profile_version TEXT NOT NULL,
                profile_hash TEXT NOT NULL, executor_id TEXT NOT NULL, state TEXT NOT NULL,
                idempotency_key TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3, created_at TEXT NOT NULL,
                available_at TEXT NOT NULL, lease_until TEXT, started_at TEXT,
                completed_at TEXT, external_request_started INTEGER NOT NULL DEFAULT 0,
                error_code TEXT, error_summary TEXT, result_json TEXT, schedule_id TEXT
            )""")
            connection.execute("PRAGMA user_version = 4")
            connection.commit()
        migrated = Store(legacy_path, self.root / "schema-v4-artifacts")
        with closing(migrated.connect()) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            columns = {
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(agent_tasks)"
                ).fetchall()
            }
        self.assertEqual(version, 7)
        self.assertTrue({"lease_owner", "lease_generation"}.issubset(columns))

    def test_v5_database_migrates_existing_interval_schedule_rows_additively(self) -> None:
        legacy_path = self.root / "schema-v5.sqlite3"
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.execute("""CREATE TABLE agent_schedules (
                id TEXT PRIMARY KEY, task_type TEXT NOT NULL, payload_json TEXT NOT NULL,
                profile_id TEXT NOT NULL, profile_version TEXT NOT NULL, profile_hash TEXT NOT NULL,
                executor_id TEXT NOT NULL, interval_seconds INTEGER NOT NULL,
                timezone TEXT NOT NULL DEFAULT 'UTC', misfire_policy TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0, next_run_at TEXT NOT NULL,
                last_enqueued_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            connection.execute(
                """INSERT INTO agent_schedules
                   VALUES ('legacy-interval','validation.research','{}','validation','1','hash',
                           'simulated',60,'UTC','skip',0,'2026-01-01T00:00:00+00:00',NULL,
                           'created','updated')"""
            )
            connection.execute("PRAGMA user_version = 5")
            connection.commit()
        migrated = Store(legacy_path, self.root / "schema-v5-artifacts")
        with closing(migrated.connect()) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 7)
            row = connection.execute(
                "SELECT * FROM agent_schedules WHERE id='legacy-interval'"
            ).fetchone()
            columns = {item["name"] for item in connection.execute("PRAGMA table_info(agent_schedules)")}
        self.assertEqual(row["schedule_kind"], "interval")
        self.assertEqual(row["dry_run"], 1)
        self.assertIsNone(row["schedule_group_id"])
        self.assertTrue({"schedule_group_id", "schedule_kind", "local_time", "domain_quotas_json", "dry_run"} <= columns)

    def test_v6_database_migrates_task_dependency_ledger_additively(self) -> None:
        with closing(self.store.connect()) as connection:
            connection.execute("DROP TABLE agent_task_dependencies")
            connection.execute("PRAGMA user_version = 6")
            connection.commit()
        migrated = Store(self.root / "motor.sqlite3", self.root / "artifacts")
        with closing(migrated.connect()) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            columns = {
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(agent_task_dependencies)"
                ).fetchall()
            }
        self.assertEqual(version, 7)
        self.assertEqual(columns, {"task_id", "depends_on_task_id", "created_at"})

    def test_v3_migration_preserves_records_and_backup_restores_the_legacy_database(self) -> None:
        legacy_path = self.root / "schema-v3.sqlite3"
        backup_path = self.root / "schema-v3-backup.sqlite3"
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.executescript("""
                CREATE TABLE runs (
                    id TEXT PRIMARY KEY,
                    scenario_label TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN (
                        'running', 'recoverable_failure', 'failed_intervention',
                        'awaiting_approval', 'approved_internally'
                    )),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE stories (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    topic_key TEXT NOT NULL,
                    question TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN (
                        'selected', 'researched', 'drafted', 'blocked_by_review',
                        'corrected', 'reviewed', 'media_checked',
                        'awaiting_human_approval', 'approved_internally'
                    )),
                    current_revision_number INTEGER NOT NULL DEFAULT 0,
                    processing_status TEXT NOT NULL DEFAULT 'in_progress',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(run_id, topic_key)
                );
                CREATE TABLE editions (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    status TEXT NOT NULL CHECK (status IN (
                        'awaiting_human_approval', 'approved_internally'
                    )),
                    preview_path TEXT NOT NULL,
                    composition_status TEXT NOT NULL DEFAULT 'legacy_v1' CHECK (
                        composition_status IN (
                            'legacy_v1', 'preparing', 'waiting_on_blockers',
                            'ready_for_approval', 'approved_internally'
                        )
                    ),
                    composition_fingerprint TEXT,
                    approved_by TEXT,
                    approved_at TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(run_id)
                );
                CREATE TABLE edition_stories (
                    edition_id TEXT NOT NULL REFERENCES editions(id),
                    story_id TEXT NOT NULL REFERENCES stories(id),
                    position INTEGER NOT NULL,
                    required INTEGER NOT NULL DEFAULT 1 CHECK (required IN (0, 1)),
                    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                    exclusion_reason TEXT,
                    excluded_by TEXT,
                    excluded_at TEXT,
                    PRIMARY KEY (edition_id, story_id),
                    UNIQUE(edition_id, position)
                );
                INSERT INTO runs VALUES (
                    'legacy-run', 'fixture v3', 'awaiting_approval', 'created-v3', 'updated-v3'
                );
                INSERT INTO stories VALUES (
                    'legacy-story', 'legacy-run', 'legacy-topic', 'legacy question',
                    'awaiting_human_approval', 3, 'completed', 'story-created-v3', 'story-updated-v3'
                );
                INSERT INTO editions VALUES (
                    'legacy-edition', 'legacy-run', 'awaiting_human_approval',
                    'preview/legacy.html', 'ready_for_approval', 'fingerprint-v3',
                    NULL, NULL, 'edition-created-v3'
                );
                INSERT INTO edition_stories VALUES (
                    'legacy-edition', 'legacy-story', 1, 1, 1, NULL, NULL, NULL
                );
                PRAGMA user_version = 3;
            """)

        def snapshot(path: Path) -> dict[str, list[tuple[object, ...]]]:
            with closing(sqlite3.connect(path)) as connection:
                return {
                    table: connection.execute(
                        f"SELECT * FROM {table} ORDER BY rowid"
                    ).fetchall()
                    for table in ("runs", "stories", "editions", "edition_stories")
                }

        original_rows = snapshot(legacy_path)
        backup_path.write_bytes(legacy_path.read_bytes())
        backup_hash = hashlib.sha256(backup_path.read_bytes()).hexdigest()

        migrated = Store(legacy_path, self.root / "schema-v3-artifacts")
        with closing(migrated.connect()) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 7)
            tables = {
                row["name"] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            task_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(agent_tasks)")
            }
            foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        self.assertEqual(snapshot(legacy_path), original_rows)
        self.assertTrue({"agent_tasks", "agent_task_events", "agent_schedules"}.issubset(tables))
        self.assertTrue({"lease_owner", "lease_generation"}.issubset(task_columns))
        self.assertEqual(foreign_key_violations, [])

        # Roll back by restoring the isolated backup after every DB connection is closed.
        legacy_path.write_bytes(backup_path.read_bytes())
        self.assertEqual(snapshot(legacy_path), original_rows)
        with closing(sqlite3.connect(legacy_path)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
        self.assertEqual(hashlib.sha256(backup_path.read_bytes()).hexdigest(), backup_hash)

    def test_newer_schema_is_rejected_without_mutating_the_database(self) -> None:
        future_path = self.root / "schema-v8.sqlite3"
        with closing(sqlite3.connect(future_path)) as connection:
            connection.execute("CREATE TABLE future_records (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("INSERT INTO future_records VALUES ('kept', 'future data')")
            connection.execute("PRAGMA user_version = 8")
            connection.commit()
        original_bytes = future_path.read_bytes()

        with self.assertRaisesRegex(RuntimeError, "mais novo"):
            Store(future_path, self.root / "schema-v8-artifacts")

        self.assertEqual(future_path.read_bytes(), original_bytes)

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
        before_retry = (
            datetime.fromisoformat(persisted.available_at) - timedelta(microseconds=1)
        )
        self.assertEqual(dispatcher.dispatch_one(task_id, now=before_retry).state, "idle")
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

    def test_owner_renews_past_ttl_while_second_worker_cannot_claim(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        task_id = self.enqueue(key="lease-renewed", available_at=start)
        owner_a = self.queue.claim_next(task_id=task_id, lease_seconds=5, now=start)
        self.assertTrue(self.queue.renew_lease(
            task_id, owner_a.lease_owner, owner_a.lease_generation,
            lease_seconds=5, now=start + timedelta(seconds=4),
        ))

        owner_b = self.queue.claim_next(
            task_id=task_id, lease_seconds=5, now=start + timedelta(seconds=6)
        )
        self.assertIsNone(owner_b)
        self.assertEqual(self.queue.get(task_id).state, "running")
        self.assertTrue(self.queue.complete(
            task_id, owner_a.lease_owner, owner_a.lease_generation, {"owner": "A"},
            now=start + timedelta(seconds=8),
        ))
        completed = self.queue.get(task_id)
        self.assertEqual(completed.state, "succeeded")
        self.assertEqual(completed.result, {"owner": "A"})
        self.assertEqual(completed.lease_owner, None)
        self.assertEqual(completed.lease_generation, 1)
        event_dump = json.dumps(self.queue.events(task_id), ensure_ascii=False)
        self.assertNotIn(owner_a.lease_owner, event_dump)
        self.assertNotIn(owner_a.lease_owner, repr(owner_a))

    def test_stale_owner_cannot_complete_fail_or_mark_reclaimed_task(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        task_id = self.enqueue(key="lease-fenced", available_at=start)
        owner_a = self.queue.claim_next(task_id=task_id, lease_seconds=3, now=start)
        owner_b = self.queue.claim_next(
            task_id=task_id, lease_seconds=10, now=start + timedelta(seconds=4)
        )
        self.assertEqual(owner_b.lease_generation, owner_a.lease_generation + 1)
        self.assertNotEqual(owner_b.lease_owner, owner_a.lease_owner)
        self.assertFalse(self.queue.renew_lease(
            task_id, owner_a.lease_owner, owner_a.lease_generation,
            lease_seconds=10, now=start + timedelta(seconds=5),
        ))
        self.assertFalse(self.queue.mark_external_started(
            task_id, owner_a.lease_owner, owner_a.lease_generation,
            now=start + timedelta(seconds=5),
        ))
        self.assertFalse(self.queue.complete(
            task_id, owner_a.lease_owner, owner_a.lease_generation, {"stale": True},
            now=start + timedelta(seconds=5),
        ))
        self.assertIsNone(self.queue.fail(
            task_id, owner_a.lease_owner, owner_a.lease_generation,
            TaskFailure("stale", "Owner antigo."), now=start + timedelta(seconds=5),
        ))
        still_owned = self.queue.get(task_id)
        self.assertEqual(still_owned.state, "running")
        self.assertEqual(still_owned.lease_owner, owner_b.lease_owner)
        self.assertTrue(self.queue.complete(
            task_id, owner_b.lease_owner, owner_b.lease_generation, {"owner": "B"},
            now=start + timedelta(seconds=6),
        ))
        self.assertEqual(self.queue.get(task_id).result, {"owner": "B"})

    def test_dispatcher_heartbeat_keeps_long_executor_owned_past_ttl(self) -> None:
        task_id = self.enqueue(key="dispatcher-heartbeat", executor="slow")
        started = threading.Event()
        release = threading.Event()
        heartbeat_renewed = threading.Event()
        renewal_observations: list[tuple[float, bool | str]] = []
        lease_seconds = 6
        lease_started_at = datetime.now(timezone.utc)
        original_claim_next = self.queue.claim_next
        original_renew_lease = self.queue.renew_lease

        def claim_at_test_time(
            *,
            task_id: str | None = None,
            lease_seconds: int = 120,
            now: datetime | str | None = None,
        ):
            effective_now = lease_started_at if now is None else now
            return original_claim_next(
                task_id=task_id, lease_seconds=lease_seconds, now=effective_now,
            )

        self.queue.claim_next = claim_at_test_time  # type: ignore[method-assign]

        def observe_renewal(
            renewed_task_id: str,
            lease_owner: str,
            lease_generation: int,
            *,
            lease_seconds: int,
            now: datetime | str | None = None,
        ) -> bool:
            attempt_at = time.monotonic()
            try:
                renewed = original_renew_lease(
                    renewed_task_id, lease_owner, lease_generation,
                    lease_seconds=lease_seconds, now=now,
                )
            except Exception as error:
                renewal_observations.append((attempt_at, type(error).__name__))
                raise
            renewal_observations.append((attempt_at, renewed))
            if renewed:
                heartbeat_renewed.set()
            return renewed

        self.queue.renew_lease = observe_renewal  # type: ignore[method-assign]

        class SlowExecutor:
            executor_id = "slow"

            def execute(self, task, profile, context):
                started.set()
                if not release.wait(timeout=12):
                    raise AssertionError("test did not release slow executor")
                return {"ok": True}

        dispatcher = TaskDispatcher(
            self.queue, executors={"slow": SlowExecutor()},
            profiles={(VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE},
            lease_seconds=lease_seconds,
        )
        outcome: list[Any] = []
        worker = threading.Thread(target=lambda: outcome.append(dispatcher.dispatch_one(task_id)))
        worker.start()
        try:
            self.assertTrue(started.wait(timeout=2))
            self.assertTrue(
                heartbeat_renewed.wait(timeout=5.5),
                f"heartbeat did not renew before TTL: {renewal_observations}",
            )
            # Compete just beyond the original deadline while the live heartbeat owns an extension.
            competitor_time = lease_started_at + timedelta(
                seconds=lease_seconds, milliseconds=100,
            )
            second_worker = self.queue.claim_next(
                task_id=task_id, lease_seconds=lease_seconds, now=competitor_time,
            )
            self.assertIsNone(second_worker)
        finally:
            release.set()
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertTrue(any(result is True for _, result in renewal_observations))
        self.assertEqual(outcome[0].state, "succeeded", renewal_observations)
        self.assertEqual(self.queue.get(task_id).result, {"ok": True})

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
        task = self.queue.claim_next(task_id=task_id, lease_seconds=5, now=start)
        self.assertTrue(self.queue.mark_external_started(
            task_id, task.lease_owner, task.lease_generation, now=start
        ))
        next_task = self.queue.claim_next(now=start + timedelta(seconds=6))
        self.assertIsNone(next_task)
        task = self.queue.get(task_id)
        self.assertEqual(task.state, "uncertain")
        self.assertTrue(task.external_request_started)
        self.assertEqual(self.queue.events(task_id)[-1]["action"], "lease_expired_uncertain")
        self.assertFalse(self.queue.complete(
            task_id, "stale-owner", 1, {"late": True}, now=start + timedelta(seconds=7)
        ))
        self.assertEqual(self.queue.get(task_id).state, "uncertain")

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

    def test_three_daily_local_windows_are_utc_persisted_disabled_and_deduplicated(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ids = self.queue.create_daily_window_set(
            schedule_group_id="radar-main", task_type="radar.general.scan",
            payload={"source_ids": ["fixture-source"]}, profile=VALIDATION_PROFILE,
            executor_id="simulated", local_times=["08:00", "14:00", "20:00"],
            domain_quotas={"news.example.invalid": 8},
            timezone_name="America/Sao_Paulo", misfire_policy="run_once",
            start_at=base,
        )
        self.assertEqual(len(ids), 3)
        schedules = self.queue.list_schedules()
        self.assertTrue(all(not row["enabled"] for row in schedules))
        self.assertTrue(all(row["schedule_kind"] == "daily_window" for row in schedules))
        self.assertTrue(all(row["dry_run"] for row in schedules))
        self.assertEqual(
            {row["next_run_at"] for row in schedules},
            {"2026-01-01T11:00:00+00:00", "2026-01-01T17:00:00+00:00", "2026-01-01T23:00:00+00:00"},
        )
        self.assertEqual(self.queue.scheduler_tick(now=base + timedelta(days=2)), [])

        self.queue.set_schedule_group_enabled("radar-main", True, now=base)
        first_due = datetime(2026, 1, 1, 11, tzinfo=timezone.utc)
        task_ids = self.queue.scheduler_tick(now=first_due)
        self.assertEqual(len(task_ids), 1)
        task = self.queue.get(task_ids[0])
        self.assertEqual(task.schedule_id, "radar-main:0800")  # type: ignore[union-attr]
        policy = task.payload["radar_collection_policy"]  # type: ignore[union-attr]
        self.assertEqual(policy["timezone"], "America/Sao_Paulo")
        self.assertEqual(policy["domain_quotas"], {"news.example.invalid": 8})
        self.assertEqual(policy["quota_period"], "local_day")
        self.assertTrue(policy["dry_run"])
        self.assertEqual(self.queue.scheduler_tick(now=first_due), [])

    def test_daily_windows_accept_four_to_six_and_reject_bad_config_atomically(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)

        def add(group: str, times: list[str]) -> list[str]:
            return self.queue.create_daily_window_set(
                schedule_group_id=group, task_type="radar.general.scan", payload={},
                profile=VALIDATION_PROFILE, executor_id="simulated", local_times=times,
                domain_quotas={"example.invalid": 2}, start_at=base,
            )

        self.assertEqual(len(add("four-windows", ["05:00", "11:00", "17:00", "23:00"])), 4)
        self.assertEqual(len(add("six-windows", ["04:00", "08:00", "12:00", "16:00", "20:00", "23:00"])), 6)
        initial_count = len(self.queue.list_schedules())
        for group, times in (
            ("too-few", ["08:00", "16:00"]),
            ("too-many", ["01:00", "05:00", "09:00", "13:00", "17:00", "21:00", "23:00"]),
            ("duplicate", ["08:00", "08:00", "16:00"]),
            ("invalid-time", ["08:00", "24:00", "16:00"]),
        ):
            with self.subTest(group=group), self.assertRaises(ValueError):
                add(group, times)
        self.assertEqual(len(self.queue.list_schedules()), initial_count)

    def test_daily_windows_cli_creates_disabled_dry_run_group(self) -> None:
        args = _build_parser().parse_args([
            "scheduler", "windows-add", "radar-cli", "radar.general.scan",
            "--times", "07:00", "13:00", "19:00",
            "--domain-quota", "example.invalid=3",
            "--payload", '{"source_ids":["synthetic"]}',
        ])
        output = io.StringIO()
        with redirect_stdout(output):
            result = _handle_scheduler(args, self.queue)
        self.assertEqual(result, 0)
        body = json.loads(output.getvalue())
        self.assertEqual(body["schedule_group_id"], "radar-cli")
        self.assertFalse(body["enabled"])
        self.assertTrue(body["dry_run"])
        self.assertEqual(len(body["schedule_ids"]), 3)
        self.assertTrue(all(not row["enabled"] for row in self.queue.list_schedules()))

    def test_daily_skip_misfire_and_pause_resume_skip_paused_windows(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.queue.create_daily_window_set(
            schedule_group_id="skip-daily", task_type="radar.general.scan", payload={},
            profile=VALIDATION_PROFILE, executor_id="simulated",
            local_times=["08:00", "14:00", "20:00"],
            domain_quotas={"example.invalid": 5}, misfire_policy="skip",
            misfire_grace_seconds=300, start_at=base,
        )
        self.queue.set_schedule_group_enabled("skip-daily", True, now=base)
        overdue = datetime(2026, 1, 1, 11, 10, tzinfo=timezone.utc)
        self.assertEqual(self.queue.scheduler_tick(now=overdue), [])
        self.assertEqual(self.queue.list_tasks(), [])
        morning = next(row for row in self.queue.list_schedules() if row["local_time"] == "08:00")
        self.assertEqual(morning["next_run_at"], "2026-01-02T11:00:00+00:00")

        paused = self.queue.set_schedule_group_enabled("skip-daily", False, now=overdue)
        self.assertEqual(len(paused), 3)
        self.assertTrue(all(not row["enabled"] for row in self.queue.list_schedules()))
        resumed = self.queue.set_schedule_group_enabled(
            "skip-daily", True, now=datetime(2026, 1, 3, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(len(resumed), 3)
        self.assertEqual(self.queue.scheduler_tick(now=datetime(2026, 1, 3, 12, tzinfo=timezone.utc)), [])
        self.assertTrue(all(row["next_run_at"] > "2026-01-03T12:00:00+00:00" for row in self.queue.list_schedules()))

    def test_daily_run_once_recovers_one_task_per_missed_window_without_duplicates(self) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.queue.create_daily_window_set(
            schedule_group_id="recover-daily", task_type="radar.general.scan", payload={},
            profile=VALIDATION_PROFILE, executor_id="simulated",
            local_times=["08:00", "14:00", "20:00"],
            domain_quotas={"example.invalid": 5}, misfire_policy="run_once",
            start_at=base,
        )
        self.queue.set_schedule_group_enabled("recover-daily", True, now=base)
        recovery = datetime(2026, 1, 4, 2, tzinfo=timezone.utc)
        task_ids = self.queue.scheduler_tick(now=recovery)
        self.assertEqual(len(task_ids), 3)
        self.assertEqual(self.queue.scheduler_tick(now=recovery), [])
        self.assertEqual(len(self.queue.list_tasks()), 3)
        self.assertTrue(all(row["next_run_at"] > recovery.isoformat() for row in self.queue.list_schedules()))

    def test_empty_scheduler_poll_does_not_call_executor(self) -> None:
        class CountingExecutor:
            executor_id = "counting"

            def __init__(self) -> None:
                self.calls = 0

            def execute(self, task, profile, context):
                self.calls += 1
                return {"unexpected": True}

        executor = CountingExecutor()
        dispatcher = TaskDispatcher(
            self.queue, executors={"counting": executor},
            profiles={(VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE},
        )
        SchedulerWorker(self.queue, dispatcher, poll_seconds=0.001).run(max_cycles=1)
        self.assertEqual(executor.calls, 0)

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
    def test_models_catalog_request_is_timed_with_offline_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = SIWCClient(CredentialStore(Path(directory) / "tokens.bin"))
            fixture = json.dumps({"models": [{
                "slug": "gpt-6-luna", "display_name": "Luna", "visibility": "list",
            }]}).encode("utf-8")
            with patch.object(client, "_request", return_value=fixture) as request:
                models = client.models()
        request.assert_called_once_with("GET", f"{API_BASE}/models")
        self.assertEqual(models[0]["slug"], "gpt-6-luna")
        self.assertEqual(client.models_request_count, 1)
        self.assertIsInstance(client.last_models_request_metrics, dict)
        self.assertGreaterEqual(client.last_models_request_metrics["duration_ms"], 0)
        self.assertIn("started_at", client.last_models_request_metrics)
        self.assertIn("completed_at", client.last_models_request_metrics)

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
                    payload={"model": "model-fixture", "reasoning_effort": "max"},
                    profile=SIWC_PROBE_PROFILE, executor_id="siwc-responses",
                    idempotency_key="siwc-contract-probe", max_attempts=1,
                )
                task = queue.claim_next(task_id=task_id)
                context = TaskExecutionContext(queue, task, lease_seconds=120)

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
                            "response": {
                                "id": "resp_fixture", "model": "model-fixture-2026-10-19",
                                "reasoning": {"effort": "max"},
                                "usage": {
                                    "input_tokens": 4, "output_tokens": 3, "total_tokens": 7,
                                    "output_tokens_details": {"reasoning_tokens": 2},
                                },
                            },
                        }) + "\n")
                        return iter(row.encode("utf-8") for row in rows)

                def fake_urlopen(request, timeout):
                    self.assertEqual(request.full_url, f"{API_BASE}/responses")
                    self.assertEqual(request.get_header("Authorization"), "Bearer oauth-fixture-token")
                    body = json.loads(request.data.decode("utf-8"))
                    self.assertEqual(body["model"], "model-fixture")
                    self.assertEqual(body["reasoning"], {"effort": "max"})
                    self.assertFalse(body["store"])
                    self.assertTrue(body["stream"])
                    self.assertEqual(body["input"][0]["role"], "user")
                    self.assertNotIn("max_output_tokens", body)
                    self.assertNotIn("tools", body)
                    return FakeResponse()

                with patch.object(client, "models", return_value=[
                    {"slug": "model-fixture", "visibility": "list"},
                ]), patch("motor_editorial.siwc.urllib.request.urlopen", side_effect=fake_urlopen):
                    result = SIWCExecutor(client, model=None).execute(
                        task, SIWC_PROBE_PROFILE, context
                    )
                self.assertTrue(context.external_request_started)
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["response_id"], "resp_fixture")
                self.assertEqual(result["model_requested"], "model-fixture")
                self.assertEqual(result["model"], "model-fixture-2026-10-19")
                self.assertEqual(result["reasoning_effort_requested"], "max")
                self.assertEqual(result["reasoning_effort"], "max")
                self.assertEqual(result["external_call_count"], 1)
                self.assertEqual(result["usage"]["total_tokens"], 7)
                self.assertGreaterEqual(result["duration_ms"], 0)

    def test_editorial_raw_stream_sink_preserves_exact_complete_and_partial_text(self) -> None:
        class FakeResponse:
            def __init__(self, rows):
                self.rows = rows

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def __iter__(self):
                return iter(row.encode("utf-8") for row in self.rows)

        class FakeContext:
            external_request_started = False

            def mark_external_started(self):
                self.external_request_started = True

        with tempfile.TemporaryDirectory() as directory:
            client = SIWCClient(CredentialStore(Path(directory) / "tokens.bin"))
            raw_text = ' \n{"full_text":"primeiro parágrafo\\nsegundo parágrafo"}\t\n'
            deltas = [raw_text[:20], raw_text[20:]]
            complete_rows = [
                "data: " + json.dumps({"type": "response.output_text.delta", "delta": delta}, ensure_ascii=False) + "\n"
                for delta in deltas
            ]
            complete_rows.append("data: " + json.dumps({
                "type": "response.completed",
                "response": {
                    "id": "response-raw-fixture", "model": "gpt-6-luna-2026-10-26",
                    "reasoning": {"effort": "max"}, "usage": {"total_tokens": 9},
                },
            }) + "\n")
            captured = []
            context = FakeContext()

            def sink(text, metadata):
                captured.append((text, dict(metadata)))
                return {"ref": "fixture://response", "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}

            with patch.object(client, "access_token", return_value="oauth-fixture-token"), patch(
                "motor_editorial.siwc.urllib.request.urlopen", return_value=FakeResponse(complete_rows),
            ):
                result = client.editorial_stream_with_raw(
                    model="gpt-6-luna", reasoning_effort="max", instructions="trusted",
                    input_text="untrusted data", stage="fixture", context=context, response_sink=sink,
                )
            self.assertEqual(captured[0][0], raw_text)
            self.assertEqual(result["response_sha256"], hashlib.sha256(raw_text.encode("utf-8")).hexdigest())
            self.assertTrue(result["response_completed"])
            self.assertFalse(result["store"])
            self.assertTrue(result["stream"])
            self.assertEqual(result["raw_artifact"]["ref"], "fixture://response")
            self.assertTrue(context.external_request_started)

            partial_text = '{"body":"parágrafo incompleto'
            partial_rows = ["data: " + json.dumps({
                "type": "response.output_text.delta", "delta": partial_text,
            }, ensure_ascii=False) + "\n"]
            partial_captured = []
            with patch.object(client, "access_token", return_value="oauth-fixture-token"), patch(
                "motor_editorial.siwc.urllib.request.urlopen", return_value=FakeResponse(partial_rows),
            ):
                with self.assertRaises(TaskFailure) as raised:
                    client.editorial_stream_with_raw(
                        model="gpt-6-luna", reasoning_effort="max", instructions="trusted",
                        input_text="untrusted data", stage="fixture", context=FakeContext(),
                        response_sink=lambda text, metadata: partial_captured.append((text, dict(metadata))) or None,
                    )
            self.assertEqual(raised.exception.code, "stream_incomplete")
            self.assertTrue(raised.exception.uncertain)
            self.assertEqual(partial_captured[0][0], partial_text)
            self.assertEqual(partial_captured[0][1]["output_state"], "incomplete")
            self.assertFalse(partial_captured[0][1]["response_completed"])

    def test_responses_executor_requires_explicit_catalog_model_and_effort_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = SIWCClient(CredentialStore(Path(directory) / "tokens.bin"))
            store = Store(Path(directory) / "motor.sqlite3", Path(directory) / "artifacts")
            queue = AgentQueue(store)
            for suffix, payload, catalog in (
                ("missing-effort", {"model": "gpt-6-luna"}, [{"slug": "gpt-6-luna", "visibility": "list"}]),
                ("missing-model", {"reasoning_effort": "max"}, [{"slug": "gpt-6-luna", "visibility": "list"}]),
                ("catalog-miss", {"model": "gpt-6-luna", "reasoning_effort": "max"}, []),
            ):
                task_id = queue.enqueue(
                    task_type=SIWC_PROBE_TASK_TYPE, payload=payload,
                    profile=SIWC_PROBE_PROFILE, executor_id="siwc-responses",
                    idempotency_key=f"siwc-{suffix}", max_attempts=1,
                )
                task = queue.claim_next(task_id=task_id)
                context = TaskExecutionContext(queue, task, lease_seconds=120)
                with patch.object(client, "models", return_value=catalog), patch(
                    "motor_editorial.siwc.urllib.request.urlopen"
                ) as urlopen:
                    with self.assertRaises(TaskFailure):
                        SIWCExecutor(client, model=None).execute(task, SIWC_PROBE_PROFILE, context)
                urlopen.assert_not_called()
                self.assertFalse(context.external_request_started)

    def test_responses_executor_rejects_effective_model_or_effort_mismatch(self) -> None:
        class FakeResponse:
            def __init__(self, response_model, response_effort):
                self.response_model = response_model
                self.response_effort = response_effort

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def __iter__(self):
                rows = ["data: " + json.dumps({
                    "type": "response.output_text.delta",
                    "delta": '{"status":"ok","message":"teste de integração aprovado"}',
                }, ensure_ascii=False) + "\n"]
                rows.append("data: " + json.dumps({
                    "type": "response.completed",
                    "response": {
                        "id": "resp_mismatch",
                        "model": self.response_model,
                        "reasoning": {"effort": self.response_effort},
                        "usage": {"total_tokens": 7},
                    },
                }) + "\n")
                return iter(row.encode("utf-8") for row in rows)

        for suffix, response_model, response_effort, expected_code in (
            ("wrong-model", "gpt-6.1-sol", "max", "siwc_model_mismatch"),
            ("wrong-effort", "gpt-6-luna", "high", "siwc_reasoning_effort_mismatch"),
        ):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                client = SIWCClient(CredentialStore(Path(directory) / "tokens.bin"))
                store = Store(Path(directory) / "motor.sqlite3", Path(directory) / "artifacts")
                queue = AgentQueue(store)
                task_id = queue.enqueue(
                    task_type=SIWC_PROBE_TASK_TYPE,
                    payload={"model": "gpt-6-luna", "reasoning_effort": "max"},
                    profile=SIWC_PROBE_PROFILE, executor_id="siwc-responses",
                    idempotency_key=f"siwc-{suffix}", max_attempts=1,
                )
                task = queue.claim_next(task_id=task_id)
                context = TaskExecutionContext(queue, task, lease_seconds=120)
                with patch.object(client, "models", return_value=[
                    {"slug": "gpt-6-luna", "visibility": "list"},
                ]), patch.object(client, "access_token", return_value="oauth-fixture-token"), patch(
                    "motor_editorial.siwc.urllib.request.urlopen",
                    return_value=FakeResponse(response_model, response_effort),
                ):
                    with self.assertRaises(TaskFailure) as raised:
                        SIWCExecutor(client, model=None).execute(task, SIWC_PROBE_PROFILE, context)
                self.assertEqual(raised.exception.code, expected_code)
                self.assertTrue(context.external_request_started)

    def test_siwe_reasoning_effort_allowlist_excludes_unverified_values(self) -> None:
        self.assertEqual(SIWC_REASONING_EFFORTS, {"none", "low", "medium", "high", "xhigh", "max"})

    def test_responses_transport_failure_is_uncertain_and_never_auto_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = SIWCClient(CredentialStore(Path(directory) / "tokens.bin"))
            with patch.object(client, "access_token", return_value="oauth-fixture-token"):
                context = type("Context", (), {"mark_external_started": lambda self: setattr(self, "started", True)})()
                with patch("motor_editorial.siwc.urllib.request.urlopen", side_effect=OSError("private transport detail")):
                    with self.assertRaises(TaskFailure) as raised:
                        client.inference_stream("model-fixture", "max", context)
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
