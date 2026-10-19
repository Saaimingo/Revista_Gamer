"""Guard and checkpoint tests for the local CODEX-004 editorial experiment."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

from motor_editorial.db import Store
from motor_editorial.editorial import (
    EDITORIAL_EXECUTOR_ID,
    EDITORIAL_MODEL,
    EDITORIAL_PROFILE,
    EDITORIAL_REASONING_EFFORT,
    EDITORIAL_TASK_TYPE,
    SIWCEditorialExecutor,
    build_stage_input,
    normalize_source_packet,
    validate_stage_output,
)
from motor_editorial.orchestration import AgentQueue, TaskDispatcher, TaskFailure
from motor_editorial.orchestration_cli import _editorial_run


def source_packet() -> dict[str, object]:
    return {
        "article_type": "cover",
        "topic": "Rumor sobre a produção da GeForce RTX 5090",
        "research_note": "Pesquisa documental; sem entrevista, teste ou benchmark próprio.",
        "sources": [
            {
                "id": "S1", "title": "GeForce RTX 5090", "publisher": "NVIDIA",
                "url": "https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/",
                "published_at": "current product page", "accessed_at": "2026-10-19",
                "kind": "official", "confidence": "high",
                "evidence": "A página oficial lista Blackwell e 32 GB GDDR7.",
            },
            {
                "id": "S2", "title": "RTX 5090 production report", "publisher": "Tom's Hardware",
                "url": "https://www.tomshardware.com/pc-components/gpus/example",
                "published_at": "2026-10-10", "accessed_at": "2026-10-19",
                "kind": "secondary", "confidence": "medium",
                "evidence": "O texto chama a alegação de não verificada e baseada em vazamento.",
            },
        ],
    }


class EditorialPacketTests(unittest.TestCase):
    def test_packet_requires_https_distinct_publishers_and_primary_plus_secondary(self) -> None:
        packet = normalize_source_packet(source_packet())
        self.assertEqual(packet["article_type"], "cover")
        self.assertEqual([source["id"] for source in packet["sources"]], ["S1", "S2"])

        invalid = source_packet()
        invalid["sources"][0]["url"] = "http://www.nvidia.com/product"
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            normalize_source_packet(invalid)

    def test_packet_rejects_credentials_and_repeated_source_ids(self) -> None:
        invalid = source_packet()
        invalid["sources"][1]["evidence"] = "Bearer ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        with self.assertRaisesRegex(ValueError, "credencial"):
            normalize_source_packet(invalid)

        invalid = source_packet()
        invalid["sources"][1]["id"] = "S1"
        with self.assertRaisesRegex(ValueError, "repetido"):
            normalize_source_packet(invalid)

    def test_stage_builder_requires_completed_prior_checkpoint(self) -> None:
        packet = normalize_source_packet(source_packet())
        with self.assertRaisesRegex(ValueError, "Checkpoint anterior"):
            build_stage_input(stage="outline", packet=packet, previous_outputs={})
        value = build_stage_input(
            stage="outline", packet=packet,
            previous_outputs={"source_analysis": {"claims": []}},
        )
        self.assertIn('"stage":"outline"', value)

    def test_generated_text_must_cite_only_sources_in_packet(self) -> None:
        valid_ids = {"S1", "S2"}
        article = {
            "headline": "RTX 5090",
            "dek": "O que sabemos.",
            "body_markdown": "A página oficial lista 32 GB [S1].",
            "source_ids": ["S1"],
        }
        self.assertEqual(validate_stage_output("draft", article, valid_ids), article)
        invalid = {**article, "body_markdown": "Alegação sem referência [S9]."}
        with self.assertRaises(TaskFailure):
            validate_stage_output("draft", invalid, valid_ids)
        invalid = {**article, "body_markdown": "Alegação sem fonte."}
        with self.assertRaises(TaskFailure):
            validate_stage_output("draft", invalid, valid_ids)

    def test_review_and_correction_cannot_remove_human_checkpoint(self) -> None:
        with self.assertRaises(TaskFailure):
            validate_stage_output("review", {
                "verdict": "pass", "findings": [], "human_review_required": False,
            }, {"S1"})

    def test_source_analysis_and_fact_check_enforce_bounded_claim_lists(self) -> None:
        claim = {
            "claim_id": "C1", "claim": "Afirmação", "source_ids": ["S1"],
            "assessment": "supported", "confidence": "high", "caveat": "",
        }
        with self.assertRaises(TaskFailure):
            validate_stage_output("source_analysis", {"claims": [claim] * 15}, {"S1"})
        finding = {
            "claim": "Afirmação", "source_ids": ["S1"], "status": "supported",
            "confidence": "high", "correction": "",
        }
        with self.assertRaises(TaskFailure):
            validate_stage_output("fact_check", {"findings": [finding] * 19}, {"S1"})
        with self.assertRaises(TaskFailure):
            validate_stage_output("correction", {
                "headline": "RTX 5090", "dek": "Resumo", "body_markdown": "Texto [S1].",
                "source_ids": ["S1"], "remaining_issues": [], "human_review_required": False,
            }, {"S1"})

    def test_editorial_executor_keeps_luna_max_and_persists_stage_checkpoint(self) -> None:
        class StubClient:
            def __init__(self):
                self.calls = 0

            def models(self):
                return [{"slug": EDITORIAL_MODEL, "visibility": "list"}]

            def editorial_stream(self, **kwargs):
                self.calls += 1
                return {
                    "model": EDITORIAL_MODEL,
                    "model_requested": kwargs["model"],
                    "reasoning_effort": EDITORIAL_REASONING_EFFORT,
                    "reasoning_effort_requested": kwargs["reasoning_effort"],
                    "stage": kwargs["stage"],
                    "duration_ms": 5,
                    "external_call_count": 1,
                    "usage": {"input_tokens": 12, "output_tokens": 8, "total_tokens": 20},
                    "structured_output": {
                        "claims": [{
                            "claim_id": "C1", "claim": "Blackwell e 32 GB GDDR7",
                            "source_ids": ["S1"], "assessment": "supported",
                            "confidence": "high", "caveat": "",
                        }],
                    },
                }

        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "motor.sqlite3", Path(directory) / "artifacts")
            queue = AgentQueue(store)
            client = StubClient()
            packet = normalize_source_packet(source_packet())
            task_id = queue.enqueue(
                task_type=EDITORIAL_TASK_TYPE,
                payload={
                    "run_id": "fixture-run", "stage": "source_analysis", "packet": packet,
                    "previous_outputs": {}, "model": EDITORIAL_MODEL,
                    "reasoning_effort": EDITORIAL_REASONING_EFFORT,
                },
                profile=EDITORIAL_PROFILE, executor_id=EDITORIAL_EXECUTOR_ID,
                idempotency_key="editorial-fixture-stage", max_attempts=1,
            )
            outcome = TaskDispatcher(
                queue,
                executors={EDITORIAL_EXECUTOR_ID: SIWCEditorialExecutor(client)},
                profiles={(EDITORIAL_PROFILE.profile_id, EDITORIAL_PROFILE.version): EDITORIAL_PROFILE},
            ).dispatch_one(task_id)
            result = queue.get(task_id).result
            self.assertEqual(outcome.state, "succeeded")
            self.assertEqual(client.calls, 1)
            self.assertEqual(result["reasoning_effort"], "max")
            self.assertTrue(result["human_review_required"])
            self.assertEqual(result["publication_state"], "not_published")

    def test_editorial_executor_rejects_sol_fallback_before_catalog_or_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "motor.sqlite3", Path(directory) / "artifacts")
            queue = AgentQueue(store)
            client = Mock()
            task_id = queue.enqueue(
                task_type=EDITORIAL_TASK_TYPE,
                payload={
                    "run_id": "fixture-run", "stage": "source_analysis",
                    "packet": normalize_source_packet(source_packet()), "previous_outputs": {},
                    "model": "gpt-6.1-sol", "reasoning_effort": "high",
                },
                profile=EDITORIAL_PROFILE, executor_id=EDITORIAL_EXECUTOR_ID,
                idempotency_key="editorial-no-fallback", max_attempts=1,
            )
            outcome = TaskDispatcher(
                queue,
                executors={EDITORIAL_EXECUTOR_ID: SIWCEditorialExecutor(client)},
                profiles={(EDITORIAL_PROFILE.profile_id, EDITORIAL_PROFILE.version): EDITORIAL_PROFILE},
            ).dispatch_one(task_id)
            self.assertEqual(outcome.error_code, "editorial_model_effort_mismatch")
            client.models.assert_not_called()
            client.editorial_stream.assert_not_called()

    def test_pipeline_cli_records_six_sqlite_checkpoints_and_resumes_without_replay(self) -> None:
        structured_outputs = {
            "source_analysis": {"claims": [{
                "claim_id": "C1", "claim": "32 GB GDDR7",
                "source_ids": ["S1"], "assessment": "supported", "confidence": "high", "caveat": "",
            }]},
            "outline": {
                "headline": "RTX 5090", "dek": "O que sabemos.",
                "sections": [{"heading": "Status", "focus": "relatos", "source_ids": ["S2"]}],
            },
            "draft": {
                "headline": "RTX 5090", "dek": "O que sabemos.",
                "body_markdown": "A página oficial lista 32 GB [S1]. A produção não está confirmada [S2].",
                "source_ids": ["S1", "S2"],
            },
            "fact_check": {"findings": [{
                "claim": "32 GB GDDR7", "source_ids": ["S1"], "status": "supported",
                "confidence": "high", "correction": "",
            }]},
            "review": {"verdict": "revise", "findings": ["Rever atribuição do relato."], "human_review_required": True},
            "correction": {
                "headline": "RTX 5090", "dek": "O que sabemos.",
                "body_markdown": "A página oficial lista 32 GB [S1]. A produção não está confirmada [S2].",
                "source_ids": ["S1", "S2"], "remaining_issues": [], "human_review_required": True,
            },
        }

        class StubClient:
            def __init__(self):
                self.calls = 0

            def models(self):
                return [{"slug": EDITORIAL_MODEL, "visibility": "list"}]

            def editorial_stream(self, **kwargs):
                self.calls += 1
                return {
                    "status": "ok", "provider": "openai-siwc", "endpoint": "/v1/responses",
                    "stage": kwargs["stage"], "model_requested": EDITORIAL_MODEL,
                    "model": EDITORIAL_MODEL, "reasoning_effort_requested": "max",
                    "reasoning_effort": "max", "request_started_at": "2026-10-19T00:00:00+00:00",
                    "completed_at": "2026-10-19T00:00:00.005+00:00", "duration_ms": 5,
                    "external_call_count": 1, "usage": {
                        "input_tokens": 10, "output_tokens": 4, "total_tokens": 14,
                        "output_tokens_details": {"reasoning_tokens": 1},
                    },
                    "response_sha256": "fixture", "structured_output": structured_outputs[kwargs["stage"]],
                }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_path = root / "packet.json"
            packet_path.write_text(json.dumps(source_packet(), ensure_ascii=False), encoding="utf-8")
            store = Store(root / "motor.sqlite3", root / "artifacts")
            client = StubClient()
            first_stdout = io.StringIO()
            with patch("motor_editorial.orchestration_cli.SIWCClient", return_value=client), redirect_stdout(first_stdout):
                self.assertEqual(_editorial_run(Namespace(packet=packet_path, run_id=None), store), 0)
            first_result = json.loads(first_stdout.getvalue())
            self.assertEqual(first_result["state"], "awaiting_human_review")
            self.assertEqual(first_result["calls_completed"], 6)
            self.assertEqual(first_result["usage_totals"]["total_tokens"], 84)
            self.assertEqual(first_result["profile_id"], EDITORIAL_PROFILE.profile_id)
            self.assertEqual(first_result["profile_version"], EDITORIAL_PROFILE.version)
            self.assertEqual(first_result["profile_sha256"], EDITORIAL_PROFILE.content_hash)
            self.assertEqual(first_result["word_count"], 13)
            self.assertFalse(first_result["length_target_met"])
            self.assertEqual(client.calls, 6)
            artifact_path = Path(first_result["artifact"])
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            self.assertEqual(len(artifact["stages"]), 6)
            self.assertEqual(artifact["profile_id"], EDITORIAL_PROFILE.profile_id)
            self.assertEqual(artifact["profile_version"], EDITORIAL_PROFILE.version)
            self.assertEqual(artifact["profile_sha256"], EDITORIAL_PROFILE.content_hash)
            self.assertTrue(artifact["human_review_required"])
            self.assertEqual(artifact["publication_state"], "not_published")

            resume_client = StubClient()
            second_stdout = io.StringIO()
            with patch("motor_editorial.orchestration_cli.SIWCClient", return_value=resume_client), redirect_stdout(second_stdout):
                self.assertEqual(_editorial_run(Namespace(packet=packet_path, run_id=first_result["run_id"]), store), 0)
            self.assertEqual(json.loads(second_stdout.getvalue())["calls_completed"], 6)
            self.assertEqual(resume_client.calls, 0)


if __name__ == "__main__":
    unittest.main()
