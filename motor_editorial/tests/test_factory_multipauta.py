from __future__ import annotations

import hashlib
import json
import socket
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import patch
from xml.sax.saxutils import escape

from motor_editorial.agent_contracts import (
    AgentRoleCatalog,
    AgentRoleProfile,
    AgentTaskEnvelope,
    ResearchPacket,
    ResearchRequest,
    enqueue_contract_task,
    envelope_from_payload,
    load_builtin_role_catalog,
)
from motor_editorial.agent_workflow import (
    RADAR_RESEARCH_EXECUTOR_ID,
    RADAR_RESEARCH_PROFILE,
    RADAR_RESEARCH_TASK_ROUTES,
    RADAR_RESEARCH_TASK_TYPE,
    ResearchResultRouter,
    ResearchTaskExecutor,
)
from motor_editorial.db import Store, json_dumps, stable_hash
from motor_editorial.editorial import EDITORIAL_TASK_TYPE
from motor_editorial.factory import (
    FACTORY_EXECUTOR_ID,
    FACTORY_TASK_ROUTES,
    GATE_PROFILE,
    LAYOUT_PROFILE,
    MEDIA_PROFILE,
    PACKAGE_PROFILE,
    EDITORIAL_PROFILE,
    FactoryStoryRun,
    SyntheticFactoryExecutor,
    run_factory_multipauta_demo,
)
from motor_editorial.orchestration import AgentQueue, TaskDispatcher, VALIDATION_PROFILE
from motor_editorial.radar_connectors import (
    HttpResponse,
    PerOriginLimiter,
    RadarConnectorService,
    SourceProfile,
)
from motor_editorial.radar_incremental import IncrementalRadarService
from motor_editorial.radar_store import RadarStore
from motor_editorial.radar_triage import RadarGeneralService, _TRIAGE_EXECUTOR_PROFILE
from motor_editorial.research_service import RADAR_INDEX_SCOPE, ResearchService


NOW = "2026-10-25T18:00:00+00:00"
FIXTURE_DIR = Path(__file__).parents[1] / "fixtures"


class FixtureResolver:
    def __call__(self, host: str, port: int, *, type: int) -> list[tuple[Any, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))]


class FixtureTransport:
    def __init__(self, body: bytes):
        self.body = body
        self.calls: list[str] = []

    def request(
        self, url: str, pinned_address: str, *, headers: Mapping[str, str], timeout_seconds: float,
        max_response_bytes: int, allow_loopback_http: bool = False,
    ) -> HttpResponse:
        self.calls.append(url)
        return HttpResponse(200, {"content-type": "application/rss+xml", "etag": '"e15-fixture"'}, self.body)


class SyntheticEditorialRoleExecutor:
    executor_id = "synthetic-e15-role"

    def __init__(self, research_profiles: Mapping[str, str]) -> None:
        self.research_profiles = dict(research_profiles)
        self.calls: list[tuple[str, str, bool]] = []
        self.persona_bindings: list[tuple[str, str, str]] = []
        self.persona_packet_hashes: list[tuple[str, str | None]] = []

    def execute(self, task, profile, context):
        envelope = context.agent_task_envelope
        packet = context.agent_invocation_context.untrusted_evidence["packet"]
        self.calls.append((envelope.role_id, envelope.story_id, packet is not None))
        if envelope.role_id == "persona_writer":
            packet_data = context.agent_invocation_context.untrusted_evidence["packet"]
            self.persona_packet_hashes.append((
                envelope.persona_id or "",
                packet_data.get("content_hash") if packet_data else None,
            ))
            persona_sections = [
                section for section in context.agent_invocation_context.trusted_instruction_sections
                if section.source.startswith("persona:")
            ]
            self.persona_bindings.extend(
                (envelope.persona_id or "", section.source, section.text)
                for section in persona_sections
            )
        request = None
        if envelope.role_id == "evidence_investigator" and packet is None:
            request = make_research_request(
                envelope,
                task.payload["input"],
                self.research_profiles[envelope.story_id],
            )
        digest = hashlib.sha256(f"e15-result:{envelope.task_id}".encode("utf-8")).hexdigest()
        return {
            "schema_version": "1.0",
            "task_id": envelope.task_id,
            "status": "needs_more_research" if request else "completed",
            "output_schema_version": "1.0.0",
            "artifact_ref": {"ref": f"fixture://e15/result/{envelope.task_id}", "sha256": digest},
            "material_claims": [],
            "requested_research": request.to_dict() if request else None,
            "open_questions": ["fixture evidence gap"] if request else [],
            "observed_constraints": ["fixture only; deterministic executor"],
            "input_hash": envelope.input_hash,
            "output_hash": digest,
            "created_at": NOW,
            "model_used": None,
            "model_effort": None,
            "usage_reported": None,
            "next_action_suggestion": None,
        }


