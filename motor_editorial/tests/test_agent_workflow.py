from __future__ import annotations

import hashlib
import tempfile
import unittest
import uuid
from pathlib import Path

from motor_editorial.agent_contracts import (
    AGENT_ROLE_PROFILE_SCHEMA_VERSION,
    AgentRoleCatalog,
    AgentRoleProfile,
    AgentTaskEnvelope,
    ResearchPacket,
    ResearchRequest,
    enqueue_contract_task,
    envelope_from_payload,
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
from motor_editorial.orchestration import AgentQueue, TaskDispatcher, VALIDATION_PROFILE
from motor_editorial.radar_store import RadarStore
from motor_editorial.research_service import (
    PUBLIC_SOURCES_SCOPE,
    RADAR_INDEX_SCOPE,
    ResearchProviderResult,
    ResearchService,
)


def role_profile(role_id: str) -> AgentRoleProfile:
    instructions = f"Fixture determinística para {role_id}; não representa jornalista público."
    return AgentRoleProfile.from_mapping({
        "schema_version": AGENT_ROLE_PROFILE_SCHEMA_VERSION,
        "role_id": role_id,
        "role_version": "1.0.0",
        "instructions": instructions,
        "instructions_sha256": stable_hash(instructions),
        "purpose": "Validar contrato e handoff de uma função editorial.",
        "success_criteria": ["referência de artigo preservada"],
        "excluded_actions": ["publicar", "inventar fontes"],
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string", "minLength": 1}},
            "required": ["question"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object", "version": "1.0.0"},
        "allowed_tools": [],
        "data_access": ["fixture_only"],
        "allowed_sources": ["fixture_only"],
        "time_budget_seconds": 30,
        "usage_budget": {"max_calls": 1, "max_iterations": 1},
        "allowed_model_policy": {"mode": "deterministic_or_authorized_executor"},
        "request_research_allowed": True,
        "max_iterations": 1,
        "handoff_targets": ["assignment_editor", "fact_checker"],
        "human_review_gate": {"required": True, "stages": ["fixture"]},
        "failure_policy": {"timeout": "blocked"},
        "quality_rubric": ["structured output"],
        "evaluation_fixture_refs": ["fixture://agent-workflow/e13"],
        "owner": "engineering",
    })


def make_envelope(profile: AgentRoleProfile, story_id: str) -> tuple[AgentTaskEnvelope, dict]:
    task_id = str(uuid.uuid4())
    input_payload = {"question": f"Pergunta sintética para {story_id}."}
    envelope = AgentTaskEnvelope.from_mapping({
        "schema_version": "1.0",
        "task_id": task_id,
        "run_id": "run-e13-fixture",
        "story_id": story_id,
        "edition_id": "edition-fixture",
        "role_id": profile.role_id,
        "role_version": profile.role_version,
        "role_hash": profile.content_hash,
        "input_payload_hash": stable_hash(json_dumps(input_payload)),
        "persona_id": None,
        "persona_version": None,
        "persona_hash": None,
        "input_artifact_refs": [{"ref": f"fixture://brief/{story_id}", "sha256": "a" * 64}],
        "source_snapshot_ids": [f"snapshot:{story_id}"],
        "authorized_tools": [],
        "deadline": "2026-10-26T00:00:00Z",
        "context_schema_version": "1.0",
        "usage_guardrails": {"max_calls": 1, "max_iterations": 1},
        "idempotency_key": f"fixture-task:{task_id}",
        "correlation_id": f"fixture:{story_id}",
        "requires_human_gate": True,
    })
    return envelope, input_payload


def make_research_request(envelope: AgentTaskEnvelope) -> ResearchRequest:
    return ResearchRequest.from_mapping({
        "schema_version": "1.1",
        "request_id": f"research-{envelope.story_id}",
        "parent_task_id": envelope.task_id,
        "story_id": envelope.story_id,
        "story_revision_id": f"revision-{envelope.story_id}",
        "requester_role_id": envelope.role_id,
        "requester_persona_id": envelope.persona_id,
        "research_profile_id": "research.games.v1",
        "research_profile_version": "1.0.0",
        "question": f"Localizar evidência adicional para {envelope.story_id}.",
        "queries": [f"fixture query {envelope.story_id}"],
        "entity_ids": [],
        "required_evidence_kinds": ["official_statement"],
        "preferred_source_ids": [],
        "preferred_domains": [],
        "languages": ["pt-BR"],
        "time_window": {},
        "versions_configurations": {},
        "known_evidence_ids": [],
        "exclusions": [],
        "max_sources": 1,
        "max_requests": 1,
        "max_bytes": 10_000,
        "max_duration_seconds": 10,
        "reason": "E13 synthetic fixture.",
        "allowed_scope": [RADAR_INDEX_SCOPE],
        "idempotency_key": f"research-idem:{envelope.story_id}",
        "human_gate_if_sensitive": True,
    })


def result_for(
    envelope: AgentTaskEnvelope,
    *,
    requested_research: ResearchRequest | None = None,
) -> dict:
    digest = hashlib.sha256(f"artifact:{envelope.task_id}".encode("utf-8")).hexdigest()
    return {
        "schema_version": "1.0",
        "task_id": envelope.task_id,
        "status": "needs_more_research" if requested_research else "completed",
        "output_schema_version": "1.0.0",
        "artifact_ref": {"ref": f"fixture://result/{envelope.task_id}", "sha256": digest},
        "material_claims": [],
        "requested_research": requested_research.to_dict() if requested_research else None,
        "open_questions": ["fixture evidence gap"] if requested_research else [],
        "observed_constraints": ["fixture only"],
        "input_hash": envelope.input_hash,
        "output_hash": digest,
        "created_at": "2026-10-25T16:00:00Z",
        "model_used": None,
        "model_effort": None,
        "usage_reported": None,
        "next_action_suggestion": None,
    }


class SyntheticRoleExecutor:
    executor_id = "synthetic-role-fixture"

    def __init__(self):
        self.calls: list[tuple[str, str, dict | None]] = []

    def execute(self, task, profile, context):
        envelope = context.agent_task_envelope
        evidence = context.agent_invocation_context.untrusted_evidence["packet"]
        self.calls.append((envelope.role_id, envelope.story_id, evidence))
        if envelope.role_id == "evidence_investigator" and evidence is None:
            return result_for(envelope, requested_research=make_research_request(envelope))
        return result_for(envelope)


class PublicScopeRoleExecutor(SyntheticRoleExecutor):
    def execute(self, task, profile, context):
        envelope = context.agent_task_envelope
        request = make_research_request(envelope)
        public_request = ResearchRequest.from_mapping({
            **request.to_dict(),
            "allowed_scope": [RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE],
        })
        self.calls.append((envelope.role_id, envelope.story_id, None))
        return result_for(envelope, requested_research=public_request)


class BlockedProvider:
    def search(self, request, profile, *, cached_document_ids, budget):
        return ResearchProviderResult(
            status="blocked",
            missing_evidence=request.required_evidence_kinds,
            constraints=("fixture retriever blocked",),
        )


class AgentWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="revista-agent-workflow-e13-")
        self.root = Path(self.temp.name)
        self.motor_path = self.root / "factory.sqlite3"
        self.artifact_dir = self.root / "artifacts"
        self.radar_path = self.root / "radar.sqlite3"
        self.profile_a = role_profile("evidence_investigator")
        self.profile_b = role_profile("assignment_editor")
        self.catalog = AgentRoleCatalog([self.profile_a, self.profile_b])
        self.execution_profiles = {
            (VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE,
            (RADAR_RESEARCH_PROFILE.profile_id, RADAR_RESEARCH_PROFILE.version): RADAR_RESEARCH_PROFILE,
        }
        self.radar_store = RadarStore(self.radar_path)
        self.research_service = ResearchService(store=self.radar_store)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def dispatcher(self, queue: AgentQueue, *, router=None, role_executor=None):
        executor = role_executor or SyntheticRoleExecutor()
        research_executor = ResearchTaskExecutor(self.research_service, self.catalog)
        return TaskDispatcher(
            queue,
            executors={
                executor.executor_id: executor,
                research_executor.executor_id: research_executor,
            },
            profiles=self.execution_profiles,
            role_catalog=self.catalog,
            deterministic_task_routes=RADAR_RESEARCH_TASK_ROUTES,
            result_router=router,
        ), executor

    def enqueue_role(self, queue, role_profile_value, story_id):
        envelope, input_payload = make_envelope(role_profile_value, story_id)
        task_id = enqueue_contract_task(
            queue, envelope, input_payload, catalog=self.catalog,
            executor_profile=VALIDATION_PROFILE,
            executor_id=SyntheticRoleExecutor.executor_id,
        )
        return task_id, envelope

    def test_one_dispatcher_routes_two_roles_through_research_back_to_correct_story(self) -> None:
        queue = AgentQueue(Store(self.motor_path, self.artifact_dir))
        router = ResearchResultRouter(
            queue=queue, catalog=self.catalog, executor_profiles=self.execution_profiles,
        )
        dispatcher, role_executor = self.dispatcher(queue, router=router)
        investigator_id, investigator_envelope = self.enqueue_role(queue, self.profile_a, "story-A")
        editor_id, _editor_envelope = self.enqueue_role(queue, self.profile_b, "story-B")

        self.assertEqual(dispatcher.dispatch_one(investigator_id).state, "succeeded")
        self.assertEqual(dispatcher.dispatch_one(editor_id).state, "succeeded")
        research_tasks = [task for task in queue.list_tasks() if task.task_type == RADAR_RESEARCH_TASK_TYPE]
        self.assertEqual(len(research_tasks), 1)
        research_task = research_tasks[0]
        request = ResearchRequest.from_mapping(research_task.payload["research_request"])
        self.assertEqual(request.story_id, "story-A")
        self.assertEqual(request.parent_task_id, investigator_id)
        self.assertEqual(queue.dependencies(research_task.task_id), (investigator_id,))

        research_outcome = dispatcher.dispatch_one(research_task.task_id)
        self.assertEqual(research_outcome.state, "succeeded", research_outcome.error_code)
        continuation_tasks = [
            task for task in queue.list_tasks()
            if task.task_type == "agent.role.evidence_investigator" and task.task_id != investigator_id
        ]
        self.assertEqual(len(continuation_tasks), 1)
        continuation = continuation_tasks[0]
        continuation_envelope = envelope_from_payload(continuation.payload)
        packet = ResearchPacket.from_mapping(continuation.payload["research_packet"])
        self.assertEqual(continuation_envelope.story_id, "story-A")
        self.assertEqual(continuation_envelope.role_id, investigator_envelope.role_id)
        self.assertEqual(continuation_envelope.persona_id, investigator_envelope.persona_id)
        self.assertEqual(packet.request_id, request.request_id)
        self.assertIs(continuation.payload["research_cycle_already_used"], True)
        self.assertEqual(queue.dependencies(continuation.task_id), (research_task.task_id,))
        self.assertEqual(dispatcher.dispatch_one(continuation.task_id).state, "succeeded")

        self.assertEqual(
            [(role_id, story_id) for role_id, story_id, _packet in role_executor.calls],
            [("evidence_investigator", "story-A"), ("assignment_editor", "story-B"),
             ("evidence_investigator", "story-A")],
        )
        self.assertIsNotNone(role_executor.calls[-1][2])
        self.assertFalse(any(task.task_type.startswith("workflow.") for task in queue.list_tasks()))

    def test_blocked_empty_research_packet_does_not_enqueue_journalist_continuation(self) -> None:
        self.research_service = ResearchService(
            store=self.radar_store,
            provider=BlockedProvider(),
        )
        queue = AgentQueue(Store(self.motor_path, self.artifact_dir))
        router = ResearchResultRouter(
            queue=queue, catalog=self.catalog, executor_profiles=self.execution_profiles,
        )
        dispatcher, _executor = self.dispatcher(
            queue, router=router, role_executor=PublicScopeRoleExecutor(),
        )
        parent_id, _envelope = self.enqueue_role(queue, self.profile_a, "story-blocked-research")

        self.assertEqual(dispatcher.dispatch_one(parent_id).state, "succeeded")
        research_tasks = [task for task in queue.list_tasks() if task.task_type == RADAR_RESEARCH_TASK_TYPE]
        self.assertEqual(len(research_tasks), 1)
        research_outcome = dispatcher.dispatch_one(research_tasks[0].task_id)
        self.assertEqual(research_outcome.state, "succeeded", research_outcome.error_code)
        research_task = queue.get(research_tasks[0].task_id)
        self.assertEqual(research_task.result["packet"]["status"], "blocked")
        continuations = [
            task for task in queue.list_tasks()
            if task.task_type == "agent.role.evidence_investigator" and task.task_id != parent_id
        ]
        self.assertEqual(continuations, [])

    def test_restart_replays_success_result_and_routes_idempotently(self) -> None:
        first_queue = AgentQueue(Store(self.motor_path, self.artifact_dir))
        first_dispatcher, _ = self.dispatcher(first_queue)
        role_task_id, _ = self.enqueue_role(first_queue, self.profile_a, "story-restart")
        self.assertEqual(first_dispatcher.dispatch_one(role_task_id).state, "succeeded")
        self.assertEqual(len(first_queue.list_tasks()), 1)

        restarted_queue = AgentQueue(Store(self.motor_path, self.artifact_dir))
        router = ResearchResultRouter(
            queue=restarted_queue, catalog=self.catalog,
            executor_profiles=self.execution_profiles,
        )
        processed_first = router.resume_completed_routes()
        processed_second = router.resume_completed_routes()
        research_tasks = [task for task in restarted_queue.list_tasks() if task.task_type == RADAR_RESEARCH_TASK_TYPE]
        self.assertEqual(processed_first, 1)
        self.assertEqual(processed_second, 1)
        self.assertEqual(len(research_tasks), 1)

        dispatcher, _ = self.dispatcher(restarted_queue)
        research_task_id = research_tasks[0].task_id
        research_outcome = dispatcher.dispatch_one(research_task_id)
        self.assertEqual(research_outcome.state, "succeeded", research_outcome.error_code)
        restarted_again = AgentQueue(Store(self.motor_path, self.artifact_dir))
        replay_router = ResearchResultRouter(
            queue=restarted_again, catalog=self.catalog,
            executor_profiles=self.execution_profiles,
        )
        replay_router.resume_completed_routes()
        replay_router.resume_completed_routes()
        continuation_tasks = [
            task for task in restarted_again.list_tasks()
            if task.task_type == "agent.role.evidence_investigator" and task.task_id != role_task_id
        ]
        self.assertEqual(len(continuation_tasks), 1)
        self.assertEqual(restarted_again.dependencies(continuation_tasks[0].task_id), (research_task_id,))

    def test_dispatcher_blocks_unregistered_deterministic_task_route(self) -> None:
        queue = AgentQueue(Store(self.motor_path, self.artifact_dir))
        task_id = queue.enqueue(
            task_type=RADAR_RESEARCH_TASK_TYPE,
            payload={"research_request": {}},
            profile=RADAR_RESEARCH_PROFILE,
            executor_id="unexpected-executor",
            idempotency_key="unregistered-research-route",
        )
        dispatcher, executor = self.dispatcher(queue)
        outcome = dispatcher.dispatch_one(task_id)
        self.assertEqual((outcome.state, outcome.error_code), ("blocked", "task_route_unregistered"))
        self.assertEqual(executor.calls, [])
        self.assertEqual(queue.get(task_id).attempts, 1)


if __name__ == "__main__":
    unittest.main()
