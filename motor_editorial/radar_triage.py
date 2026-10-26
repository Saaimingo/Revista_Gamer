"""Deterministic general Radar batching and triage queue handoff.

This module only queues a versioned triage task in the existing AgentQueue. It
does not start a dispatcher, invoke an LLM, promote an editorial candidate, or
fetch sources on its own.
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from .agent_contracts import (
    AgentRoleCatalog,
    AgentRoleProfile,
    build_role_task_envelope,
    enqueue_contract_task,
    load_builtin_role_catalog,
)
from .db import json_dumps, stable_hash
from .orchestration import AgentProfile, AgentQueue
from .radar_connectors import SourceProfile
from .radar_incremental import IncrementalFetchResult, IncrementalRadarService
from .radar_store import RadarStore, RadarStoreError


_DEFAULT_PRIORITY_WEIGHTS = {
    "first_seen": 0.65,
    "title_changed": 0.85,
    "body_changed": 0.90,
    "corrected": 1.00,
    "removed": 0.35,
    "url_changed": 0.40,
    "origin_linked": 0.55,
}
_TRIAGE_EXECUTOR_PROFILE = AgentProfile(
    profile_id="radar-triage-pending",
    version="1.0.0",
    instructions=(
        "A versioned triage task is queued for a later executor integration. "
        "This placeholder does not authorize or invoke an external model."
    ),
)


@dataclass(frozen=True)
class RadarTriagePolicy:
    """Auditable deterministic event weights, not an editorial importance score."""

    relevance_threshold: float = 0.50
    priority_weights: Mapping[str, float] = field(default_factory=lambda: dict(_DEFAULT_PRIORITY_WEIGHTS))
    version: str = "radar-triage-priority-v1"

    def __post_init__(self) -> None:
        if isinstance(self.relevance_threshold, bool) or not isinstance(self.relevance_threshold, (int, float)):
            raise ValueError("relevance_threshold precisa ser numérico.")
        if not math.isfinite(float(self.relevance_threshold)) or not 0 <= self.relevance_threshold <= 1:
            raise ValueError("relevance_threshold precisa estar entre 0 e 1.")
        if not isinstance(self.priority_weights, Mapping) or not self.priority_weights:
            raise ValueError("priority_weights precisa conter ao menos um evento.")
        normalized: dict[str, float] = {}
        for event_type, weight in self.priority_weights.items():
            if event_type not in _DEFAULT_PRIORITY_WEIGHTS:
                raise ValueError(f"Evento não elegível para triagem: {event_type}.")
            if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                raise ValueError(f"Peso de {event_type} precisa ser numérico.")
            if not math.isfinite(float(weight)) or not 0 <= weight <= 1:
                raise ValueError(f"Peso de {event_type} precisa estar entre 0 e 1.")
            normalized[event_type] = float(weight)
        if not isinstance(self.version, str) or not self.version.strip() or len(self.version) > 64:
            raise ValueError("version da política precisa ser texto curto.")
        object.__setattr__(self, "priority_weights", MappingProxyType(normalized))

    def score(self, event_type: str) -> float:
        return float(self.priority_weights.get(event_type, 0.0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": self.version,
            "relevance_threshold": float(self.relevance_threshold),
            "priority_weights": dict(sorted(self.priority_weights.items())),
            "score_basis": "observation_event_type_only",
            "editorial_relevance_decision": False,
            "claim_confidence_used": False,
        }


@dataclass(frozen=True)
class DiscoveryBatch:
    batch_id: str
    items: tuple[Mapping[str, Any], ...]
    portfolio: tuple[str, ...]
    source_snapshot_ids: tuple[str, ...]
    created_at: str
    policy_snapshot: Mapping[str, Any]

    def to_agent_input(self) -> dict[str, Any]:
        """Return exactly the input shape pinned by triage_analyst@1.0.0."""
        return {
            "batch_id": self.batch_id,
            "items": [dict(item) for item in self.items],
            "portfolio": list(self.portfolio),
        }


@dataclass(frozen=True)
class RadarGeneralScanResult:
    fetches: tuple[IncrementalFetchResult, ...]
    batch: DiscoveryBatch
    triage_task_id: str | None
    unchanged_count: int
    below_threshold_count: int
    duplicate_source_count: int


TRIAGE_LANES = frozenset({"principal", "reserva", "monitoramento", "descartar"})
EDITORIAL_TRIAGE_LANES = frozenset({"principal", "reserva", "monitoramento"})


@dataclass(frozen=True)
class TriagedCandidate:
    """A triage decision resolved to exact item IDs from its DiscoveryBatch."""

    candidate_item_ids: tuple[str, ...]
    candidate_angle: str
    suggested_lane: str
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_item_ids": list(self.candidate_item_ids),
            "candidate_angle": self.candidate_angle,
            "suggested_lane": self.suggested_lane,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class TriageResolution:
    """Validated triage result, still a proposal and never a publication gate."""

    batch_id: str
    decisions: tuple[TriagedCandidate, ...]
    no_change: bool

    @property
    def status(self) -> str:
        return "no_story_yet" if self.no_change or not self.eligible_decisions else "candidates_resolved"

    @property
    def eligible_decisions(self) -> tuple[TriagedCandidate, ...]:
        return tuple(item for item in self.decisions if item.suggested_lane in EDITORIAL_TRIAGE_LANES)

    @property
    def discarded_decisions(self) -> tuple[TriagedCandidate, ...]:
        return tuple(item for item in self.decisions if item.suggested_lane == "descartar")


def resolve_triage_output(
    batch: DiscoveryBatch | Mapping[str, Any], output: Mapping[str, Any],
) -> TriageResolution:
    """Resolve exact evidence/event/document refs back to batch item IDs.

    The agent is allowed to identify an event or document without repeating an
    ``item_id``. This adapter resolves only exact typed references carried by
    that batch. It rejects unknown or ambiguous references instead of using
    substring matching or silently dropping an invalid decision.
    """

    if isinstance(batch, DiscoveryBatch):
        batch_value = batch.to_agent_input()
    elif isinstance(batch, Mapping):
        batch_value = dict(batch)
    else:
        raise RadarStoreError("DiscoveryBatch ausente ou inválido para validar triagem.")
    batch_id = batch_value.get("batch_id")
    items = batch_value.get("items")
    if not isinstance(batch_id, str) or not batch_id.strip() or not isinstance(items, (list, tuple)):
        raise RadarStoreError("DiscoveryBatch precisa de batch_id e items tipados.")
    if not isinstance(output, Mapping):
        raise RadarStoreError("Saída da triagem precisa ser objeto.")
    no_change = output.get("no_change")
    decisions = output.get("decisions")
    if not isinstance(no_change, bool) or not isinstance(decisions, (list, tuple)):
        raise RadarStoreError("Saída da triagem não corresponde ao contrato versionado.")
    if no_change and decisions:
        raise RadarStoreError("Triagem declarou no_change junto com decisões de candidatos.")
    if not no_change and not decisions:
        raise RadarStoreError("Triagem sem decisões precisa declarar no_change.")

    item_by_id: dict[str, Mapping[str, Any]] = {}
    ref_to_items: dict[str, set[str]] = defaultdict(set)
    for item in items:
        if not isinstance(item, Mapping):
            raise RadarStoreError("DiscoveryBatch contém item inválido.")
        item_id = item.get("item_id")
        refs = item.get("evidence_refs", [])
        if not isinstance(item_id, str) or not item_id.strip() or item_id in item_by_id:
            raise RadarStoreError("DiscoveryBatch contém item_id vazio ou duplicado.")
        if not isinstance(refs, (list, tuple)) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise RadarStoreError("DiscoveryBatch contém evidence_refs inválidas.")
        item_by_id[item_id] = item
        ref_to_items[item_id].add(item_id)
        for ref in refs:
            ref_to_items[ref].add(item_id)

    resolved: list[TriagedCandidate] = []
    assigned_item_ids: set[str] = set()
    for index, decision in enumerate(decisions):
        if not isinstance(decision, Mapping):
            raise RadarStoreError(f"Decisão de triagem {index} não é objeto.")
        lane = decision.get("suggested_lane")
        angle = decision.get("candidate_angle")
        refs = decision.get("evidence_refs")
        if lane not in TRIAGE_LANES:
            raise RadarStoreError(f"Decisão de triagem {index} usa suggested_lane inválida.")
        if not isinstance(angle, str) or not angle.strip():
            raise RadarStoreError(f"Decisão de triagem {index} não tem candidate_angle.")
        if not isinstance(refs, (list, tuple)) or not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise RadarStoreError(f"Decisão de triagem {index} não tem evidence_refs válidas.")
        decision_refs = tuple(dict.fromkeys(refs))
        unknown = sorted(set(decision_refs) - ref_to_items.keys())
        if unknown:
            raise RadarStoreError(f"Decisão de triagem {index} referencia refs ausentes do lote.")

        explicit_ids = decision.get("candidate_item_ids")
        if explicit_ids is not None:
            if (not isinstance(explicit_ids, (list, tuple)) or not explicit_ids
                    or any(not isinstance(item_id, str) or not item_id.strip() for item_id in explicit_ids)):
                raise RadarStoreError(f"Decisão de triagem {index} contém candidate_item_ids inválidos.")
            if len(set(explicit_ids)) != len(explicit_ids):
                raise RadarStoreError(f"Decisão de triagem {index} contém candidate_item_ids duplicados.")
            missing_ids = sorted(set(explicit_ids) - item_by_id.keys())
            if missing_ids:
                raise RadarStoreError(f"Decisão de triagem {index} seleciona candidato ausente do lote.")
            candidate_ids = set(explicit_ids)
            if any(not any(candidate_id in ref_to_items[ref] for ref in decision_refs)
                   for candidate_id in candidate_ids):
                raise RadarStoreError(f"Decisão de triagem {index} não vincula cada candidato às refs citadas.")
        else:
            ambiguous = [ref for ref in decision_refs if len(ref_to_items[ref]) != 1]
            if ambiguous:
                raise RadarStoreError(f"Decisão de triagem {index} contém refs ambíguas entre itens do lote.")
            candidate_ids = set().union(*(ref_to_items[ref] for ref in decision_refs))
            if not candidate_ids:
                raise RadarStoreError(f"Decisão de triagem {index} não resolve para candidatos do lote.")

        duplicate_ids = candidate_ids & assigned_item_ids
        if duplicate_ids:
            raise RadarStoreError("Mais de uma decisão de triagem atribuiu o mesmo candidate_item_id.")
        assigned_item_ids.update(candidate_ids)
        resolved.append(TriagedCandidate(
            candidate_item_ids=tuple(sorted(candidate_ids)),
            candidate_angle=angle.strip(),
            suggested_lane=lane,
            evidence_refs=tuple(sorted(decision_refs)),
        ))
    return TriageResolution(batch_id=batch_id, decisions=tuple(resolved), no_change=no_change)


def build_investigator_input(
    batch: DiscoveryBatch | Mapping[str, Any],
    resolution: TriageResolution,
    *,
    triage_task_id: str,
    candidate_records: Sequence[Mapping[str, Any]] | None = None,
    question: str = (
        "Apure os candidatos referenciados pelo Radar. Separe anúncio, relato, rumor, opinião e medição; "
        "preserve a origem e as republicações, ligue cada alegação a evidências consultadas e explicite "
        "contradições, lacunas e suficiência. Não transforme metadados em afirmações sobre impacto."
    ),
    search_limits: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the investigator's typed input from one validated triage result."""

    batch_value = batch.to_agent_input() if isinstance(batch, DiscoveryBatch) else dict(batch)
    if batch_value.get("batch_id") != resolution.batch_id:
        raise RadarStoreError("TriageResolution pertence a outro DiscoveryBatch.")
    if not isinstance(triage_task_id, str) or not triage_task_id.strip():
        raise RadarStoreError("Investigator exige triage_task_id persistido.")
    if resolution.no_change or not resolution.eligible_decisions:
        raise RadarStoreError("Não há candidato elegível para encaminhar ao investigador.")
    items = batch_value.get("items")
    if not isinstance(items, (list, tuple)):
        raise RadarStoreError("DiscoveryBatch.items inválido para investigação.")
    items_by_id = {item.get("item_id"): item for item in items if isinstance(item, Mapping)}
    supplied = {str(row.get("item_id") or row.get("candidate_item_id")): dict(row)
                for row in (candidate_records or ()) if isinstance(row, Mapping)}
    selected: list[dict[str, Any]] = []
    all_evidence_refs: set[str] = set()
    for decision in resolution.eligible_decisions:
        for candidate_id in decision.candidate_item_ids:
            item = items_by_id.get(candidate_id)
            if item is None:
                raise RadarStoreError("Triagem aponta para candidato que não está no DiscoveryBatch.")
            source = supplied.get(candidate_id, {})
            declared_id = source.get("item_id", source.get("candidate_item_id", candidate_id))
            if declared_id != candidate_id:
                raise RadarStoreError("Registro enriquecido pertence a outro candidate_item_id.")
            item_refs = item.get("evidence_refs", [])
            if not isinstance(item_refs, (list, tuple)):
                raise RadarStoreError("Candidato do DiscoveryBatch perdeu suas evidence_refs.")
            evidence_refs = sorted({ref for ref in item_refs if isinstance(ref, str)} | {candidate_id})
            all_evidence_refs.update(evidence_refs)
            selected.append({
                **source,
                "candidate_item_id": candidate_id,
                "triage_lane": decision.suggested_lane,
                "candidate_angle": decision.candidate_angle,
                "triage_evidence_refs": list(decision.evidence_refs),
                "evidence_refs": evidence_refs,
                "discovery_item": dict(item),
            })
    selected.sort(key=lambda row: row["candidate_item_id"])
    limits = dict(search_limits or {})
    limits.update({
        "batch_id": resolution.batch_id,
        "triage_task_id": triage_task_id,
        "candidate_count": len(selected),
        "candidate_records": selected,
    })
    return {
        "question": question,
        "evidence_refs": sorted(all_evidence_refs),
        "claim_history": [],
        "search_limits": limits,
    }


