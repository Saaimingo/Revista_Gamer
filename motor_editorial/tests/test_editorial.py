"""Guard and checkpoint tests for the local CODEX-004 editorial experiment."""

from __future__ import annotations

import io
import json
import re
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
    EDITORIAL_STAGES,
    SIWCEditorialExecutor,
    article_revision_sha256,
    build_stage_input,
    normalize_source_packet,
    review_matches_revision,
    review_next_action,
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


def stage_outputs(*, review_verdict: str = "revise", final_verdict: str = "pass") -> dict[str, dict[str, object]]:
    draft_body = "A página oficial lista 32 GB [S1]. A produção não está confirmada [S2]."
    corrected_body = draft_body + " A fala posterior continua atribuída a relatos [S2]."
    return {
        "source_analysis": {"claims": [{
            "claim_id": "C1", "claim": "32 GB GDDR7", "source_ids": ["S1"],
            "evidence_excerpt": "A ficha oficial lista 32 GB GDDR7.",
            "assessment": "supported", "confidence": "high", "caveat": "",
        }]},
        "outline": {
            "headline": "RTX 5090", "dek": "O que sabemos.",
            "sections": [{"heading": "Status", "focus": "relatos", "source_ids": ["S2"]}],
        },
        "draft": {
            "headline": "RTX 5090", "dek": "O que sabemos.",
            "body_markdown": draft_body, "source_ids": ["S1", "S2"],
        },
        "fact_check": {"findings": [{
            "claim": "32 GB GDDR7", "source_ids": ["S1"], "status": "supported",
            "confidence": "high", "correction": "",
        }]},
        "review": {
            "verdict": review_verdict,
            "findings": [] if review_verdict == "pass" else ["Rever a atribuição do relato."],
            "human_review_required": True,
        },
        "correction": {
            "headline": "RTX 5090", "dek": "O que sabemos.",
            "body_markdown": corrected_body, "source_ids": ["S1", "S2"],
            "remaining_issues": [], "human_review_required": True,
        },
        "final_fact_check": {"findings": [{
            "claim": "32 GB GDDR7", "source_ids": ["S1"], "status": "supported",
            "confidence": "high", "correction": "",
        }]},
        "final_review": {
            "verdict": final_verdict,
            "findings": [] if final_verdict == "pass" else ["Requer decisão humana sobre pendência."],
            "human_review_required": True,
        },
    }


