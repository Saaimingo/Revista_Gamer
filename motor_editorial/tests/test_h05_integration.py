from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any

from motor_editorial.agent_contracts import (
    AgentTaskEnvelope,
    enqueue_contract_task,
    load_builtin_role_catalog,
)
from motor_editorial.agent_siwc import SIWC_ROLE_EXECUTOR_ID, SIWC_ROLE_EXECUTOR_PROFILE, register_siwc_role_executor
from motor_editorial.agent_workflow import (
    RADAR_RESEARCH_EXECUTOR_ID,
    RADAR_RESEARCH_PROFILE,
    RADAR_RESEARCH_TASK_TYPE,
    ResearchResultRouter,
    ResearchTaskExecutor,
)
from motor_editorial.db import Store, json_dumps, stable_hash
from motor_editorial.factory import run_factory_demo
from motor_editorial.orchestration import AgentQueue, TaskDispatcher, TaskFailure, VALIDATION_PROFILE
from motor_editorial.radar_store import RadarStore
from motor_editorial.research_service import RADAR_INDEX_SCOPE, ResearchService


class FakePersonaWriterClient:
    def __init__(self, output: dict[str, Any]):
        self.output = output
        self.calls: list[dict[str, Any]] = []

    def editorial_stream_with_raw(self, **kwargs: Any) -> dict[str, Any]:
        context = kwargs["context"]
        context.mark_external_started()
        raw = json.dumps(self.output, ensure_ascii=False, separators=(",", ":"))
        metadata = {
            "status": "ok",
            "provider": "offline-fixture",
            "model_requested": "gpt-6-luna",
            "model": "gpt-6-luna-fixture",
            "reasoning_effort_requested": "max",
            "reasoning_effort": "max",
            "request_started_at": "2026-10-26T00:00:00Z",
            "completed_at": "2026-10-26T00:00:02Z",
            "duration_ms": 2000.0,
            "external_call_count": 1,
            "usage": {
                "input_tokens": 100,
                "output_tokens": 250,
                "reasoning_tokens": 75,
                "total_tokens": 350,
            },
            "response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "response_completed": True,
            "store": False,
            "stream": True,
            "output_state": "completed",
        }
        artifact = kwargs["response_sink"](raw, metadata)
        self.calls.append({"stage": kwargs["stage"], "instructions": kwargs["instructions"], "input_text": kwargs["input_text"]})
        return {**metadata, "raw_artifact": artifact, "structured_output": self.output}