def _utc_iso(value: str | datetime | None) -> str:
    if value is None:
        current = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        current = value
    elif isinstance(value, str):
        try:
            current = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("now precisa ser timestamp ISO-8601 com fuso.") from error
    else:
        raise ValueError("now precisa ser timestamp ISO-8601 com fuso.")
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now precisa declarar fuso horário.")
    return current.astimezone(timezone.utc).isoformat(timespec="seconds")


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _role_profile(catalog: AgentRoleCatalog, role_id: str) -> AgentRoleProfile:
    for raw_profile in catalog.to_mapping()["profiles"]:
        if raw_profile.get("role_id") == role_id:
            parsed = AgentRoleProfile.from_mapping(raw_profile)
            return catalog.resolve(parsed.role_id, parsed.role_version, parsed.content_hash)
    raise RadarStoreError(f"Papel obrigatório ausente do catálogo: {role_id}.")


class RadarGeneralService:
    """Collect supplied approved source profiles and queue one batch for triage."""

    def __init__(
        self,
        *,
        store: RadarStore,
        incremental: IncrementalRadarService,
        queue: AgentQueue,
        catalog: AgentRoleCatalog | None = None,
        executor_id: str = "triage.pending",
        executor_profile: AgentProfile | None = None,
    ):
        if not isinstance(executor_id, str) or not executor_id.strip() or len(executor_id) > 128:
            raise ValueError("executor_id precisa ser texto curto.")
        self.store = store
        self.incremental = incremental
        self.queue = queue
        self.catalog = catalog or load_builtin_role_catalog()
        self.executor_id = executor_id
        self.executor_profile = executor_profile or _TRIAGE_EXECUTOR_PROFILE
        self.triage_profile = _role_profile(self.catalog, "triage_analyst")

    def scan(
        self,
        source_profiles: Sequence[SourceProfile],
        *,
        now: str | datetime | None = None,
        policy: RadarTriagePolicy | None = None,
        portfolio: Sequence[str] = (),
        wait_for_origin_slot: bool = False,
    ) -> RadarGeneralScanResult:
        profiles = tuple(source_profiles)
        if not profiles:
            raise ValueError("Radar geral exige ao menos uma fonte configurada.")
        if any(not isinstance(profile, SourceProfile) for profile in profiles):
            raise ValueError("source_profiles precisa conter SourceProfile validados.")
        source_ids = [profile.source_id for profile in profiles]
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("source_profiles contém source_id duplicado.")
        if isinstance(portfolio, (str, bytes)):
            raise ValueError("portfolio precisa ser uma sequência de identificadores.")
        portfolio_ids = tuple(portfolio)
        if any(not isinstance(item, str) or not item.strip() or len(item) > 256 for item in portfolio_ids):
            raise ValueError("portfolio contém identificador inválido.")
        if len(set(portfolio_ids)) != len(portfolio_ids):
            raise ValueError("portfolio contém identificador duplicado.")

        observed_at = _utc_iso(now)
        selected_policy = policy or RadarTriagePolicy()
        prior_republication_groups = {
            row["group_id"] for row in self.store.list_rows("radar_republication_groups")
        }
        prior_claim_groups = {
            (row["claim_id"], row["origin_group_id"])
            for row in self.store.list_rows("radar_claim_sources")
        }
        fetches_list: list[IncrementalFetchResult] = []
        last_origin_started: dict[str, tuple[float, int]] = {}
        for profile in profiles:
            origin = f"{urlsplit(profile.target_url()).scheme}://{urlsplit(profile.target_url()).hostname}"
            previous = last_origin_started.get(origin)
            if wait_for_origin_slot and previous is not None:
                elapsed = time.monotonic() - previous[0]
                wait = previous[1] + 0.1 - elapsed
                if wait > 0:
                    time.sleep(wait)
            last_origin_started[origin] = (time.monotonic(), profile.min_poll_interval_seconds)
            fetches_list.append(self.incremental.fetch(profile, now=observed_at))
        fetches = tuple(fetches_list)

        documents = {row["document_id"]: row for row in self.store.list_rows("radar_documents")}
        observations = {row["event_id"]: row for row in self.store.list_rows("radar_observation_events")}
        republish_members = self.store.list_rows("radar_republication_members")
        claim_sources = self.store.list_rows("radar_claim_sources")
        claims = {row["claim_id"]: row for row in self.store.list_rows("radar_claims")}

        republish_by_document: dict[str, list[dict[str, Any]]] = defaultdict(list)
        republish_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for member in republish_members:
            republish_by_document[member["document_id"]].append(member)
            republish_by_group[member["group_id"]].append(member)

        claim_groups_by_document: dict[str, set[tuple[str, str]]] = defaultdict(set)
        claim_documents_by_group: dict[tuple[str, str], set[str]] = defaultdict(set)
        for link in claim_sources:
            document_id = link.get("document_id")
            if document_id is None:
                continue
            group_key = (link["claim_id"], link["origin_group_id"])
            claim_groups_by_document[document_id].add(group_key)
            claim_documents_by_group[group_key].add(document_id)

        republish_claim_groups: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for group_id, members in republish_by_group.items():
            for member in members:
                republish_claim_groups[group_id].update(claim_groups_by_document.get(member["document_id"], set()))

        candidate_events: dict[str, tuple[Any, dict[str, Any], float]] = {}
        unchanged_count = 0
        below_threshold_count = 0
        duplicate_source_count = 0
        for fetch in fetches:
            for observed in fetch.documents:
                if observed.duplicate_snapshot or not (observed.is_new or observed.material_change):
                    unchanged_count += 1
                    continue
                document = documents.get(observed.document_id)
                event = observations.get(observed.event_id)
                if document is None or event is None:
                    raise RadarStoreError("ObservationEvent sem documento/proveniência persistidos.")

                republish_groups = {item["group_id"] for item in republish_by_document.get(observed.document_id, [])}
                claim_groups = claim_groups_by_document.get(observed.document_id, set())
                if observed.is_new:
                    if republish_groups.intersection(prior_republication_groups) or claim_groups.intersection(prior_claim_groups):
                        duplicate_source_count += 1
                        continue

                priority = selected_policy.score(observed.event_type)
                if priority < selected_policy.relevance_threshold:
                    below_threshold_count += 1
                    continue
                candidate_events[observed.event_id] = (observed, document, priority)

        grouped_events: dict[tuple[str, ...], list[tuple[Any, dict[str, Any], float]]] = defaultdict(list)
        for record in candidate_events.values():
            observed, document, _priority = record
            document_id = observed.document_id
            group_keys = set(claim_groups_by_document.get(document_id, set()))
            for member in republish_by_document.get(document_id, []):
                group_keys.update(republish_claim_groups.get(member["group_id"], set()))
            if group_keys:
                keys = [("claim", claim_id, origin_group_id) for claim_id, origin_group_id in sorted(group_keys)]
            else:
                republish_groups = sorted({item["group_id"] for item in republish_by_document.get(document_id, [])})
                keys = [("republication", group_id) for group_id in republish_groups]
                if not keys:
                    keys = [("document", document_id)]
            for key in keys:
                grouped_events[key].append(record)

        batch_items: list[dict[str, Any]] = []
        snapshot_ids: set[str] = set()
        for group_key, records in grouped_events.items():
            event_records = {record[0].event_id: record for record in records}
            records = list(event_records.values())
            candidate_document_ids = {record[0].document_id for record in records}
            context_document_ids = set(candidate_document_ids)
            if group_key[0] == "claim":
                claim_key = (group_key[1], group_key[2])
                context_document_ids.update(claim_documents_by_group.get(claim_key, set()))
            for document_id in tuple(context_document_ids):
                for member in republish_by_document.get(document_id, []):
                    context_document_ids.update(
                        item["document_id"] for item in republish_by_group.get(member["group_id"], [])
                    )

            lineage: list[dict[str, Any]] = []
            linked_claims: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
            for document_id in sorted(context_document_ids):
                document = documents.get(document_id)
                if document is None:
                    continue
                relations = sorted({
                    member["relation"] for member in republish_by_document.get(document_id, [])
                })
                lineage.append({
                    "document_id": document_id,
                    "source_id": document["source_id"],
                    "publisher": document["publisher"],
                    "url": document["canonical_url"],
                    "republication_relations": relations,
                })
                for link in claim_sources:
                    if link.get("document_id") != document_id:
                        continue
                    claim = claims.get(link["claim_id"])
                    if claim is None:
                        continue
                    claim_key = (
                        link["claim_id"], link["origin_group_id"], link["source_id"],
                        link["relation_type"], document_id,
                    )
                    linked_claims[claim_key] = {
                        "claim_id": link["claim_id"],
                        "epistemic_status": claim["epistemic_status"],
                        "origin_group_id": link["origin_group_id"],
                        "source_id": link["source_id"],
                        "document_id": document_id,
                        "relation_type": link["relation_type"],
                        "based_on_source_id": link.get("based_on_source_id"),
                    }

            # Only persisted, hash-based change evidence and source lineage enter the batch.
            event_evidence: list[dict[str, Any]] = []
            for observed, _document, priority in sorted(records, key=lambda item: item[0].event_id):
                event = observations[observed.event_id]
                event_evidence.append({
                    "event_id": observed.event_id,
                    "event_type": observed.event_type,
                    "observed_at": event["observed_at"],
                    "source_snapshot_id": event["source_snapshot_id"],
                    "diff": json.loads(event["diff_json"]),
                    "priority_weight": priority,
                })
                if event["source_snapshot_id"]:
                    snapshot_ids.add(event["source_snapshot_id"])

            representative = sorted(
                records,
                key=lambda item: (-item[2], item[1]["canonical_url"], item[0].document_id),
            )[0]
            representative_doc = representative[1]
            relevant_republish_groups = sorted({
                member["group_id"]
                for document_id in context_document_ids
                for member in republish_by_document.get(document_id, [])
            })
            if relevant_republish_groups:
                group_ref: str | None = relevant_republish_groups[0]
            elif group_key[0] == "claim":
                group_ref = group_key[2]
            else:
                group_ref = None
            priority = max(record[2] for record in records)
            detail = {
                "group_kind": group_key[0],
                "group_ref": group_ref,
                "candidate_document_ids": sorted(candidate_document_ids),
                "relevance_score": priority,
                "policy": selected_policy.to_dict(),
                "observations": event_evidence,
                "source_lineage": sorted(lineage, key=lambda item: (item["source_id"], item["document_id"])),
                "claim_lineage": [linked_claims[key] for key in sorted(linked_claims)],
                "rumor_status_is_not_content_confirmation": True,
            }
            item_id = f"discovery-{stable_hash(json_dumps(group_key))[:24]}"
            item: dict[str, Any] = {
                "item_id": item_id,
                "url": representative_doc["canonical_url"],
                "publisher": representative_doc["publisher"],
                "diff": _compact_json(detail),
                "evidence_refs": sorted({
                    item_id,
                    *(f"radar://document/{document_id}" for document_id in candidate_document_ids),
                    *(str(event["event_id"]) for event in event_evidence),
                    *(str(event["source_snapshot_id"]) for event in event_evidence if event.get("source_snapshot_id")),
                }),
            }
            if representative_doc.get("published_at"):
                item["published_at"] = representative_doc["published_at"]
            if group_ref:
                item["republish_group"] = group_ref
            batch_items.append(item)

        batch_items.sort(key=lambda item: (item["item_id"], item["url"]))
        batch_core = {
            "created_at": observed_at,
            "items": batch_items,
            "portfolio": list(portfolio_ids),
            "source_snapshot_ids": sorted(snapshot_ids),
            "policy": selected_policy.to_dict(),
        }
        batch_id = stable_hash(json_dumps(batch_core))[:32]
        batch = DiscoveryBatch(
            batch_id=batch_id,
            items=tuple(batch_items),
            portfolio=portfolio_ids,
            source_snapshot_ids=tuple(sorted(snapshot_ids)),
            created_at=observed_at,
            policy_snapshot=selected_policy.to_dict(),
        )

        triage_task_id: str | None = None
        if batch.items:
            input_payload = batch.to_agent_input()
            envelope = build_role_task_envelope(
                self.triage_profile,
                task_id=f"radar-triage-{batch.batch_id}",
                run_id=f"radar-run-{batch.batch_id}",
                story_id=f"discovery-{batch.batch_id}",
                input_payload=input_payload,
                input_artifact_refs=(),
                source_snapshot_ids=batch.source_snapshot_ids,
                authorized_tools=({"tool_id": "motor.read_assigned_input", "scopes": ["read:assigned_batch"]},),
                usage_guardrails={"max_calls": 1, "max_iterations": 1},
                idempotency_key=f"radar-triage:{batch.batch_id}",
                correlation_id=batch.batch_id,
                requires_human_gate=True,
            )
            triage_task_id = enqueue_contract_task(
                self.queue, envelope, input_payload, catalog=self.catalog,
                executor_profile=self.executor_profile, executor_id=self.executor_id,
                max_attempts=1,
            )

        return RadarGeneralScanResult(
            fetches=fetches,
            batch=batch,
            triage_task_id=triage_task_id,
            unchanged_count=unchanged_count,
            below_threshold_count=below_threshold_count,
            duplicate_source_count=duplicate_source_count,
        )