def make_research_request(
    envelope: AgentTaskEnvelope, input_payload: Mapping[str, Any], profile_id: str,
) -> ResearchRequest:
    question = str(input_payload["question"])
    return ResearchRequest.from_mapping({
        "schema_version": "1.1",
        "request_id": f"e15-research-{envelope.story_id}",
        "parent_task_id": envelope.task_id,
        "story_id": envelope.story_id,
        "story_revision_id": f"revision-{envelope.story_id}",
        "requester_role_id": envelope.role_id,
        "requester_persona_id": envelope.persona_id,
        "research_profile_id": profile_id,
        "research_profile_version": "1.0.0",
        "question": question,
        "queries": [question],
        "entity_ids": [],
        "required_evidence_kinds": ["official_statement"],
        "preferred_source_ids": [],
        "preferred_domains": [],
        "languages": ["pt-BR"],
        "time_window": {},
        "versions_configurations": {},
        "known_evidence_ids": [],
        "exclusions": [],
        "max_sources": 2,
        "max_requests": 1,
        "max_bytes": 10000,
        "max_duration_seconds": 10,
        "reason": "Ensaio multipauta E15 com índice local sintético.",
        "allowed_scope": [RADAR_INDEX_SCOPE],
        "idempotency_key": f"e15-research-idempotency:{envelope.story_id}",
        "human_gate_if_sensitive": True,
    })


def make_rss(items: list[tuple[str, str, str]]) -> bytes:
    content = ["<rss><channel>"]
    for index, (title, url, description) in enumerate(items, start=1):
        content.append(
            "<item>"
            f"<title>{escape(title)}</title><link>{escape(url)}</link>"
            f"<guid>e15-item-{index}</guid><pubDate>Sun, 25 Oct 2026 17:0{index}:00 GMT</pubDate>"
            f"<description><![CDATA[<p>{description}</p>]]></description>"
            "</item>"
        )
    content.append("</channel></rss>")
    return "".join(content).encode("utf-8")


def make_source_profile() -> SourceProfile:
    host = "e15-fiction.example.invalid"
    return SourceProfile.from_mapping({
        "source_id": "source-e15-fixture",
        "connector_kind": "rss_atom",
        "root_url": f"https://{host}/",
        "feed_url": f"https://{host}/feed?edition=pt&format=rss",
        "allowed_hosts": [host],
        "allowed_operations": ["feed_read"],
        "access_policy": "allowed",
        "terms_checked_at": "2026-10-24",
        "robots_policy": "allowed",
        "robots_checked_at": "2026-10-24",
        "robots_rules_by_host": {host: "User-agent: *\nAllow: /"},
        "min_poll_interval_seconds": 1,
        "max_response_bytes": 100000,
        "timeout_seconds": 2,
        "max_redirects": 1,
    })


def make_investigator_task(queue: AgentQueue, catalog: AgentRoleCatalog, story_id: str, query: str) -> str:
    raw_role = next(item for item in catalog.to_mapping()["profiles"] if item["role_id"] == "evidence_investigator")
    role = AgentRoleProfile.from_mapping(raw_role)
    input_payload = {
        "question": query,
        "evidence_refs": [],
        "search_limits": {"max_sources": 2},
    }
    task_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"revista-gamer:e15-investigator:{story_id}"))
    envelope = AgentTaskEnvelope.from_mapping({
        "schema_version": "1.0",
        "task_id": task_id,
        "run_id": "eng-codex-007-e15",
        "story_id": story_id,
        "edition_id": "edition-e15-fixture",
        "role_id": role.role_id,
        "role_version": role.role_version,
        "role_hash": role.content_hash,
        "input_payload_hash": stable_hash(json_dumps(input_payload)),
        "persona_id": None,
        "persona_version": None,
        "persona_hash": None,
        "input_artifact_refs": [{"ref": f"fixture://e15/brief/{story_id}", "sha256": "a" * 64}],
        "source_snapshot_ids": [f"e15-snapshot:{story_id}"],
        "authorized_tools": [],
        "deadline": "2026-10-26T00:00:00Z",
        "context_schema_version": "1.0",
        "usage_guardrails": {"max_calls": 1, "max_iterations": 1},
        "idempotency_key": f"e15-role:{story_id}",
        "correlation_id": f"e15:{story_id}",
        "requires_human_gate": True,
    })
    return enqueue_contract_task(
        queue, envelope, input_payload, catalog=catalog,
        executor_profile=VALIDATION_PROFILE,
        executor_id=SyntheticEditorialRoleExecutor.executor_id,
    )