class H05IntegrationTests(unittest.TestCase):
    def test_persona_draft_mediation_local_research_and_private_archives_share_one_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dna_path = Path(__file__).resolve().parents[2] / "docs" / "personagens" / "GAMER.md"
            dna_bytes_before = dna_path.read_bytes()
            persona_text = dna_bytes_before.decode("utf-8").strip()
            persona_hash = stable_hash(persona_text)
            story_id = "story-eng009-beto"
            task_id = str(uuid.uuid4())

            approved_question = "Quais plataformas foram confirmadas oficialmente para o jogo?"
            approved_purpose = "confirmar as plataformas no comunicado de lançamento"
            policy = {
                "schema_version": "ResearchMediationPolicy.v1",
                "story_revision_id": f"{story_id}-r1",
                "routes": [{
                    "route_id": "brief-platforms",
                    "question": approved_question,
                    "purpose": approved_purpose,
                    "research_profile_id": "research.games.v1",
                    "research_profile_version": "1.0.0",
                    "required_evidence_kinds": ["official_statement"],
                    "reason": "O brief pede confirmar a lista de plataformas.",
                    "entity_ids": ["entity-requiem"],
                    "preferred_source_ids": [],
                    "preferred_domains": [],
                    "languages": ["pt-BR", "en"],
                    "time_window": {},
                    "versions_configurations": {},
                    "known_evidence_ids": ["evidence-announcement"],
                    "exclusions": ["rumor"],
                }],
            }
            input_payload = {
                "editorial_brief": {"questions": [approved_question]},
                "evidence_dossier": {
                    "evidence": [{"evidence_id": "evidence-announcement", "source_id": "G02"}],
                    "claims": [{
                        "claim_id": "claim-platforms",
                        "evidence_ids": ["evidence-announcement"],
                        "epistemic_status": "official_statement",
                    }],
                },
                "writing_constraints": {"spoiler_policy": "no_major_spoilers", "target_words": 500},
            }
            output = {
                "title": "Duas jornadas, uma lista de plataformas",
                "dek": "Um rascunho curto de integração, sem afirmar teste próprio.",
                "sections": [{
                    "heading": "O anúncio",
                    "body": "A matéria preserva a atribuição e deixa a lacuna de pesquisa explícita.",
                    "evidence_ids": ["evidence-announcement"],
                }],
                "claim_refs": ["claim-platforms"],
                "requested_research": [{"question": approved_question, "purpose": approved_purpose}],
            }

            catalog = load_builtin_role_catalog()
            profile_row = next(row for row in catalog.to_mapping()["profiles"] if row["role_id"] == "persona_writer")
            role = catalog.resolve("persona_writer", profile_row["role_version"], profile_row["profile_sha256"])
            envelope = AgentTaskEnvelope.from_mapping({
                "schema_version": "1.1",
                "task_id": task_id,
                "run_id": "run-eng009-beto",
                "story_id": story_id,
                "edition_id": "edition-eng009",
                "role_id": "persona_writer",
                "role_version": role.role_version,
                "role_hash": role.content_hash,
                "input_payload_hash": stable_hash(json_dumps(input_payload)),
                "persona_id": "beto-cartucho",
                "persona_version": "0.2",
                "persona_hash": persona_hash,
                "input_artifact_refs": [{"ref": "private://eng009/beto/brief", "sha256": "a" * 64}],
                "source_snapshot_ids": ["snapshot-eng009-beto-r1"],
                "authorized_tools": [],
                "deadline": "2026-10-26T01:00:00Z",
                "context_schema_version": "1.0",
                "usage_guardrails": {"max_calls": 1, "max_iterations": 2},
                "idempotency_key": f"eng009:{task_id}",
                "correlation_id": f"{story_id}:{task_id}",
                "requires_human_gate": True,
                "research_mediation_policy": policy,
            })

            store = Store(root / "motor.sqlite3", root / "queue-artifacts")
            queue = AgentQueue(store)
            client = FakePersonaWriterClient(output)
            dispatcher = TaskDispatcher(
                queue,
                executors={},
                profiles={(VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE},
                role_catalog=catalog,
                persona_instruction_resolver=lambda _envelope: persona_text,
                deterministic_task_routes={RADAR_RESEARCH_TASK_TYPE: RADAR_RESEARCH_EXECUTOR_ID},
            )
            private_artifacts = root / "private" / "ensaios-009"
            register_siwc_role_executor(
                dispatcher,
                client,
                artifact_root=private_artifacts,
                model="gpt-6-luna",
                reasoning_effort="max",
                catalog_models={"gpt-6-luna"},
            )

            radar = RadarStore(root / "radar.sqlite3")
            service = ResearchService(store=radar, provider=None)
            dispatcher.executors[RADAR_RESEARCH_EXECUTOR_ID] = ResearchTaskExecutor(service, catalog)
            dispatcher.profiles[(RADAR_RESEARCH_PROFILE.profile_id, RADAR_RESEARCH_PROFILE.version)] = RADAR_RESEARCH_PROFILE
            dispatcher.result_router = ResearchResultRouter(
                queue=queue,
                catalog=catalog,
                executor_profiles={
                    (SIWC_ROLE_EXECUTOR_PROFILE.profile_id, SIWC_ROLE_EXECUTOR_PROFILE.version): SIWC_ROLE_EXECUTOR_PROFILE,
                    (RADAR_RESEARCH_PROFILE.profile_id, RADAR_RESEARCH_PROFILE.version): RADAR_RESEARCH_PROFILE,
                },
            )

            enqueued = enqueue_contract_task(
                queue,
                envelope,
                input_payload,
                catalog=catalog,
                executor_profile=SIWC_ROLE_EXECUTOR_PROFILE,
                executor_id=SIWC_ROLE_EXECUTOR_ID,
                max_attempts=1,
            )
            self.assertEqual(enqueued, task_id)
            writer_outcome = dispatcher.dispatch_one(task_id)
            self.assertEqual(writer_outcome.state, "succeeded")
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(dna_path.read_bytes(), dna_bytes_before)

            parent = queue.get(task_id)
            request = parent.result["requested_research"]
            self.assertEqual(request["allowed_scope"], [RADAR_INDEX_SCOPE])
            self.assertEqual(request["story_revision_id"], f"{story_id}-r1")
            self.assertEqual(request["requester_persona_id"], "beto-cartucho")
            research_task = next(item for item in queue.list_tasks(limit=100) if item.task_type == RADAR_RESEARCH_TASK_TYPE)
            research_outcome = dispatcher.dispatch_one(research_task.task_id)
            self.assertEqual(research_outcome.state, "succeeded", research_outcome.error_code)
            research_result = queue.get(research_task.task_id).result
            self.assertFalse(research_result["provider_called"])
            self.assertEqual(research_result["index_hit_count"], 0)
            self.assertEqual(research_result["packet"]["status"], "not_found")
            self.assertEqual(len(client.calls), 1, "retorno Radar fica enfileirado sem uma segunda inferência neste teste")

            usage_files = list((private_artifacts / "agent-usage").glob("*.json"))
            self.assertEqual(len(usage_files), 1)
            usage = json.loads(usage_files[0].read_text(encoding="utf-8"))
            self.assertEqual(usage["persona_id"], "beto-cartucho")
            self.assertEqual(usage["input_tokens"], 100)
            self.assertEqual(usage["reasoning_tokens"], 75)
            self.assertEqual(usage["total_tokens"], 350)
            self.assertEqual(usage["latency_ms"], 2000.0)
            self.assertIsNone(usage["research_request_count"])
            self.assertEqual(usage["research_suggestion_count"], 1)
            self.assertIsNone(usage["research_network_requests"])
            self.assertEqual(usage["model_requested"], "gpt-6-luna")
            self.assertEqual(usage["reasoning_effort_requested"], "max")
            self.assertGreater(usage["context_bytes"], 0)
            self.assertEqual(usage["provider_call_outcome"], "success")
            self.assertEqual(usage["calls_success"], 1)
            self.assertIsNone(usage["actual_billed_api_cost"])
            self.assertIsNone(usage["franchise_percent"])

            story_index = next((private_artifacts / "story-versions").glob("*/INDEX.json"))
            index = json.loads(story_index.read_text(encoding="utf-8"))
            self.assertEqual(len(index["versions"]), 1)
            full_text = private_artifacts / index["versions"][0]["full_text_ref"]
            self.assertIn("Duas jornadas, uma lista de plataformas", full_text.read_text(encoding="utf-8"))
            raw_copy = private_artifacts / index["versions"][0]["manifest_ref"]
            manifest = json.loads(raw_copy.read_text(encoding="utf-8"))
            raw_saved = private_artifacts / manifest["raw_response_ref"]
            self.assertEqual(hashlib.sha256(raw_saved.read_bytes()).hexdigest(), manifest["raw_response_sha256"])
            self.assertEqual(manifest["version_kind"], "original")

            with self.assertRaises(TaskFailure) as pending_bridge:
                run_factory_demo(
                    store,
                    queue=queue,
                    dispatcher=dispatcher,
                    persona_draft_task_id=task_id,
                    persona_draft_artifact_root=private_artifacts,
                    persona_draft_evidence_rows=[{"evidence_id": "evidence-announcement", "source_id": "G02"}],
                    persona_draft_valid_source_ids={"G02"},
                )
            self.assertEqual(pending_bridge.exception.code, "factory_persona_bridge_research_pending")

            second_task_id = str(uuid.uuid4())
            second_story_id = "story-eng009-beto-bridge"
            second_policy = {**policy, "story_revision_id": f"{second_story_id}-r1"}
            second_envelope_value = envelope.to_dict()
            second_envelope_value.update({
                "task_id": second_task_id,
                "story_id": second_story_id,
                "idempotency_key": f"eng009:{second_task_id}",
                "correlation_id": f"{second_story_id}:{second_task_id}",
                "research_mediation_policy": second_policy,
            })
            second_envelope = AgentTaskEnvelope.from_mapping(second_envelope_value)
            client.output = {**output, "requested_research": []}
            self.assertEqual(enqueue_contract_task(
                queue,
                second_envelope,
                input_payload,
                catalog=catalog,
                executor_profile=SIWC_ROLE_EXECUTOR_PROFILE,
                executor_id=SIWC_ROLE_EXECUTOR_ID,
                max_attempts=1,
            ), second_task_id)
            second_outcome = dispatcher.dispatch_one(second_task_id)
            self.assertEqual(second_outcome.state, "succeeded", second_outcome.error_code)
            self.assertEqual(len(client.calls), 2)
            self.assertEqual(dna_path.read_bytes(), dna_bytes_before)

            bridge = run_factory_demo(
                store,
                queue=queue,
                dispatcher=dispatcher,
                persona_draft_task_id=second_task_id,
                persona_draft_artifact_root=private_artifacts,
                persona_draft_evidence_rows=[{"evidence_id": "evidence-announcement", "source_id": "G02"}],
                persona_draft_valid_source_ids={"G02"},
            )
            self.assertEqual(bridge["status"], "awaiting_human_review")
            self.assertEqual(bridge["publication_state"], "not_published")
            self.assertEqual(bridge["fact_check_status"], "not_run")
            self.assertEqual(bridge["editorial_review_status"], "not_run")
            self.assertIn("G02", bridge["source_ids"])
            factory_task = queue.get(bridge["factory_task_id"])
            self.assertEqual(factory_task.task_type, "factory.persona_draft_bridge")
            persisted_factory_json = json.dumps({"payload": factory_task.payload, "result": factory_task.result})
            self.assertNotIn("Duas jornadas, uma lista de plataformas", persisted_factory_json)
            self.assertNotIn("A matéria preserva a atribuição", persisted_factory_json)
            converted = json.loads((private_artifacts / bridge["article_draft_ref"]).read_text(encoding="utf-8"))
            self.assertIn("Duas jornadas, uma lista de plataformas", converted["headline"])
            self.assertIn("[G02]", converted["body_markdown"])
            self.assertEqual(
                hashlib.sha256((private_artifacts / bridge["article_draft_ref"]).read_bytes()).hexdigest(),
                bridge["article_draft_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
