from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from motor_editorial.agent_contracts import AgentTaskEnvelope
from motor_editorial.db import stable_hash
from motor_editorial.orchestration import AgentTask
from motor_editorial.usage_meter import (
    AgentUsageArtifactStore,
    StoryVersionArchive,
    aggregate_usage_by_persona,
    build_usage_record,
)


def envelope(*, task_id: str, story_id: str, version: str = "1.0") -> AgentTaskEnvelope:
    persona_text = "DNA approved fixture reference, unchanged."
    return AgentTaskEnvelope.from_mapping({
        "schema_version": version,
        "task_id": task_id,
        "run_id": f"run-{task_id}",
        "story_id": story_id,
        "edition_id": "edition-009",
        "role_id": "persona_writer",
        "role_version": "1.0.0",
        "role_hash": "a" * 64,
        "input_payload_hash": "b" * 64,
        "persona_id": "beto-cartucho",
        "persona_version": "0.2",
        "persona_hash": stable_hash(persona_text),
        "input_artifact_refs": [{"ref": "private://input/brief", "sha256": "c" * 64}],
        "source_snapshot_ids": ["snapshot-009"],
        "authorized_tools": [],
        "deadline": None,
        "context_schema_version": "1.0",
        "usage_guardrails": {"max_calls": 1, "max_iterations": 1},
        "idempotency_key": f"idem-{task_id}",
        "correlation_id": f"corr-{task_id}",
        "requires_human_gate": True,
    })


def task(task_id: str, *, attempts: int = 1) -> AgentTask:
    return AgentTask(
        task_id=task_id,
        task_type="agent.role.persona_writer",
        payload={},
        profile_id="siwc-agent-role-runtime",
        profile_version="1.0.0",
        profile_hash="d" * 64,
        executor_id="siwc-agent-role",
        state="running",
        idempotency_key=f"idem-{task_id}",
        attempts=attempts,
        max_attempts=1,
        created_at="2026-10-26T00:00:00Z",
        available_at="2026-10-26T00:00:00Z",
        external_request_started=True,
    )