def make_persona_writer_task(
    queue: AgentQueue,
    catalog: AgentRoleCatalog,
    persona_id: str,
    persona_instructions: str,
    input_payload: Mapping[str, Any],
    *,
    task_suffix: str = "shared",
    research_packet: ResearchPacket | None = None,
) -> str:
    raw_role = next(item for item in catalog.to_mapping()["profiles"] if item["role_id"] == "persona_writer")
    role = AgentRoleProfile.from_mapping(raw_role)
    task_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"revista-gamer:e19-persona:{task_suffix}:{persona_id}"))
    envelope = AgentTaskEnvelope.from_mapping({
        "schema_version": "1.0",
        "task_id": task_id,
        "run_id": "eng-codex-007-e19",
        "story_id": "story-factory-e15-approved",
        "edition_id": "edition-e15-fixture",
        "role_id": role.role_id,
        "role_version": role.role_version,
        "role_hash": role.content_hash,
        "input_payload_hash": stable_hash(json_dumps(dict(input_payload))),
        "persona_id": persona_id,
        "persona_version": "e19-synthetic-marker-v1",
        "persona_hash": stable_hash(persona_instructions),
        "input_artifact_refs": [{"ref": "fixture://e19/shared-brief-dossier", "sha256": "e" * 64}],
        "source_snapshot_ids": ["snapshot://e19/synthetic-shared"],
        "authorized_tools": [item.to_dict() for item in role.allowed_tools],
        "deadline": "2026-10-26T00:00:00Z",
        "context_schema_version": "1.0",
        "usage_guardrails": {"max_calls": 1, "max_iterations": 1},
        "idempotency_key": f"e19:{task_suffix}:persona:{persona_id}",
        "correlation_id": f"e19:comparable:{persona_id}",
        "requires_human_gate": True,
    })
    return enqueue_contract_task(
        queue, envelope, input_payload, catalog=catalog,
        executor_profile=VALIDATION_PROFILE,
        executor_id=SyntheticEditorialRoleExecutor.executor_id,
        research_packet=research_packet,
    )


