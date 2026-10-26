"""Durable research handoffs routed through the existing AgentQueue.

This module does not create another queue, dispatcher, worker, or scheduler.
It turns a validated role result into a deterministic Radar task, and turns
that task's persisted packet into a continuation of the same story and role.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from .agent_contracts import (
    AgentRoleCatalog,
    AgentTaskEnvelope,
    ResearchPacket,
    ResearchRequest,
    enqueue_contract_task,
    envelope_from_payload,
)
from .db import stable_hash
from .orchestration import (
    AgentProfile,
    AgentQueue,
    AgentTask,
    TaskExecutionContext,
    TaskFailure,
)
from .research_service import PUBLIC_SOURCES_SCOPE, ResearchService


RADAR_RESEARCH_TASK_TYPE = "radar.research_request.v1"
RADAR_RESEARCH_EXECUTOR_ID = "radar.research.deterministic"
RADAR_RESEARCH_PROFILE = AgentProfile(
    profile_id="radar-research-deterministic",
    version="1.0.0",
    instructions=(
        "Executor determinístico local do ResearchService compartilhado. "
        "Não gera texto editorial nem chama um modelo de linguagem."
    ),
)
RADAR_RESEARCH_TASK_ROUTES = {
    RADAR_RESEARCH_TASK_TYPE: RADAR_RESEARCH_EXECUTOR_ID,
}


class ResearchTaskExecutor:
    """Adapter from a durable queue task to the shared, cache-first Radar service."""

    executor_id = RADAR_RESEARCH_EXECUTOR_ID

    def __init__(self, service: ResearchService, catalog: AgentRoleCatalog):
        self.service = service
        self.catalog = catalog

    def execute(
        self,
        task: AgentTask,
        profile: AgentProfile,
        context: TaskExecutionContext,
    ) -> Mapping[str, Any]:
        if task.task_type != RADAR_RESEARCH_TASK_TYPE:
            raise TaskFailure("research_task_type_invalid", "Executor recebeu tipo de tarefa inesperado.", blocked=True)
        raw_request = task.payload.get("research_request")
        if not isinstance(raw_request, Mapping) or set(task.payload) != {"research_request"}:
            raise TaskFailure("research_request_invalid", "Payload de pesquisa não corresponde ao contrato versionado.", blocked=True)
        try:
            request = ResearchRequest.from_mapping(raw_request)
            self._validate_parent_binding(request, context.queue)
        except (TypeError, ValueError):
            raise TaskFailure(
                "research_request_unbound",
                "ResearchRequest não corresponde ao resultado versionado de origem.",
                blocked=True,
            ) from None

        # If an explicitly configured provider might be reached, preserve the
        # queue's existing uncertain-after-external-call retry guard.
        if self.service.provider is not None and PUBLIC_SOURCES_SCOPE in request.allowed_scope:
            context.mark_external_started()
        execution = self.service.execute(request)
        return {
            "schema_version": "1.0",
            "request_id": execution.request_id,
            "story_id": execution.story_id,
            "story_revision_id": execution.story_revision_id,
            "packet_id": execution.packet_id,
            "packet": execution.packet.to_dict(),
            "cache_hit": execution.cache_hit,
            "index_hit_count": execution.index_hit_count,
            "provider_called": execution.provider_called,
        }

    def _validate_parent_binding(self, request: ResearchRequest, queue: AgentQueue) -> None:
        if request.schema_version != "1.1" or not request.story_revision_id:
            raise ValueError("ResearchRequest v1.1 is required for workflow routing.")
        parent = queue.get(request.parent_task_id)
        if parent is None or parent.state != "succeeded" or parent.result is None:
            raise ValueError("ResearchRequest parent task is not a successful durable task.")
        envelope = envelope_from_payload(parent.payload)
        role_result = self.catalog.validate_result(envelope, parent.result)
        if (
            envelope.story_id != request.story_id
            or envelope.role_id != request.requester_role_id
            or envelope.persona_id != request.requester_persona_id
            or role_result.requested_research != request
        ):
            raise ValueError("ResearchRequest does not match its originating role result.")


class ResearchResultRouter:
    """Idempotent result routing attached to TaskDispatcher's success path."""

    def __init__(
        self,
        *,
        queue: AgentQueue,
        catalog: AgentRoleCatalog,
        executor_profiles: Mapping[tuple[str, str], AgentProfile],
    ):
        self.queue = queue
        self.catalog = catalog
        self.executor_profiles = dict(executor_profiles)

    def __call__(self, task: AgentTask) -> None:
        if task.state != "succeeded" or task.result is None:
            raise ValueError("Somente resultado durável concluído pode gerar handoff.")
        if task.task_type.startswith("agent.role."):
            self._route_role_result(task)
        elif task.task_type == RADAR_RESEARCH_TASK_TYPE:
            self._route_research_result(task)

    def resume_completed_routes(self, *, limit: int = 1000) -> int:
        """Replay successful results after a process restart; enqueue is idempotent."""
        processed = 0
        for task in reversed(self.queue.list_tasks(limit=limit)):
            if task.state == "succeeded" and task.result is not None:
                self(task)
                processed += 1
        return processed

    def _route_role_result(self, task: AgentTask) -> None:
        envelope = envelope_from_payload(task.payload)
        result = self.catalog.validate_result(envelope, task.result)
        request = result.requested_research
        if request is None:
            return
        self._validate_request_binding(envelope, request, task.task_id)
        self.queue.enqueue(
            task_type=RADAR_RESEARCH_TASK_TYPE,
            payload={"research_request": request.to_dict()},
            profile=RADAR_RESEARCH_PROFILE,
            executor_id=RADAR_RESEARCH_EXECUTOR_ID,
            idempotency_key=f"radar-research:{request.request_id}",
            dependencies=(task.task_id,),
        )

    @staticmethod
    def _validate_request_binding(
        envelope: AgentTaskEnvelope,
        request: ResearchRequest,
        parent_task_id: str,
    ) -> None:
        if (
            request.schema_version != "1.1"
            or not request.story_revision_id
            or request.parent_task_id != parent_task_id
            or request.story_id != envelope.story_id
            or request.requester_role_id != envelope.role_id
            or request.requester_persona_id != envelope.persona_id
        ):
            raise ValueError("ResearchRequest diverge do papel, persona, artigo ou revisão de origem.")

    def _route_research_result(self, task: AgentTask) -> None:
        request_value = task.payload.get("research_request")
        if not isinstance(request_value, Mapping):
            raise ValueError("Tarefa Radar concluída sem ResearchRequest persistido.")
        request = ResearchRequest.from_mapping(request_value)
        raw_result = task.result or {}
        if raw_result.get("schema_version") != "1.0" or raw_result.get("request_id") != request.request_id:
            raise ValueError("Resultado Radar não corresponde ao ResearchRequest da tarefa.")
        if (
            raw_result.get("story_id") != request.story_id
            or raw_result.get("story_revision_id") != request.story_revision_id
            or not isinstance(raw_result.get("packet_id"), str)
        ):
            raise ValueError("Resultado Radar perdeu o vínculo com o artigo ou revisão corretos.")
        packet = ResearchPacket.from_mapping(raw_result.get("packet"))
        if packet.request_id != request.request_id:
            raise ValueError("ResearchPacket não corresponde ao ResearchRequest da tarefa.")

        parent = self.queue.get(request.parent_task_id)
        if parent is None or parent.state != "succeeded" or parent.result is None:
            raise ValueError("Tarefa de origem ausente ou ainda não concluída.")
        parent_envelope = envelope_from_payload(parent.payload)
        parent_result = self.catalog.validate_result(parent_envelope, parent.result)
        if parent_result.requested_research != request:
            raise ValueError("Pesquisa concluída não pertence ao resultado da tarefa de origem.")
        self._validate_request_binding(parent_envelope, request, parent.task_id)

        original_input = parent.payload.get("input")
        if not isinstance(original_input, Mapping):
            raise ValueError("Tarefa de origem não possui input estruturado para retomada.")
        executor_profile = self.executor_profiles.get((parent.profile_id, parent.profile_version))
        if executor_profile is None or executor_profile.content_hash != parent.profile_hash:
            raise ValueError("Perfil do executor original não está disponível para retomada.")

        envelope_data = parent_envelope.to_dict()
        envelope_data["task_id"] = str(uuid.uuid5(
            uuid.NAMESPACE_URL, f"revista-gamer:research-return:{request.request_id}"
        ))
        envelope_data["idempotency_key"] = f"research-return:{stable_hash(request.request_id)}"
        packet_ref = f"radar://research-packet/{raw_result['packet_id']}"
        artifact_refs = list(envelope_data["input_artifact_refs"])
        if all(item.get("ref") != packet_ref for item in artifact_refs):
            artifact_refs.append({"ref": packet_ref, "sha256": packet.content_hash})
        envelope_data["input_artifact_refs"] = artifact_refs
        snapshot_id = f"research:{request.request_id}:{packet.content_hash}"
        snapshots = list(envelope_data["source_snapshot_ids"])
        if snapshot_id not in snapshots:
            snapshots.append(snapshot_id)
        envelope_data["source_snapshot_ids"] = snapshots
        continuation = AgentTaskEnvelope.from_mapping(envelope_data)

        enqueue_contract_task(
            self.queue,
            continuation,
            dict(original_input),
            catalog=self.catalog,
            executor_profile=executor_profile,
            executor_id=parent.executor_id,
            dependencies=(task.task_id,),
            research_packet=packet,
            research_cycle_already_used=True,
        )