class UsageMeterTests(unittest.TestCase):
    def test_record_uses_reported_usage_and_keeps_quota_and_cost_separate(self) -> None:
        raw = b'{"title":"Full story"}'
        record = build_usage_record(
            task=task("task-meter", attempts=2),
            envelope=envelope(task_id="task-meter", story_id="story-meter"),
            metadata={
                "model": "gpt-6-luna-2026-10-26",
                "reasoning_effort": "max",
                "response_completed": True,
                "duration_ms": 2345.5,
                "external_call_count": 1,
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 250,
                    "reasoning_tokens": 100,
                    "total_tokens": 370,
                    "input_tokens_details": {"cached_tokens": 40},
                },
            },
            raw_response=raw,
            research_request_count=1,
            schema_status="role_schema_valid",
            story_revision_id="story-meter-r1",
        )

        self.assertEqual(record["input_tokens"], 120)
        self.assertEqual(record["output_tokens"], 250)
        self.assertEqual(record["reasoning_tokens"], 100)
        self.assertEqual(record["total_tokens"], 370)
        self.assertEqual(record["cached_input_tokens"], 40)
        self.assertEqual(record["latency_ms"], 2345.5)
        self.assertEqual(record["retry_count"], 1)
        self.assertIsNone(record["research_index_hits"])
        self.assertIsNone(record["research_cache_hits"])
        self.assertIsNone(record["actual_billed_api_cost"])
        self.assertIsNone(record["franchise_percent"])
        self.assertEqual(record["raw_response_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(record["raw_response_bytes"], len(raw))
        self.assertFalse(record["published"])

    def test_missing_token_or_quota_metrics_remain_null(self) -> None:
        record = build_usage_record(
            task=task("task-missing"),
            envelope=envelope(task_id="task-missing", story_id="story-missing"),
            metadata={"model": "gpt-6-luna", "response_completed": True, "usage": {"output_tokens": 0}},
            raw_response=b"{}",
            research_request_count=0,
            schema_status="role_schema_valid",
        )
        self.assertIsNone(record["input_tokens"])
        self.assertEqual(record["output_tokens"], 0)
        self.assertIsNone(record["reasoning_tokens"])
        self.assertIsNone(record["total_tokens"])
        self.assertIsNone(record["latency_ms"])
        self.assertIsNone(record["franchise_percent"])

    def test_uncertain_attempt_records_known_metrics_without_inventing_usage_or_cost(self) -> None:
        record = build_usage_record(
            task=task("task-uncertain"),
            envelope=envelope(task_id="task-uncertain", story_id="story-uncertain"),
            metadata={
                "model_requested": "gpt-6-luna",
                "reasoning_effort_requested": "max",
                "provider_call_outcome": "uncertain",
                "response_completed": False,
                "duration_ms": 900.0,
                "context_bytes": 4096,
                "blocked_reason": "timeout_after_request_started",
            },
            raw_response=b"",
            research_request_count=None,
            schema_status="provider_call_failed",
        )

        self.assertEqual(record["provider_call_outcome"], "uncertain")
        self.assertEqual(record["calls_uncertain"], 1)
        self.assertEqual(record["calls_failed"], 0)
        self.assertEqual(record["model_requested"], "gpt-6-luna")
        self.assertEqual(record["reasoning_effort_requested"], "max")
        self.assertEqual(record["context_bytes"], 4096)
        self.assertEqual(record["latency_ms"], 900.0)
        self.assertIsNone(record["total_tokens"])
        self.assertIsNone(record["request_count"])
        self.assertIsNone(record["research_network_requests"])
        self.assertEqual(record["blocked_reason"], "timeout_after_request_started")
        self.assertIsNone(record["actual_billed_api_cost"])
        self.assertIsNone(record["franchise_percent"])

    def test_usage_receipts_are_per_attempt_immutable_and_hash_addressed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = AgentUsageArtifactStore(Path(temporary))
            receipt = store.write({
                "schema_version": "AgentUsageRecord.v1",
                "task_id": "task-receipt",
                "attempt_number": 1,
                "persona_id": "nina-prisma",
            })
            path = Path(temporary) / receipt["ref"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), receipt["sha256"])
            with self.assertRaisesRegex(ValueError, "já existe"):
                store.write({
                    "schema_version": "AgentUsageRecord.v1",
                    "task_id": "task-receipt",
                    "attempt_number": 1,
                    "persona_id": "nina-prisma",
                })

    def test_full_original_and_revisions_are_separate_and_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = StoryVersionArchive(Path(temporary))
            original_raw = b'{"title":"Original","body":"Complete original text."}'
            revised_raw = b'{"title":"Revision","body":"Complete revised text."}'
            original = archive.write(
                task=task("task-story-original"),
                envelope=envelope(task_id="task-story-original", story_id="eng-codex-009/persona/story-full"),
                raw_response=original_raw,
                structured_story={
                    "title": "Original",
                    "dek": "Original dek",
                    "sections": [{"heading": "Start", "body": "Every original paragraph is stored intact."}],
                },
                response_ref={"ref": "siwc-role-responses/task-story-original.response.json", "sha256": hashlib.sha256(original_raw).hexdigest()},
                usage_ref={"ref": "agent-usage/task-story-original.attempt-001.json", "sha256": "e" * 64},
            )
            revised = archive.write(
                task=task("task-story-revision"),
                envelope=envelope(task_id="task-story-revision", story_id="eng-codex-009/persona/story-full"),
                raw_response=revised_raw,
                structured_story={
                    "title": "Revision",
                    "dek": "Revision dek",
                    "sections": [{"heading": "Correction", "body": "Every revised paragraph is stored separately."}],
                },
                response_ref={"ref": "siwc-role-responses/task-story-revision.response.json", "sha256": hashlib.sha256(revised_raw).hexdigest()},
                usage_ref=None,
            )

            self.assertEqual(original["version_kind"], "original")
            self.assertEqual(revised["version_kind"], "revision")
            original_manifest = Path(temporary) / original["manifest_ref"]
            revision_manifest = Path(temporary) / revised["manifest_ref"]
            self.assertNotEqual(original_manifest.parent, revision_manifest.parent)
            self.assertEqual(Path(temporary, original["raw_response_ref"]).read_bytes(), original_raw)
            self.assertEqual(Path(temporary, revised["raw_response_ref"]).read_bytes(), revised_raw)
            self.assertIn("Every original paragraph is stored intact.", Path(temporary, original["full_text_ref"]).read_text(encoding="utf-8"))
            self.assertIn("Every revised paragraph is stored separately.", Path(temporary, revised["full_text_ref"]).read_text(encoding="utf-8"))
            index_path = next((Path(temporary) / "story-versions").glob("*/INDEX.json"))
            index = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(index["story_id"], "eng-codex-009/persona/story-full")
            self.assertEqual({item["version_kind"] for item in index["versions"]}, {"original", "revision"})

    def test_summary_is_grouped_by_persona_without_filling_missing_metrics(self) -> None:
        summary = aggregate_usage_by_persona([
            {"task_id": "t1", "persona_id": "ranzinza", "role_id": "persona_writer", "provider_call_status": "completed", "input_tokens": 100, "output_tokens": 200, "reasoning_tokens": 50, "total_tokens": 300, "latency_ms": 10.0},
            {"task_id": "t2", "persona_id": "ranzinza", "role_id": "persona_writer", "provider_call_status": "completed", "input_tokens": 200, "output_tokens": 400, "reasoning_tokens": None, "total_tokens": 600, "latency_ms": 30.0},
        ], research_results={
            "t1": {"index_hit_count": 2, "cache_hit": False, "provider_called": False},
            "t2": {"index_hit_count": 4},
        })

        persona = summary["personas"]["ranzinza"]
        self.assertEqual(persona["call_count"], 2)
        self.assertEqual(persona["metrics"]["total_tokens"]["median"], 450)
        self.assertEqual(persona["metrics"]["reasoning_tokens"]["reported_count"], 1)
        self.assertEqual(persona["metrics"]["research_index_hits"]["median"], 3)
        self.assertEqual(persona["metrics"]["research_cache_hits"]["reported_count"], 1)
        self.assertIsNone(persona["actual_billed_api_cost"])
        self.assertIsNone(persona["franchise_percent"])


if __name__ == "__main__":
    unittest.main()