class FactoryMultipautaE2ETests(unittest.TestCase):
    def test_radar_research_factory_multi_story_replay_uses_one_shared_ledger(self) -> None:
        with tempfile.TemporaryDirectory(prefix="revista-factory-e15-") as temp_dir:
            root = Path(temp_dir)
            motor_path = root / "motor.sqlite3"
            radar_path = root / "radar.sqlite3"
            artifact_dir = root / "artifacts"
            fixture_dir = root / "fixtures"
            fixture_dir.mkdir()

            cases = json.loads((FIXTURE_DIR / "factory-e14-cases.json").read_text(encoding="utf-8"))["cases"]
            case_by_id = {item["case_id"]: item for item in cases}
            persona_manifest = json.loads(
                (Path(__file__).parent / "fixtures" / "persona_trials_offline_v1.json").read_text(encoding="utf-8")
            )
            case_specs = (
                ("rumor-atribuido", "factory-e15-blocked", "Neblina de Vidro rumor adiamento", "research.games.v1", "hold", "approve_internally"),
                ("hardware-declaracao", "factory-e15-corrected", "Aurora de Papel ficha técnica memória", "research.hardware.v1", "revise", "hold"),
                ("jogo-mod", "factory-e15-approved", "Jardim de Nuvem mod área cooperativa", "research.creators.v1", "pass", "approve_internally"),
            )
            rss_items = []
            for index, (case_id, run_id, query, _profile_id, _review, _decision) in enumerate(case_specs, start=1):
                rss_items.append((
                    query,
                    f"https://e15-fiction.example.invalid/story/{index}",
                    f"Registro inteiramente fictício de E15 sobre {query}; usado somente para testar descoberta e pesquisa locais.",
                ))

            base_fixture = json.loads((FIXTURE_DIR / "factory-demo.json").read_text(encoding="utf-8"))
            radar_store = RadarStore(radar_path)
            radar_store.register_source(
                source_id="source-e15-fixture",
                display_name="Fonte sintética E15",
                canonical_url="https://e15-fiction.example.invalid/",
                source_type="publisher",
                access_policy="allowed",
                rights_status="authorized",
                language="pt-BR",
                now=NOW,
            )
            transport = FixtureTransport(make_rss(rss_items))
            connector = RadarConnectorService(
                transport=transport,
                resolver=FixtureResolver(),
                limiter=PerOriginLimiter(monotonic=lambda: 0.0),
            )
            queue = AgentQueue(Store(motor_path, artifact_dir))
            catalog = load_builtin_role_catalog()
            persona_markers = {
                item["persona_id"]: f"OFFLINE_FACTORY_PERSONA::{item['persona_id']}::{item['source_commit']}"
                for item in persona_manifest["personas"]
            }
            research_profiles = {
                f"story-{run_id}": profile_id
                for _case_id, run_id, _query, profile_id, _review, _decision in case_specs
            }
            role_executor = SyntheticEditorialRoleExecutor(research_profiles)
            research_service = ResearchService(store=radar_store)
            research_executor = ResearchTaskExecutor(research_service, catalog)
            result_router = ResearchResultRouter(
                queue=queue,
                catalog=catalog,
                executor_profiles={
                    (VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE,
                    (RADAR_RESEARCH_PROFILE.profile_id, RADAR_RESEARCH_PROFILE.version): RADAR_RESEARCH_PROFILE,
                },
            )
            factory_executor = SyntheticFactoryExecutor(artifact_dir=artifact_dir)
            profiles = [
                VALIDATION_PROFILE,
                RADAR_RESEARCH_PROFILE,
                _TRIAGE_EXECUTOR_PROFILE,
                EDITORIAL_PROFILE,
                LAYOUT_PROFILE,
                MEDIA_PROFILE,
                PACKAGE_PROFILE,
                GATE_PROFILE,
            ]
            dispatcher = TaskDispatcher(
                queue,
                executors={
                    role_executor.executor_id: role_executor,
                    RADAR_RESEARCH_EXECUTOR_ID: research_executor,
                    FACTORY_EXECUTOR_ID: factory_executor,
                },
                profiles={(profile.profile_id, profile.version): profile for profile in profiles},
                role_catalog=catalog,
                persona_instruction_resolver=lambda envelope: persona_markers.get(envelope.persona_id or ""),
                deterministic_task_routes={**RADAR_RESEARCH_TASK_ROUTES, **FACTORY_TASK_ROUTES},
                result_router=result_router,
            )
            incremental = IncrementalRadarService(store=radar_store, connector=connector)
            radar = RadarGeneralService(
                store=radar_store,
                incremental=incremental,
                queue=queue,
                catalog=catalog,
                executor_id=role_executor.executor_id,
            )

            scan = radar.scan([make_source_profile()], now=NOW, portfolio=["edition-e15-fixture"])
            self.assertEqual(len(scan.batch.items), 3)
            self.assertIsNotNone(scan.triage_task_id)
            self.assertEqual(dispatcher.dispatch_one(scan.triage_task_id or "").state, "succeeded")
            self.assertEqual(len(transport.calls), 1)

            story_packets: dict[str, ResearchPacket] = {}
            story_bindings: dict[str, dict[str, str]] = {}
            document_rows = radar_store.list_rows("radar_documents")
            for case_id, run_id, query, profile_id, _review_flow, _decision in case_specs:
                story_id = f"story-{run_id}"
                parent_id = make_investigator_task(queue, catalog, story_id, query)
                self.assertEqual(dispatcher.dispatch_one(parent_id).state, "succeeded")
                research_task = next(
                    task for task in queue.list_tasks(limit=1000)
                    if task.task_type == RADAR_RESEARCH_TASK_TYPE
                    and task.payload["research_request"]["story_id"] == story_id
                )
                self.assertEqual(dispatcher.dispatch_one(research_task.task_id).state, "succeeded")
                continuation = next(
                    task for task in queue.list_tasks(limit=1000)
                    if task.task_type == "agent.role.evidence_investigator"
                    and task.task_id != parent_id
                    and envelope_from_payload(task.payload).story_id == story_id
                )
                self.assertEqual(dispatcher.dispatch_one(continuation.task_id).state, "succeeded")
                self.assertTrue(continuation.payload.get("research_packet"))
                research_packet = ResearchPacket.from_mapping(continuation.payload["research_packet"])
                self.assertTrue(research_packet.document_refs)
                self.assertFalse(research_packet.retrieval_log_ref)
                story_packets[run_id] = research_packet

                case = json.loads(json.dumps(case_by_id[case_id], ensure_ascii=False))
                case["e14_case"].update({"case_id": case_id, "case_type": case["case_type"]})
                packet_ref = research_packet.document_refs[0].ref
                story_bindings[run_id] = {packet_ref: "S3"}
                document_id = packet_ref.rsplit("/", 1)[-1]
                document = next(row for row in document_rows if row["document_id"] == document_id)
                packet_source = {
                    "id": "S3",
                    "title": document["title"],
                    "publisher": document["publisher"],
                    "url": document["canonical_url"],
                    "published_at": document["published_at"] or NOW,
                    "accessed_at": document["fetched_at"],
                    "kind": "secondary",
                    "confidence": "medium",
                    "evidence": research_packet.relevant_excerpts_short[0],
                }
                case["sources"].append(packet_source)
                case["e14_case"]["source_ids"].append("S3")
                case["e14_case"]["body_markdown"] += " O Radar sintético encontrou este registro adicional, ainda sujeito à revisão editorial [S3]."
                if case_id == "hardware-declaracao":
                    case["e14_case"]["correction_body_markdown"] = case["e14_case"]["body_markdown"].replace(
                        "Este ensaio não executou teste, benchmark ou validação física do hardware.",
                        "A especificação permanece apenas como declaração; não houve teste, benchmark ou validação física do hardware nesta simulação.",
                    )
                fixture = json.loads(json.dumps(base_fixture, ensure_ascii=False))
                fixture.update({
                    "run_id": run_id,
                    "article_type": case["article_type"],
                    "topic": case["topic"],
                    "research_note": case["research_note"],
                    "sources": case["sources"],
                    "e14_case": case["e14_case"],
                    "simulated_human_decision": _decision,
                })
                fixture_path = fixture_dir / f"{run_id}.json"
                fixture_path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            story_runs = [
                FactoryStoryRun(
                    run_id=run_id,
                    fixture_path=fixture_dir / f"{run_id}.json",
                    review_flow=review_flow,
                    research_packet=story_packets[run_id],
                    research_source_bindings=story_bindings[run_id],
                )
                for _case_id, run_id, _query, _profile_id, review_flow, _decision in case_specs
            ]
            with patch("motor_editorial.factory._build_factory_dispatcher") as build_dispatcher:
                first_report = run_factory_multipauta_demo(
                    Store(motor_path, artifact_dir),
                    story_runs,
                    queue=queue,
                    dispatcher=dispatcher,
                    batch_id="factory-e15-radar-research",
                )
                build_dispatcher.assert_not_called()
            by_run = {item["run_id"]: item for item in first_report["story_outcomes"]}
            self.assertEqual(first_report["story_count"], 3)
            self.assertEqual(first_report["status"], "completed_with_blocked_stories")
            self.assertEqual(by_run["factory-e15-blocked"]["outcome"], "blocked")
            self.assertEqual(by_run["factory-e15-blocked"]["failure_code"], "factory_editorial_hold")
            self.assertEqual(by_run["factory-e15-blocked"]["failed_tasks"], [])
            self.assertEqual(by_run["factory-e15-corrected"]["outcome"], "corrected", msg=repr(by_run["factory-e15-corrected"]))
            self.assertEqual(by_run["factory-e15-corrected"]["story_revision"], 2)
            self.assertEqual(by_run["factory-e15-corrected"]["factory_status"], "simulated_on_hold")
            self.assertEqual(by_run["factory-e15-approved"]["outcome"], "approved_internal_preview")
            self.assertFalse(first_report["published"])
            self.assertTrue(all(item["radar_research_packet"] for item in by_run.values()))

            shared_packet = story_packets["factory-e15-approved"]
            comparable_input = {
                "editorial_brief": {
                    "topic": "Jardim de Nuvem: mudança fictícia em jogo cooperativo",
                    "assignment": "explicar evidência, incerteza e limite da conclusão",
                },
                "evidence_dossier": {
                    "research_packet_hash": shared_packet.content_hash,
                    "claims": list(shared_packet.claim_refs),
                    "sources": [item.ref for item in shared_packet.document_refs],
                },
                "writing_constraints": {
                    "language": "pt-BR",
                    "target_words": 180,
                    "no_firsthand_experience": True,
                },
            }
            persona_task_ids: list[str] = []
            persona_input_hashes: set[str] = set()
            for persona in persona_manifest["personas"]:
                persona_id = persona["persona_id"]
                marker = persona_markers[persona_id]
                task_id = make_persona_writer_task(
                    queue, catalog, persona_id, marker, comparable_input,
                    research_packet=shared_packet,
                )
                outcome = dispatcher.dispatch_one(task_id)
                self.assertEqual(outcome.state, "succeeded", msg=f"{persona_id}: {outcome}")
                task = queue.get(task_id)
                envelope_payload = task.payload["agent_task_envelope"]
                self.assertEqual(task.payload["input"], comparable_input)
                self.assertEqual(envelope_payload["persona_id"], persona_id)
                self.assertEqual(envelope_payload["story_id"], "story-factory-e15-approved")
                persona_input_hashes.add(envelope_payload["input_payload_hash"])
                persona_task_ids.append(task_id)
            self.assertEqual(len(set(persona_task_ids)), 3)
            self.assertEqual(len(persona_input_hashes), 1)
            self.assertEqual(len(role_executor.persona_bindings), 3)
            self.assertEqual(
                dict(role_executor.persona_packet_hashes),
                {persona_id: shared_packet.content_hash for persona_id in persona_markers},
            )
            self.assertEqual(
                {persona_id: (source, text) for persona_id, source, text in role_executor.persona_bindings},
                {
                    persona_id: (f"persona:{persona_id}", marker)
                    for persona_id, marker in persona_markers.items()
                },
            )
            self.assertFalse(any(task.result and task.result.get("model_used") for task in queue.list_tasks(limit=1000)))
            calls_before_missing_resolver = len(role_executor.calls)
            missing_resolver_task = make_persona_writer_task(
                queue, catalog, "ranzinza", persona_markers["ranzinza"], comparable_input,
                task_suffix="missing-resolver",
                research_packet=shared_packet,
            )
            fail_closed_dispatcher = TaskDispatcher(
                queue,
                executors={role_executor.executor_id: role_executor},
                profiles={(VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE},
                role_catalog=catalog,
            )
            blocked_outcome = fail_closed_dispatcher.dispatch_one(missing_resolver_task)
            self.assertEqual(blocked_outcome.state, "blocked")
            self.assertEqual(blocked_outcome.error_code, "agent_contract_invalid")
            self.assertEqual(len(role_executor.calls), calls_before_missing_resolver)
            foreign_resolver_task = make_persona_writer_task(
                queue, catalog, "ranzinza", persona_markers["ranzinza"], comparable_input,
                task_suffix="foreign-resolver",
                research_packet=shared_packet,
            )
            foreign_dispatcher = TaskDispatcher(
                queue,
                executors={role_executor.executor_id: role_executor},
                profiles={(VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE},
                role_catalog=catalog,
                persona_instruction_resolver=lambda _envelope: persona_markers["beto-cartucho"],
            )
            foreign_outcome = foreign_dispatcher.dispatch_one(foreign_resolver_task)
            self.assertEqual(foreign_outcome.state, "blocked")
            self.assertEqual(foreign_outcome.error_code, "agent_contract_invalid")
            self.assertEqual(len(role_executor.calls), calls_before_missing_resolver)
            resolver_error_task = make_persona_writer_task(
                queue, catalog, "nina-prisma", persona_markers["nina-prisma"], comparable_input,
                task_suffix="resolver-error",
                research_packet=shared_packet,
            )

            def broken_resolver(_envelope):
                raise RuntimeError("fixture resolver unavailable")

            error_dispatcher = TaskDispatcher(
                queue,
                executors={role_executor.executor_id: role_executor},
                profiles={(VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE},
                role_catalog=catalog,
                persona_instruction_resolver=broken_resolver,
            )
            resolver_error_outcome = error_dispatcher.dispatch_one(resolver_error_task)
            self.assertEqual(resolver_error_outcome.state, "blocked")
            self.assertEqual(resolver_error_outcome.error_code, "agent_contract_invalid")
            self.assertEqual(len(role_executor.calls), calls_before_missing_resolver)

            all_tasks_before_replay = {task.task_id for task in queue.list_tasks(limit=1000)}
            factory_task = next(
                task for task in queue.list_tasks(limit=1000)
                if task.task_type == EDITORIAL_TASK_TYPE
                and task.payload.get("run_id") == "factory-e15-approved"
                and task.payload.get("stage") == "source_analysis"
            )
            research_packet_payload = factory_task.payload["radar_research_packet"]
            self.assertEqual(
                research_packet_payload["content_hash"],
                story_packets["factory-e15-approved"].content_hash,
            )
            self.assertEqual(
                factory_task.payload["radar_research_source_bindings"],
                story_bindings["factory-e15-approved"],
            )
            radar_source = next(source for source in factory_task.payload["packet"]["sources"] if source["id"] == "S3")
            radar_document = next(
                row for row in document_rows
                if row["canonical_url"] == radar_source["url"]
            )
            self.assertEqual(
                research_packet_payload["document_refs"][0]["ref"],
                f"radar://document/{radar_document['document_id']}",
            )
            self.assertIn("triage_analyst", [task.task_type.removeprefix("agent.role.") for task in queue.list_tasks(limit=1000)])
            self.assertEqual(len([task for task in queue.list_tasks(limit=1000) if task.task_type == RADAR_RESEARCH_TASK_TYPE]), 3)

            restarted_queue = AgentQueue(Store(motor_path, artifact_dir))
            restarted_research_store = RadarStore(radar_path)
            restarted_catalog = load_builtin_role_catalog()
            restarted_role_executor = SyntheticEditorialRoleExecutor(research_profiles)
            restarted_research_executor = ResearchTaskExecutor(
                ResearchService(store=restarted_research_store), restarted_catalog,
            )
            restarted_router = ResearchResultRouter(
                queue=restarted_queue,
                catalog=restarted_catalog,
                executor_profiles={
                    (VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE,
                    (RADAR_RESEARCH_PROFILE.profile_id, RADAR_RESEARCH_PROFILE.version): RADAR_RESEARCH_PROFILE,
                },
            )
            restarted_dispatcher = TaskDispatcher(
                restarted_queue,
                executors={
                    restarted_role_executor.executor_id: restarted_role_executor,
                    RADAR_RESEARCH_EXECUTOR_ID: restarted_research_executor,
                    FACTORY_EXECUTOR_ID: SyntheticFactoryExecutor(artifact_dir=artifact_dir),
                },
                profiles={(profile.profile_id, profile.version): profile for profile in profiles},
                role_catalog=restarted_catalog,
                persona_instruction_resolver=lambda envelope: persona_markers.get(envelope.persona_id or ""),
                deterministic_task_routes={**RADAR_RESEARCH_TASK_ROUTES, **FACTORY_TASK_ROUTES},
                result_router=restarted_router,
            )
            restarted_router.resume_completed_routes()
            restarted_router.resume_completed_routes()
            self.assertEqual({task.task_id for task in restarted_queue.list_tasks(limit=1000)}, all_tasks_before_replay)
            with patch("motor_editorial.factory._build_factory_dispatcher") as build_dispatcher:
                replay_report = run_factory_multipauta_demo(
                    Store(motor_path, artifact_dir),
                    story_runs,
                    queue=restarted_queue,
                    dispatcher=restarted_dispatcher,
                    batch_id="factory-e15-radar-research",
                )
                build_dispatcher.assert_not_called()
            self.assertEqual(replay_report["task_ids"], first_report["task_ids"])
            self.assertEqual(replay_report["story_outcomes"], first_report["story_outcomes"])
            self.assertEqual({task.task_id for task in restarted_queue.list_tasks(limit=1000)}, all_tasks_before_replay)
            self.assertEqual(len(transport.calls), 1)
            self.assertTrue(any(packet for _role, _story, packet in role_executor.calls))


if __name__ == "__main__":
    unittest.main()
