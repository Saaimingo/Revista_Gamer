from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import Mock

from motor_editorial.agent_contracts import ResearchPacket, ResearchRequest
from motor_editorial.eng_codex_011 import (
    SOURCE_CANDIDATES,
    Checkpoint,
    RunBlocked,
    _canonicalize_investigator_claim_ids,
    _make_radar_profile,
    _build_initial_packet,
    _map_persisted_live_items,
    _normalize_writer_claim_refs_against_section_evidence,
    _read_completed_role_artifact,
    _load_succeeded_role_output,
    _restore_persisted_discovery_batch,
    _task_output,
    _advance_reviewer_correction,
    _dispatch_reviewer_research_return,
    RADAR_RESEARCH_TASK_TYPE,
    RUN_MISSION,
    _register_source,
)
from motor_editorial.agent_siwc import SIWCResponseArtifactStore
from motor_editorial.radar_store import RadarStore
from motor_editorial.radar_triage import EDITORIAL_TRIAGE_LANES, resolve_triage_output
from motor_editorial.db import stable_hash
from motor_editorial.usage_meter import AgentUsageArtifactStore, StoryVersionArchive


class PersistedTriageResumeTests(unittest.TestCase):
    def test_runner_reuses_executor_persisted_usage_receipt_without_rewriting(self) -> None:
        task_id = "triage-receipt-reuse"
        raw_bytes = b'{"decisions":[],"no_change":true}'
        response_digest = hashlib.sha256(raw_bytes).hexdigest()
        receipt_ref = {"ref": f"agent-usage/{task_id}.attempt-001.json", "sha256": "b" * 64}
        usage_record = {
            "task_id": task_id, "attempt_number": 1, "role_id": "triage_analyst",
            "model": "gpt-6-luna-2026-10-26", "reasoning_effort": "max",
            "input_tokens": 8, "output_tokens": 4, "total_tokens": 12,
            "raw_response_sha256": response_digest, "provider_response_id": "resp-fixture",
        }
        metadata = {
            "role_id": "triage_analyst", "usage_receipt_ref": receipt_ref,
            "model": usage_record["model"], "reasoning_effort": "max", "response_id": "resp-fixture",
            "usage": {"input_tokens": 8, "output_tokens": 4, "total_tokens": 12},
            "response_sha256": response_digest, "output_validation": "role_schema_valid",
        }
        with tempfile.TemporaryDirectory(prefix="eng012-receipt-reuse-") as temporary:
            root = Path(temporary)
            metadata_path = root / "metadata.json"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            task = SimpleNamespace(
                task_id=task_id, state="succeeded", attempts=1,
                result={
                    "artifact_ref": {"ref": "response.json", "sha256": response_digest},
                    "usage_receipt_ref": receipt_ref,
                },
            )

            class Queue:
                def get(self, requested_task_id):
                    return task if requested_task_id == task_id else None

            class ResponseStore:
                def artifact_paths(self, requested_task_id):
                    return None, None, metadata_path

                def read_response(self, ref, digest):
                    self.assert_ref = (ref, digest)
                    return raw_bytes

            class UsageStore:
                def read(self, ref, digest):
                    if (ref, digest) != (receipt_ref["ref"], receipt_ref["sha256"]):
                        raise AssertionError("unexpected receipt reference")
                    return usage_record

                def write(self, record):
                    raise AssertionError("runner must not rewrite the executor receipt")

            envelope = SimpleNamespace(role_id="triage_analyst", research_mediation_policy=None)
            with patch("motor_editorial.eng_codex_011.build_usage_record", return_value=usage_record):
                output, recovered_metadata, recovered_ref = _task_output(
                    task_id=task_id, queue=Queue(), response_store=ResponseStore(), root=root,
                    envelope=envelope, usage_store=UsageStore(), research_suggestion_count=None,
                )

            self.assertEqual(output, {"decisions": [], "no_change": True})
            self.assertEqual(recovered_metadata["response_sha256"], response_digest)
            self.assertEqual(recovered_ref, receipt_ref)
            self.assertTrue((root / "structured-outputs" / f"{task_id}.json").is_file())

    def test_call_started_checkpoint_resume_is_validation_only_until_ledger_recovery(self) -> None:
        run_id = "eng-codex-012-fixture-run"
        task_id = "radar-triage-fixture"
        with tempfile.TemporaryDirectory(prefix="eng012-triage-resume-validation-") as temporary:
            root = Path(temporary)
            response_store = SIWCResponseArtifactStore(root)
            response_store.write_request(task_id, {"prompt_input": {"task_input_data": {"data": {}}}})
            raw_response = '{"decisions":[]}'
            response_store.write_response(task_id, raw_response, {
                "role_id": "triage_analyst", "response_id": "resp-fixture",
                "model": "gpt-6-luna-2026-10-26", "reasoning_effort": "max",
                "response_completed": True, "store": False, "stream": True,
                "output_validation": "role_schema_valid",
                "response_sha256": hashlib.sha256(raw_response.encode("utf-8")).hexdigest(),
            })
            response_digest = hashlib.sha256(raw_response.encode("utf-8")).hexdigest()
            usage_store = AgentUsageArtifactStore(root)
            usage_ref = usage_store.write({
                "task_id": task_id, "attempt_number": 1, "raw_response_sha256": response_digest,
                "role_id": "triage_analyst", "provider_response_id": "resp-fixture",
                "model": "gpt-6-luna-2026-10-26", "reasoning_effort": "max",
            })
            response_store.update_metadata(task_id, {"usage_receipt_ref": usage_ref})
            checkpoint_state = {
                "run_id": run_id, "stage": "triage_agent", "status": "running",
                "events": [{"stage": "triage_agent", "status": "call_started", "task_id": task_id}],
            }
            checkpoint_path = root / "checkpoint.json"
            original = json.dumps(checkpoint_state, ensure_ascii=False)
            checkpoint_path.write_text(original, encoding="utf-8")

            with patch("motor_editorial.eng_codex_011.REASONING_EFFORT", "max"):
                checkpoint = Checkpoint.resume_after_triage(root, run_id)

            self.assertEqual(checkpoint.resume_recovery, "adopt_durable_triage_result_after_runner_interruption")
            self.assertEqual(checkpoint_path.read_text(encoding="utf-8"), original)

    def test_triage_reused_checkpoint_can_resume_without_adding_duplicate_events(self) -> None:
        run_id = "eng-codex-012-fixture-run"
        task_id = "radar-triage-fixture"
        with tempfile.TemporaryDirectory(prefix="eng012-triage-reused-resume-") as temporary:
            root = Path(temporary)
            AgentUsageArtifactStore(root).write({
                "task_id": task_id, "attempt_number": 1,
                "raw_response_sha256": "a" * 64, "role_id": "triage_analyst",
                "model": "gpt-6-luna-2026-10-26", "reasoning_effort": "max",
            })
            state = {
                "run_id": run_id, "stage": "triage_reused", "status": "running",
                "events": [{
                    "stage": "triage_reused", "status": "succeeded", "task_id": task_id,
                    "prior_triage_calls": 1, "repeated_siwc_calls": 0,
                    "repeated_public_requests": 0,
                }],
            }
            checkpoint_path = root / "checkpoint.json"
            original = json.dumps(state, ensure_ascii=False)
            checkpoint_path.write_text(original, encoding="utf-8")

            checkpoint = Checkpoint.resume_after_triage(root, run_id)

            self.assertEqual(checkpoint.resume_recovery, "continue_after_durable_triage_reuse")
            self.assertEqual(checkpoint_path.read_text(encoding="utf-8"), original)

    def test_interrupted_triage_resume_event_is_recoverable_without_duplicate_start(self) -> None:
        run_id = "eng-codex-012-fixture-run"
        task_id = "radar-triage-fixture"
        with tempfile.TemporaryDirectory(prefix="eng012-triage-resume-event-") as temporary:
            root = Path(temporary)
            receipt = AgentUsageArtifactStore(root).write({
                "task_id": task_id, "attempt_number": 1,
                "raw_response_sha256": "a" * 64, "role_id": "triage_analyst",
                "model": "gpt-6-luna-2026-10-26", "reasoning_effort": "max",
            })
            state = {
                "run_id": run_id, "stage": "resume_after_triage", "status": "running",
                "events": [{
                    "stage": "resume_after_triage", "status": "started",
                    "reused_task_id": task_id, "usage_record_ref": receipt["ref"],
                    "repeated_siwc_calls": 0, "repeated_public_requests": 0,
                }],
            }
            checkpoint_path = root / "checkpoint.json"
            original = json.dumps(state, ensure_ascii=False)
            checkpoint_path.write_text(original, encoding="utf-8")

            checkpoint = Checkpoint.resume_after_triage(root, run_id)

            self.assertEqual(checkpoint.resume_recovery, "continue_interrupted_triage_recovery")
            self.assertEqual(checkpoint_path.read_text(encoding="utf-8"), original)

    def test_recovered_persisted_batch_is_a_typed_batch_accepted_by_triage_resolver(self) -> None:
        batch = _restore_persisted_discovery_batch({
            "batch_id": "batch-1",
            "portfolio": ["game-proton"],
            "items": [{"item_id": "item-1", "evidence_refs": ["snapshot-1"]}],
        }, ["snapshot-1"])

        resolution = resolve_triage_output(batch, {
            "no_change": False,
            "decisions": [{
                "candidate_item_ids": ["item-1"], "candidate_angle": "Release oficial",
                "suggested_lane": "principal", "evidence_refs": ["snapshot-1"],
            }],
        })

        self.assertEqual(batch.batch_id, "batch-1")
        self.assertEqual(batch.source_snapshot_ids, ("snapshot-1",))
        self.assertEqual(resolution.eligible_decisions[0].candidate_item_ids, ("item-1",))

    def test_missing_derived_output_reconstructs_from_raw_and_preserves_usage_receipt(self) -> None:
        task_id = "triage-reconstruct-fixture"
        input_payload = {"batch_id": "batch-1", "items": []}
        raw_bytes = b'{"decisions":[],"no_change":true}'
        response_digest = hashlib.sha256(raw_bytes).hexdigest()
        request_record = {"prompt_input": {"task_input_data": {"data": input_payload}}}
        request_bytes = json.dumps(request_record, separators=(",", ":")).encode("utf-8")
        request_digest = hashlib.sha256(request_bytes).hexdigest()
        metadata = {
            "task_id": task_id, "role_id": "triage_analyst", "response_sha256": response_digest,
            "response_completed": True, "store": False, "stream": True,
            "output_validation": "role_schema_valid", "model": "gpt-6-luna-2026-10-26",
            "reasoning_effort": "max", "response_id": "resp-fixture",
            "usage": {"input_tokens": 8, "output_tokens": 4, "total_tokens": 12},
            "request_artifact_ref": "request.json", "request_artifact_sha256": request_digest,
        }
        with tempfile.TemporaryDirectory(prefix="eng012-missing-structured-output-") as temporary:
            root = Path(temporary)
            request_path = root / "request.json"
            metadata_path = root / "metadata.json"
            request_path.write_bytes(request_bytes)
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            usage_store = AgentUsageArtifactStore(root)
            receipt = {
                "task_id": task_id, "attempt_number": 1, "role_id": "triage_analyst",
                "model": metadata["model"], "reasoning_effort": "max",
                "provider_response_id": "resp-fixture", "input_tokens": 8,
                "output_tokens": 4, "total_tokens": 12, "raw_response_sha256": response_digest,
            }
            usage_ref = usage_store.write(receipt)
            metadata["usage_receipt_ref"] = usage_ref
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            task = SimpleNamespace(
                task_id=task_id, state="succeeded", attempts=1,
                payload={"input": input_payload},
                result={
                    "artifact_ref": {"ref": "response.json", "sha256": response_digest},
                    "usage_receipt_ref": usage_ref,
                },
            )

            class Queue:
                def get(self, requested_task_id):
                    return task if requested_task_id == task_id else None

                def events(self, requested_task_id):
                    return []

            class ResponseStore:
                def artifact_paths(self, requested_task_id):
                    return request_path, root / "response.json", metadata_path

                def read_response(self, ref, digest):
                    value = {"response.json": raw_bytes, "request.json": request_bytes}[ref]
                    if hashlib.sha256(value).hexdigest() != digest:
                        raise ValueError("fixture digest mismatch")
                    return value

            class RoleCatalog:
                def validate_task(self, *args, **kwargs):
                    return None

                def validate_result(self, *args, **kwargs):
                    return None

                def resolve(self, *args, **kwargs):
                    return SimpleNamespace(output_schema={})

            envelope = SimpleNamespace(role_id="triage_analyst", role_version="1.0.0", role_hash="a" * 64)
            with patch("motor_editorial.eng_codex_011.REASONING_EFFORT", "max"), \
                 patch("motor_editorial.eng_codex_011.envelope_from_payload", return_value=envelope), \
                 patch("motor_editorial.eng_codex_011.validate_json_schema"), \
                 patch("motor_editorial.eng_codex_011._validate_output_references"):
                output, recovered_metadata, recovered_usage_ref = _load_succeeded_role_output(
                    task_id=task_id, queue=Queue(), role_catalog=RoleCatalog(),
                    response_store=ResponseStore(), root=root,
                )

            output_path = root / "structured-outputs" / f"{task_id}.json"
            self.assertEqual(output, {"decisions": [], "no_change": True})
            self.assertEqual(recovered_metadata["response_sha256"], response_digest)
            self.assertEqual(recovered_usage_ref, usage_ref["ref"])
            self.assertTrue(output_path.is_file())
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8"))["raw_response_sha256"], response_digest)
            self.assertEqual(usage_store.read(usage_ref["ref"], usage_ref["sha256"]), receipt)

    def test_reviewer_correction_research_returns_once_to_same_journalist_within_budget(self) -> None:
        request = ResearchRequest.from_mapping({
            "schema_version": "1.1", "request_id": "review-research-1", "parent_task_id": "writer-correction-1",
            "story_id": "story-1", "story_revision_id": "story-revision-review-01",
            "requester_role_id": "persona_writer", "requester_persona_id": "persona-a",
            "research_profile_id": "radar.general.v1", "research_profile_version": "1.0.0",
            "question": "Confirme o detalhe publicado na versão selecionada.", "queries": ["release notes tag"],
            "entity_ids": [], "required_evidence_kinds": ["official_statement"],
            "preferred_source_ids": ["source-selected"], "preferred_domains": ["api.github.com"],
            "languages": ["en"], "time_window": {}, "versions_configurations": {},
            "known_evidence_ids": [], "exclusions": [], "max_sources": 1, "max_requests": 1,
            "max_bytes": 10000, "max_duration_seconds": 10, "reason": "Complete official release evidence.",
            "allowed_scope": ["read:radar_index", "read:registered_public_sources"],
            "idempotency_key": "review-research-idem-1", "human_gate_if_sensitive": True,
        })
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "public-research-log.json").write_text(
                json.dumps({"mission": RUN_MISSION, "requests": []}), encoding="utf-8",
            )
            radar_task = SimpleNamespace(
                task_id="radar-task-1", task_type=RADAR_RESEARCH_TASK_TYPE,
                payload={"research_request": request.to_dict()}, state="queued",
                external_request_started=False, result=None,
            )
            continuation = SimpleNamespace(
                task_id="writer-return-1", task_type="agent.role.persona_writer",
                payload={"research_packet": {"request_id": request.request_id},
                         "research_cycle_already_used": True},
                state="succeeded", result={"artifact_ref": {"ref": "raw.json", "sha256": "a" * 64}},
            )

            class Queue:
                def list_tasks(self, limit=1000):
                    return [radar_task, continuation] if routed else [radar_task]

                def get(self, task_id):
                    return radar_task if task_id == radar_task.task_id else continuation

            routed = False
            queue = Queue()
            dispatcher = Mock()

            def dispatch_one(task_id):
                self.assertEqual(task_id, radar_task.task_id)
                radar_task.state = "succeeded"
                radar_task.result = {"packet": {"request_id": request.request_id}}
                return SimpleNamespace(state="succeeded")

            dispatcher.dispatch_one.side_effect = dispatch_one

            def route(task):
                nonlocal routed
                self.assertIs(task, radar_task)
                routed = True

            router = Mock(side_effect=route)
            provider = SimpleNamespace(last_execution={"endpoint": "https://api.github.com/releases/tag/x", "http_status": 200,
                                                       "fetched_at": "2026-10-27T00:00:00Z", "payload_bytes": 20,
                                                       "payload_sha256": "b" * 64})
            archive = Mock()
            archive.write.return_value = {"manifest_ref": "story/manifest.json", "full_text_sha256": "c" * 64}
            writer_output = {"title": "Título", "dek": "Linha fina", "sections": [{"heading": "Seção", "body": "Texto"}]}
            with patch("motor_editorial.eng_codex_011.ResearchPacket.from_mapping",
                       return_value=SimpleNamespace(request_id=request.request_id, document_refs=(object(),), claim_refs=())), \
                 patch("motor_editorial.eng_codex_011.envelope_from_payload",
                       return_value=SimpleNamespace(story_id="story-1", persona_id="persona-a")), \
                 patch("motor_editorial.eng_codex_011._dispatch_role",
                       return_value=(writer_output, {"model": "gpt-6-luna", "reasoning_effort": "max"}, {"ref": "usage.json", "sha256": "d" * 64})), \
                 patch("motor_editorial.eng_codex_011._read_completed_role_artifact",
                       return_value=(continuation, {"ref": "raw.json", "sha256": "a" * 64}, b"raw")):
                result = _dispatch_reviewer_research_return(
                    request=request, writer_task_id="writer-correction-1", queue=queue,
                    dispatcher=dispatcher, router=router, role_catalog=object(), provider=provider,
                    detail_source_id="source-selected", research_completed=False,
                    root=root, response_store=object(), usage_store=object(), checkpoint=Mock(), version_archive=archive,
                )
            self.assertEqual(result[0], writer_output)
            self.assertEqual(result[1].story_id, "story-1")
            self.assertEqual(result[1].persona_id, "persona-a")
            self.assertEqual(result[2], continuation)
            self.assertIs(result[5].request_id, request.request_id)
            dispatcher.dispatch_one.assert_called_once_with(radar_task.task_id)
            router.assert_called_once_with(radar_task)
            archive.write.assert_called_once()
            saved_log = json.loads((root / "public-research-log.json").read_text(encoding="utf-8"))
            self.assertEqual(len(saved_log["requests"]), 1)
            self.assertEqual(saved_log["requests"][0]["status"], "observed")

    def test_reviewer_correction_branch_rechecks_and_stops_on_holds(self) -> None:
        original = {"title": "Title", "dek": "Dek", "sections": [{"heading": "H", "body": "Original"}]}
        original_text = StoryVersionArchive._render(original)
        original_hash = stable_hash(original_text)
        revision = {"title": "Title", "dek": "Dek", "sections": [{"heading": "H", "body": "Revised"}], "requested_research": []}

        def exercise(revised, fact_status="pass", final_verdict="pass"):
            calls, tasks, events, archived = [], [], [], []
            revised_hash = stable_hash(StoryVersionArchive._render(revised))

            def new_task(**kwargs):
                tasks.append(kwargs)
                return kwargs["stage"], SimpleNamespace(role_id=kwargs["role_id"])

            def dispatch(**kwargs):
                stage = kwargs["stage"]
                calls.append(stage)
                if stage == "journalist_review_correction_agent":
                    return revised, {"provider": "fake"}, {"ref": "usage", "sha256": "b" * 64}
                if stage == "fact_checker_review_correction_agent":
                    return {"draft_hash": revised_hash, "status": fact_status, "findings": []}, {}, None
                if stage == "editorial_reviewer_final_agent":
                    return {"draft_hash": revised_hash, "verdict": final_verdict,
                            "findings": ["Ainda ajustar."] if final_verdict == "revise" else [],
                            "human_review_required": True}, {}, None
                raise AssertionError(stage)

            queue = SimpleNamespace(get=lambda task_id: SimpleNamespace(
                task_id=task_id, state="succeeded", result={"artifact_ref": {"ref": "raw", "sha256": "a" * 64}}))
            checkpoint = SimpleNamespace(event=lambda *args, **kwargs: events.append((args, kwargs)))
            archive = SimpleNamespace(write=lambda **kwargs: archived.append(kwargs) or {
                "manifest_ref": "manifest", "full_text_sha256": revised_hash})
            review = {"draft_hash": original_hash, "verdict": "revise", "findings": ["Ajustar abertura."],
                      "human_review_required": True}
            fact = {"draft_hash": original_hash, "status": "pass", "findings": []}
            args = dict(
                reviewer_output=review, reviewer_task="review-1", reviewer_envelope=object(),
                draft_hash=original_hash, editorial_brief={}, final_dossier={}, writing_constraints={},
                story_text=original_text, research_completed=False, queue=queue,
                role_catalog=SimpleNamespace(validate_result=lambda *_: SimpleNamespace(requested_research=None)),
                profiles={}, run_id="run", run_token="token", story_id="story", snapshot_ids=[], root=Path("."),
                detail_source_id="source", selected={"source": {}, "tag_name": "tag", "evidence_ids": []},
                persona_id="persona", package={"version": "v1"}, persona_text="DNA", research_packet=None,
                initial_packet=None, dispatcher=object(), router=object(), provider=object(),
                response_store=SimpleNamespace(read_response=lambda *_: b"raw"),
                usage_store=object(), checkpoint=checkpoint, version_archive=archive,
                fact_checker_input={"draft": original_text, "draft_hash": original_hash},
                reviewer_input={"draft": original_text, "draft_hash": original_hash, "fact_check_verdict": fact},
                current_writer_output=original, current_writer_task=object(), current_writer_envelope=object(),
                current_writer_meta={}, current_writer_usage=None, current_fact_output=fact,
                current_fact_task_id="fact-1", leaked_markers=[],
            )
            with patch("motor_editorial.eng_codex_011._new_role_task", side_effect=new_task), \
                 patch("motor_editorial.eng_codex_011._dispatch_role", side_effect=dispatch), \
                 patch("motor_editorial.eng_codex_011._make_med_policy", return_value={}):
                try:
                    result = _advance_reviewer_correction(**args)
                except RunBlocked as error:
                    result = str(error)
            return result, calls, tasks, events, archived

        result, calls, tasks, events, archived = exercise(revision)
        self.assertEqual(calls, ["journalist_review_correction_agent", "fact_checker_review_correction_agent", "editorial_reviewer_final_agent"])
        self.assertEqual(tasks[0]["persona_id"], "persona")
        self.assertEqual(tasks[0]["dependencies"], ("review-1",))
        self.assertEqual(tasks[1]["dependencies"], ("editorial-review-revision-01",))
        self.assertEqual(tasks[2]["dependencies"], ("fact-check-review-revision-01",))
        self.assertEqual(tasks[0]["input_payload"]["writing_constraints"]["prior_draft"], original_text)
        self.assertEqual(result[11], stable_hash(StoryVersionArchive._render(revision)))
        self.assertEqual(len(archived), 1)
        self.assertEqual(events[-1][1]["action"], "await_human_approval")

        unchanged = {**original, "requested_research": []}
        result, calls, _, _, archived = exercise(unchanged)
        self.assertEqual(result, "review_correction_did_not_change_draft")
        self.assertEqual(calls, ["journalist_review_correction_agent"])
        self.assertEqual(len(archived), 1)
        result, calls, _, _, _ = exercise({**revision, "requested_research": ["fonte adicional"]})
        self.assertEqual(result, "review_correction_research_request_not_accepted_by_motor")
        self.assertEqual(calls, ["journalist_review_correction_agent"])
        result, calls, _, _, _ = exercise(revision, fact_status="revise")
        self.assertEqual(result, "review_correction_fact_check_not_pass")
        self.assertEqual(len(calls), 2)
        _, calls, _, events, _ = exercise(revision, final_verdict="revise")
        self.assertEqual(len(calls), 3)
        self.assertEqual(events[-1][1]["action"], "hold_correction_limit")

    def test_completed_role_artifact_reads_fresh_task_after_dispatch(self) -> None:
        stale_snapshot = SimpleNamespace(state="queued", result=None)
        persisted = SimpleNamespace(state="succeeded", result={"artifact_ref": {"ref": "response.json", "sha256": "a" * 64}})

        class Queue:
            def get(self, task_id):
                self.task_id = task_id
                return persisted

        class Store:
            def read_response(self, ref, digest):
                self.args = (ref, digest)
                return b"durable response"

        queue, store = Queue(), Store()
        task, ref, raw = _read_completed_role_artifact(queue, "continued-writer", store)
        self.assertIsNot(task, stale_snapshot)
        self.assertIs(task, persisted)
        self.assertEqual(queue.task_id, "continued-writer")
        self.assertEqual(store.args, ("response.json", "a" * 64))
        self.assertEqual((ref["ref"], raw), ("response.json", b"durable response"))
        persisted.state = "queued"
        with self.assertRaisesRegex(RunBlocked, "completed_role_task_result_not_persisted"):
            _read_completed_role_artifact(queue, "continued-writer", store)
        persisted.state, persisted.result = "succeeded", {}
        with self.assertRaisesRegex(RunBlocked, "completed_role_task_artifact_reference_missing"):
            _read_completed_role_artifact(queue, "continued-writer", store)

    def test_source_registration_resume_requires_the_exact_saved_blocker(self) -> None:
        run_id = "eng-codex-011-fixture-run"
        with tempfile.TemporaryDirectory(prefix="eng011-checkpoint-resume-") as temporary:
            root = Path(temporary)
            (root / "active-run.json").write_text(json.dumps({
                "run_id": run_id, "status": "blocked", "blocker_code": "RadarStoreError",
            }), encoding="utf-8")
            (root / "checkpoint.json").write_text(json.dumps({
                "run_id": run_id, "stage": "persona_load", "status": "running",
                "events": [{"stage": "persona_load", "status": "succeeded"}],
            }), encoding="utf-8")

            checkpoint = Checkpoint.resume_after_source_registration_block(root, run_id)

            self.assertEqual(checkpoint.state["stage"], "resume_after_source_registration")
            self.assertEqual(checkpoint.state["events"][-1]["repeated_siwc_calls"], 0)
            self.assertEqual(checkpoint.state["events"][-1]["repeated_public_requests"], 0)

    def test_writer_preflight_resume_accepts_only_saved_persona_load_guard_blocker(self) -> None:
        run_id = "eng-codex-011-fixture-run"
        with tempfile.TemporaryDirectory(prefix="eng011-writer-checkpoint-") as temporary:
            root = Path(temporary)
            (root / "active-run.json").write_text(json.dumps({
                "run_id": run_id, "status": "blocked",
                "blocker_code": "existing_writer_task_is_not_a_safe_pre_external_recovery",
            }), encoding="utf-8")
            (root / "checkpoint.json").write_text(json.dumps({
                "run_id": run_id, "stage": "persona_load", "status": "running",
                "events": [{"stage": "persona_load", "status": "succeeded"}],
            }), encoding="utf-8")

            checkpoint = Checkpoint.resume_after_pre_external_writer_block(root, run_id)

            self.assertEqual(checkpoint.state["stage"], "resume_after_writer_preflight")
            self.assertEqual(checkpoint.state["events"][-1]["repeated_siwc_calls"], 0)
            self.assertEqual(checkpoint.state["events"][-1]["repeated_public_requests"], 0)

    def test_writer_revision_resume_accepts_only_saved_unknown_claim_blocker(self) -> None:
        run_id = "eng-codex-011-fixture-run"
        with tempfile.TemporaryDirectory(prefix="eng011-revision-checkpoint-") as temporary:
            root = Path(temporary)
            (root / "agent-usage").mkdir()
            (root / "agent-usage" / "revision.attempt-001.json").write_text("{}", encoding="utf-8")
            (root / "active-run.json").write_text(json.dumps({
                "run_id": run_id, "status": "blocked", "blocker_code": "persona_writer_call_blocked",
            }), encoding="utf-8")
            (root / "checkpoint.json").write_text(json.dumps({
                "run_id": run_id, "stage": "journalist_correction_agent", "status": "running",
                "events": [{
                    "stage": "journalist_correction_agent", "status": "blocked",
                    "task_id": "revision", "task_state": "blocked",
                    "error_code": "siwc_output_unknown_claim",
                    "usage_record_ref": "agent-usage/revision.attempt-001.json",
                }],
            }), encoding="utf-8")

            checkpoint = Checkpoint.resume_after_writer_revision_failure(root, run_id)

            self.assertEqual(checkpoint.state["stage"], "resume_after_writer_revision_failure")
            self.assertEqual(checkpoint.state["events"][-1]["repeated_siwc_calls"], 0)
            self.assertEqual(checkpoint.state["events"][-1]["repeated_public_requests"], 0)

    def test_event_reference_links_candidate_when_item_id_is_not_returned(self) -> None:
        batch = {
            "batch_id": "batch-release-42",
            "items": [{
                "item_id": "discovery-release-42",
                "url": "https://source.example.invalid/release",
                "publisher": "Source",
                "evidence_refs": ["event-abc", "snapshot-def", "radar://document/" + "a" * 32],
            }],
        }
        resolved = resolve_triage_output(batch, {
            "no_change": False,
            "decisions": [{
                "candidate_angle": "Analisar a mudança documentada",
                "suggested_lane": "principal",
                "evidence_refs": ["event-abc"],
            }],
        })

        self.assertEqual(resolved.decisions[0].candidate_item_ids, ("discovery-release-42",))

    def test_monitoramento_is_forwarded_to_editor_for_decision(self) -> None:
        self.assertIn("monitoramento", EDITORIAL_TRIAGE_LANES)
        self.assertNotIn("descartar", EDITORIAL_TRIAGE_LANES)

    def test_natural_language_investigator_claim_id_is_normalized_and_label_preserved(self) -> None:
        source_label = "Proton 11.0-2e release metadata: title and published date"
        normalized, mapping = _canonicalize_investigator_claim_ids({
            "claims": [{"claim_id": source_label, "evidence_ids": ["radar://document/" + "a" * 32],
                        "epistemic_status": "official_statement"}],
            "blockers": [],
        })

        claim = normalized["claims"][0]
        self.assertRegex(claim["claim_id"], r"^claim-[a-f0-9]{24}$")
        self.assertEqual(claim["source_claim_label"], source_label)
        self.assertEqual(mapping[0]["source_claim_label"], source_label)
        self.assertEqual(mapping[0]["canonical_claim_id"], claim["claim_id"])

    def test_writer_claim_field_recovery_only_drops_evidence_refs_cited_in_sections(self) -> None:
        prompt_input = {
            "task_input_data": {"data": {"evidence_dossier": {
                "claims": [], "evidence": [{"evidence_id": "radar://document/release-01"}],
            }}},
        }
        output = {
            "title": "Release",
            "dek": "The official record confirms a date.",
            "sections": [{"heading": "Record", "body": "The tag is listed.",
                          "evidence_ids": ["radar://document/release-01"]}],
            "claim_refs": ["radar://document/release-01"],
        }

        normalized, dropped = _normalize_writer_claim_refs_against_section_evidence(output, prompt_input)

        self.assertEqual(dropped, ["radar://document/release-01"])
        self.assertEqual(normalized["claim_refs"], [])
        self.assertEqual(normalized["sections"][0]["evidence_ids"], ["radar://document/release-01"])
        self.assertEqual(output["claim_refs"], ["radar://document/release-01"])

    def test_writer_claim_field_recovery_rejects_unknown_claim_label(self) -> None:
        prompt_input = {
            "task_input_data": {"data": {"evidence_dossier": {
                "claims": [], "evidence": [{"evidence_id": "evidence-01"}],
            }}},
        }
        output = {
            "sections": [{"evidence_ids": ["evidence-01"]}],
            "claim_refs": ["unsupported-claim"],
        }

        with self.assertRaisesRegex(RunBlocked, "beyond_known_section_evidence"):
            _normalize_writer_claim_refs_against_section_evidence(output, prompt_input)

    def test_persisted_document_uses_canonical_release_url_when_origin_missing(self) -> None:
        document_id = "a" * 32
        document = {
            "document_id": document_id,
            "source_id": "github-api-proton-releases",
            "origin_url": None,
            "canonical_url": "https://github.com/ValveSoftware/Proton/releases/tag/proton-11.0-2e",
            "publisher": "Valve Proton public releases",
            "byline": "ivyl",
            "published_at": "2026-10-09T17:49:01+00:00",
            "fetched_at": "2026-10-26T15:22:29+00:00",
            "title": "Proton 11.0-2e",
            "summary_snippet": "A short official release excerpt.",
        }

        class FakeRadarStore:
            def get_row(self, table: str, key_column: str, key_value: str):
                if table == "radar_documents" and key_column == "document_id" and key_value == document_id:
                    return document
                return None

        source = {
            "source_id": "github-api-proton-releases",
            "owner": "ValveSoftware",
            "repo": "Proton",
            "label": "Valve Proton public releases",
        }
        item = {
            "item_id": "discovery-release-42",
            "url": document["canonical_url"],
            "publisher": document["publisher"],
            "published_at": document["published_at"],
            "diff": "{}",
            "evidence_refs": ["event-abc", f"radar://document/{document_id}"],
        }

        mapped = _map_persisted_live_items([item], {source["source_id"]: source}, FakeRadarStore())
        candidate = mapped["discovery-release-42"]
        self.assertEqual(candidate["tag_name"], "proton-11.0-2e")
        self.assertEqual(candidate["title"], "Proton 11.0-2e")
        self.assertEqual(candidate["body_excerpt"], "A short official release excerpt.")
        self.assertEqual(candidate["author"], "ivyl")

    def test_persisted_document_does_not_treat_api_endpoint_as_release_origin(self) -> None:
        document_id = "b" * 32
        document = {
            "document_id": document_id,
            "source_id": "github-api-proton-releases",
            "origin_url": None,
            "canonical_url": "https://api.github.com/repos/ValveSoftware/Proton/releases/408184123",
            "publisher": "Valve Proton public releases",
        }

        class FakeRadarStore:
            def get_row(self, table: str, key_column: str, key_value: str):
                if table == "radar_documents" and key_column == "document_id" and key_value == document_id:
                    return document
                return None

        source = SOURCE_CANDIDATES[1]
        item = {
            "item_id": "discovery-release-api-only",
            "evidence_refs": [f"radar://document/{document_id}"],
        }

        self.assertEqual(
            _map_persisted_live_items([item], {source["source_id"]: source}, FakeRadarStore()),
            {},
        )

    def test_initial_packet_accepts_empty_republication_relation_list(self) -> None:
        document_id = "c" * 32
        source_id = "github-api-proton-releases"
        document = {
            "document_id": document_id, "source_id": source_id,
            "canonical_url": "https://github.com/ValveSoftware/Proton/releases/tag/proton-11.0-2e",
            "content_sha256": "d" * 64, "title": "Proton 11.0-2e",
            "publisher": "Valve Proton public releases", "byline": "ivyl",
            "published_at": "2026-10-09T17:49:01+00:00", "fetched_at": "2026-10-27T02:59:21+00:00",
        }

        class FakeRadarStore:
            def get_row(self, table: str, key_column: str, key_value: str):
                if table == "radar_documents" and key_column == "document_id" and key_value == document_id:
                    return document
                if table == "radar_sources" and key_column == "source_id" and key_value == source_id:
                    return {"source_type": "public_api", "rights_status": "unknown"}
                return None

        candidate = {
            "source_id": source_id, "document_ids": [document_id], "body_excerpt": None,
            "diff": json.dumps({"source_lineage": [{
                "document_id": document_id, "republication_relations": [],
            }], "claim_lineage": []}),
        }

        packet, evidence_rows = _build_initial_packet(
            request_id="initial-radar-fixture", radar_store=FakeRadarStore(),
            eligible_candidates=[candidate],
        )

        self.assertEqual(packet.status, "partial")
        self.assertEqual(len(evidence_rows), 1)
        self.assertIsNone(evidence_rows[0]["republication_relation"])

    def test_radar_source_registration_is_idempotent_but_rejects_route_conflicts(self) -> None:
        source = SOURCE_CANDIDATES[1]
        detail_source_id = "github-api-proton-detail"
        display_name = "ValveSoftware/Proton release detail"
        with tempfile.TemporaryDirectory(prefix="eng011-source-registration-") as temporary:
            store = RadarStore(Path(temporary) / "radar.sqlite3")
            profile, endpoint = _make_radar_profile(source, detail_source_id, details=True, tag="proton-11.0-2e")

            _register_source(store, profile, display_name, endpoint)
            _register_source(store, profile, display_name, endpoint)

            rows = store.list_rows("radar_sources")
            self.assertEqual(len(rows), 1)
            conflict_profile, conflict_endpoint = _make_radar_profile(
                source, detail_source_id, details=True, tag="proton-11.0-3",
            )
            with self.assertRaisesRegex(RunBlocked, "persisted_radar_source_conflicts"):
                _register_source(store, conflict_profile, display_name, conflict_endpoint)


if __name__ == "__main__":
    unittest.main()