class PipelineStubClient:
    def __init__(self, *, review_verdict: str = "revise", final_verdict: str = "pass") -> None:
        self.outputs = stage_outputs(review_verdict=review_verdict, final_verdict=final_verdict)
        self.catalog_calls = 0
        self.stage_calls: list[str] = []

    def models(self):
        self.catalog_calls += 1
        return [{"slug": EDITORIAL_MODEL, "visibility": "list"}]

    def editorial_stream(self, **kwargs):
        stage = kwargs["stage"]
        self.stage_calls.append(stage)
        return {
            "status": "ok", "provider": "openai-siwc", "endpoint": "/v1/responses",
            "stage": stage, "model_requested": EDITORIAL_MODEL,
            "model": EDITORIAL_MODEL, "reasoning_effort_requested": "max",
            "reasoning_effort": "max", "request_started_at": "2026-10-19T00:00:00+00:00",
            "completed_at": "2026-10-19T00:00:00.005+00:00", "duration_ms": 5,
            "external_call_count": 1, "usage": {
                "input_tokens": 10, "output_tokens": 4, "total_tokens": 14,
                "output_tokens_details": {"reasoning_tokens": 1},
            },
            "response_sha256": "fixture", "structured_output": self.outputs[stage],
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

    def test_draft_context_uses_compact_attributed_evidence_and_verification_keeps_full_evidence(self) -> None:
        raw = source_packet()
        raw["sources"][0]["evidence"] = "FULL_SOURCE_EVIDENCE_MARKER " + raw["sources"][0]["evidence"]
        packet = normalize_source_packet(raw)
        prior = {
            "source_analysis": {"claims": [{
                "claim_id": "C1", "claim": "32 GB GDDR7", "source_ids": ["S1"],
                "evidence_excerpt": "A ficha oficial lista 32 GB GDDR7.",
                "assessment": "supported", "confidence": "high", "caveat": "",
            }]},
            "outline": {
                "headline": "RTX 5090", "dek": "Resumo.",
                "sections": [{"heading": "Status", "focus": "relatos", "source_ids": ["S2"]}],
            },
        }
        draft_input = build_stage_input(stage="draft", packet=packet, previous_outputs=prior)
        fact_check_input = build_stage_input(
            stage="fact_check", packet=packet, previous_outputs={
                "draft": {"headline": "RTX 5090", "dek": "Resumo", "body_markdown": "Texto [S1].", "source_ids": ["S1"]},
            },
        )
        self.assertNotIn("FULL_SOURCE_EVIDENCE_MARKER", draft_input)
        self.assertIn("evidence_excerpt", draft_input)
        self.assertIn("FULL_SOURCE_EVIDENCE_MARKER", fact_check_input)

    def test_review_fingerprint_changes_when_reviewed_text_changes(self) -> None:
        stages = stage_outputs()
        draft = stages["draft"]
        corrected = stages["correction"]
        review = {
            "verdict": "revise", "findings": ["Rever a atribuição."],
            "human_review_required": True,
            "reviewed_revision_sha256": article_revision_sha256(draft),
        }
        self.assertTrue(review_matches_revision(review, draft))
        self.assertFalse(review_matches_revision(review, corrected))
        self.assertNotEqual(article_revision_sha256(draft), article_revision_sha256(corrected))
        changed_after_review = dict(draft, body_markdown=draft["body_markdown"] + " Alteração posterior [S1].")
        self.assertFalse(review_matches_revision(review, changed_after_review))

    def test_review_directs_at_most_one_correction_of_the_same_version(self) -> None:
        draft_hash = "a" * 64
        review = {"draft_hash": draft_hash, "verdict": "revise", "findings": ["Ajustar o início."], "human_review_required": True}
        self.assertEqual(review_next_action(review, draft_hash, corrections_attempted=0), "correct")
        self.assertEqual(review_next_action(review, draft_hash, corrections_attempted=1), "hold_correction_limit")
        self.assertEqual(review_next_action({**review, "findings": []}, draft_hash, corrections_attempted=0), "hold_missing_findings")
        self.assertEqual(review_next_action({**review, "verdict": "hold"}, draft_hash, corrections_attempted=0), "hold")
        self.assertEqual(review_next_action({**review, "verdict": "pass"}, draft_hash, corrections_attempted=0), "await_human_approval")
        with self.assertRaises(TaskFailure):
            review_next_action(review, "b" * 64, corrections_attempted=0)
        with self.assertRaises(TaskFailure):
            review_next_action({**review, "human_review_required": False}, draft_hash, corrections_attempted=0)

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
        passing_review = validate_stage_output("review", {
            "verdict": "pass", "findings": [], "human_review_required": True,
        }, {"S1"})
        self.assertEqual(passing_review["verdict"], "pass")
        with self.assertRaises(TaskFailure):
            validate_stage_output("review", {
                "verdict": "pass", "findings": [], "human_review_required": False,
            }, {"S1"})
        with self.assertRaises(TaskFailure):
            validate_stage_output("review", {
                "verdict": "pass", "findings": ["Ainda há pendência."],
                "human_review_required": True,
            }, {"S1"})

    def test_source_analysis_and_fact_check_enforce_bounded_claim_lists(self) -> None:
        claim = {
            "claim_id": "C1", "claim": "Afirmação", "source_ids": ["S1"],
            "evidence_excerpt": "Trecho verificável.",
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
        too_long = {**finding, "correction": "x" * 241}
        with self.assertRaises(TaskFailure):
            validate_stage_output("fact_check", {"findings": [too_long]}, {"S1"})
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
                            "evidence_excerpt": "A ficha oficial lista 32 GB GDDR7.",
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

    def _run_pipeline(self, store, client, packet_path, *, run_id=None, source_collection_duration_ms=None):
        stdout = io.StringIO()
        args = Namespace(
            packet=packet_path, run_id=run_id,
            source_collection_duration_ms=source_collection_duration_ms,
        )
        with patch("motor_editorial.orchestration_cli.SIWCClient", return_value=client), redirect_stdout(stdout):
            code = _editorial_run(args, store)
        return code, json.loads(stdout.getvalue())

    def test_pipeline_rechecks_corrected_revision_uses_one_catalog_check_and_resumes_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_path = root / "packet.json"
            packet_path.write_text(json.dumps(source_packet(), ensure_ascii=False), encoding="utf-8")
            store = Store(root / "motor.sqlite3", root / "artifacts")
            client = PipelineStubClient()
            code, summary = self._run_pipeline(
                store, client, packet_path, source_collection_duration_ms=182000
            )

            self.assertEqual(code, 0)
            self.assertEqual(summary["state"], "awaiting_human_approval")
            self.assertEqual(summary["execution_status"], "completed")
            self.assertEqual(summary["editorial_status"], "awaiting_human_approval")
            self.assertEqual(summary["human_approval_status"], "pending")
            self.assertEqual(summary["calls_completed"], 8)
            self.assertEqual(summary["usage_totals"]["total_tokens"], 112)
            self.assertEqual(summary["usage_totals"]["output_tokens"], 32)
            self.assertEqual(summary["usage_totals"]["reasoning_tokens"], 8)
            self.assertTrue(summary["reasoning_tokens_are_subset_of_output_tokens"])
            self.assertEqual(summary["catalog"]["request_count"], 1)
            self.assertEqual(client.catalog_calls, 1)
            self.assertEqual(client.stage_calls, list(EDITORIAL_STAGES))
            self.assertEqual(summary["source_collection_duration_ms"], 182000)
            self.assertIsInstance(summary["source_packet_validation_duration_ms"], (int, float))
            self.assertEqual(summary["profile_id"], EDITORIAL_PROFILE.profile_id)
            self.assertEqual(summary["profile_version"], "1.2.0")
            self.assertEqual(summary["profile_sha256"], EDITORIAL_PROFILE.content_hash)
            self.assertFalse(summary["length_target_met"])
            self.assertEqual(summary["sample_classification"], "technical_sample")
            self.assertFalse(summary["ready_for_publication"])
            self.assertTrue(summary["current_review_matches_final_article"])
            artifact = json.loads(Path(summary["artifact"]).read_text(encoding="utf-8"))
            self.assertEqual(
                summary["word_count"], len(artifact["final_article"]["body_markdown"].split())
            )
            self.assertEqual(
                summary["reviewed_revision_sha256"],
                article_revision_sha256(artifact["final_article"]),
            )
            draft_hash = artifact["outputs"]["review"]["reviewed_revision_sha256"]
            corrected_hash = artifact["outputs"]["final_review"]["reviewed_revision_sha256"]
            self.assertNotEqual(draft_hash, corrected_hash)
            self.assertEqual(
                artifact["outputs"]["final_fact_check"]["checked_revision_sha256"], corrected_hash
            )

            self.assertEqual(len(artifact["stages"]), 8)
            self.assertEqual(artifact["profile_version"], "1.2.0")
            self.assertTrue(artifact["human_review_required"])
            self.assertEqual(artifact["publication_state"], "not_published")
            self.assertEqual(artifact["source_ids"], ["S1", "S2"])

            resume_client = PipelineStubClient()
            resume_code, resumed = self._run_pipeline(
                store, resume_client, packet_path, run_id=summary["run_id"],
                source_collection_duration_ms=182000,
            )
            self.assertEqual(resume_code, 0)
            self.assertEqual(resumed["calls_completed"], 8)
            self.assertEqual(resume_client.catalog_calls, 1)
            self.assertEqual(resume_client.stage_calls, [])

    def test_initial_pass_stops_at_human_approval_without_correction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_path = root / "packet.json"
            packet_path.write_text(json.dumps(source_packet(), ensure_ascii=False), encoding="utf-8")
            store = Store(root / "motor.sqlite3", root / "artifacts")
            client = PipelineStubClient(review_verdict="pass")
            code, summary = self._run_pipeline(store, client, packet_path)

            self.assertEqual(code, 0)
            self.assertEqual(summary["execution_status"], "completed")
            self.assertEqual(summary["editorial_status"], "awaiting_human_approval")
            self.assertEqual(summary["human_approval_status"], "pending")
            self.assertEqual(client.stage_calls, list(EDITORIAL_STAGES[:5]))
            artifact = json.loads(Path(summary["artifact"]).read_text(encoding="utf-8"))
            self.assertNotIn("correction", artifact["outputs"])
            self.assertEqual(artifact["final_article"], artifact["outputs"]["draft"])
            self.assertEqual(
                summary["reviewed_revision_sha256"],
                article_revision_sha256(artifact["final_article"]),
            )
            self.assertTrue(summary["current_review_matches_final_article"])
            self.assertFalse(summary["ready_for_publication"])
            self.assertEqual(summary["publication_state"], "not_published")

    def test_hold_blocks_before_correction_and_preserves_human_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_path = root / "packet.json"
            packet_path.write_text(json.dumps(source_packet(), ensure_ascii=False), encoding="utf-8")
            store = Store(root / "motor.sqlite3", root / "artifacts")
            client = PipelineStubClient(review_verdict="hold")
            code, summary = self._run_pipeline(store, client, packet_path)
            self.assertEqual(code, 0)
            self.assertEqual(summary["execution_status"], "completed")
            self.assertEqual(summary["editorial_status"], "blocked_human_decision")
            self.assertEqual(summary["human_approval_status"], "human_action_required_hold")
            self.assertEqual(client.stage_calls, list(EDITORIAL_STAGES[:5]))
            artifact = json.loads(Path(summary["artifact"]).read_text(encoding="utf-8"))
            self.assertNotIn("correction", artifact["outputs"])
            self.assertEqual(artifact["final_article"], artifact["outputs"]["draft"])
            self.assertTrue(summary["current_review_matches_final_article"])
            self.assertEqual(summary["publication_state"], "not_published")

    def test_second_review_revise_requires_human_and_never_starts_another_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_path = root / "packet.json"
            packet_path.write_text(json.dumps(source_packet(), ensure_ascii=False), encoding="utf-8")
            store = Store(root / "motor.sqlite3", root / "artifacts")
            client = PipelineStubClient(final_verdict="revise")
            code, summary = self._run_pipeline(store, client, packet_path)

        self.assertEqual(code, 0)
        self.assertEqual(summary["execution_status"], "completed")
        self.assertEqual(summary["editorial_status"], "blocked_human_decision")
        self.assertEqual(summary["human_approval_status"], "human_action_required_review")
        self.assertEqual(client.stage_calls.count("correction"), 1)
        self.assertEqual(client.stage_calls.count("final_review"), 1)
        self.assertEqual(len(client.stage_calls), 8)
        self.assertTrue(summary["current_review_matches_final_article"])
        self.assertFalse(summary["ready_for_publication"])

    def test_run_id_cannot_reuse_checkpoints_from_older_profile(self) -> None:
        from motor_editorial.orchestration import AgentProfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_path = root / "packet.json"
            packet_path.write_text(json.dumps(source_packet(), ensure_ascii=False), encoding="utf-8")
            store = Store(root / "motor.sqlite3", root / "artifacts")
            old_profile = AgentProfile(
                profile_id=EDITORIAL_PROFILE.profile_id, version="1.1.0",
                instructions="Perfil historico de fixture.",
            )
            run_id = "c2aa11e8-019e-4cee-9e38-a3a12109c2aa"
            AgentQueue(store).enqueue(
                task_type=EDITORIAL_TASK_TYPE,
                payload={"run_id": run_id, "stage": "source_analysis"},
                profile=old_profile, executor_id=EDITORIAL_EXECUTOR_ID,
                idempotency_key=f"editorial:{run_id}:source_analysis", max_attempts=1,
            )
            client = PipelineStubClient()
            with patch("motor_editorial.orchestration_cli.SIWCClient", return_value=client):
                with self.assertRaisesRegex(ValueError, "nova run_id"):
                    _editorial_run(
                        Namespace(packet=packet_path, run_id=run_id), store
                    )
            self.assertEqual(client.catalog_calls, 0)

    def test_interrupted_run_resumes_from_durable_checkpoints_without_replaying_completed_stages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_path = root / "packet.json"
            packet_path.write_text(json.dumps(source_packet(), ensure_ascii=False), encoding="utf-8")
            store = Store(root / "motor.sqlite3", root / "artifacts")
            run_id = "ef78f680-d7ab-46cb-9712-864e9eadc433"
            first_client = PipelineStubClient()
            original_dispatch = TaskDispatcher.dispatch_one
            dispatch_count = {"value": 0}

            def interrupt_after_three(dispatcher, task_id=None, *, now=None):
                if dispatch_count["value"] == 3:
                    raise KeyboardInterrupt()
                dispatch_count["value"] += 1
                return original_dispatch(dispatcher, task_id, now=now)

            with patch("motor_editorial.orchestration_cli.SIWCClient", return_value=first_client):
                with patch.object(TaskDispatcher, "dispatch_one", new=interrupt_after_three):
                    with self.assertRaises(KeyboardInterrupt):
                        _editorial_run(Namespace(packet=packet_path, run_id=run_id), store)
            self.assertEqual(first_client.stage_calls, list(EDITORIAL_STAGES[:3]))

            resumed_client = PipelineStubClient()
            code, summary = self._run_pipeline(
                store, resumed_client, packet_path, run_id=run_id
            )
            self.assertEqual(code, 0)
            self.assertEqual(resumed_client.stage_calls, list(EDITORIAL_STAGES[3:]))
            self.assertEqual(summary["calls_completed"], 8)
            self.assertEqual(summary["execution_status"], "completed")

    def test_sample_artifacts_are_utf8_and_keep_only_source_packet_ids(self) -> None:
        root = Path(__file__).resolve().parents[2]
        sample_path = root / "docs/engenharia/evidencias/AMOSTRA-CAPA-RTX5090-CODEX-004.md"
        packet_path = root / "docs/engenharia/evidencias/ENG-CODEX-004-RTX5090-PACOTE-FONTES.json"
        metrics_path = root / "docs/engenharia/evidencias/ENG-CODEX-004-METRICAS-LUNA-MAX-2026-10-19.json"
        report_path = root / "docs/engenharia/RELATORIO-ENG-CODEX-004-EXECUCAO-LUNA-MAX-2026-10-19.md"
        texts = {
            path: path.read_bytes().decode("utf-8", errors="strict")
            for path in (sample_path, packet_path, metrics_path, report_path)
        }
        for artifact_text in texts.values():
            self.assertNotIn("\ufffd", artifact_text)

        sample = texts[sample_path]
        for corrupted in ("revis?o", "n?o", "est?", "publica??o", "Execu??o", "Extens?o", "900?1.200", ") ?"):
            self.assertNotIn(corrupted, sample)
        self.assertIn("Nota de normaliza", sample)
        packet = json.loads(texts[packet_path])
        packet_ids = {source["id"] for source in packet["sources"]}
        cited_ids = set(re.findall(r"\[([A-Z][0-9]{1,3})\]", sample.split("## Fontes do pacote")[0]))
        reference_ids = set(re.findall(r"(?m)^- \[([A-Z][0-9]{1,3})\]", sample))
        self.assertTrue(cited_ids <= packet_ids)
        self.assertEqual(reference_ids, packet_ids)
        self.assertEqual(len(packet_ids), 6)
        self.assertEqual(packet_ids, {"S1", "S2", "S3", "S4", "S5", "S6"})
        self.assertIn("578 palavras", sample)
        self.assertIn("amostra t", sample.lower())


if __name__ == "__main__":
    unittest.main()
