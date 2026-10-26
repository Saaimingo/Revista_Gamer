"""Deterministic conversion of writer suggestions into index-only requests."""

from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Mapping
from typing import Any

from .agent_contracts import EPISTEMIC_STATUSES, ResearchRequest
from .db import json_dumps, stable_hash
from .research_service import DEFAULT_RESEARCH_PROFILES, RADAR_INDEX_SCOPE


POLICY_SCHEMA_VERSION = "ResearchMediationPolicy.v1"
MEDIATION_VERSION = "1.0.0"
MAX_SUGGESTIONS = 2
MAX_SOURCES = 5
MAX_REQUESTS = 1
MAX_BYTES = 65_536
MAX_DURATION_SECONDS = 30
_NORMAL_SPACE = re.compile(r"\s+")
_NAMESPACE = uuid.UUID("e9d729dd-4bdf-5e1c-aea5-d2e2452e0572")


def _normalized(value: str) -> str:
    return _NORMAL_SPACE.sub(" ", unicodedata.normalize("NFC", value).strip()).casefold()


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(nested) for nested in value]
    return value


def _profile_index() -> dict[tuple[str, str], Any]:
    return {(profile.profile_id, profile.version): profile for profile in DEFAULT_RESEARCH_PROFILES}


def _validate_route(route: Any, index: int) -> dict[str, Any]:
    if not isinstance(route, Mapping):
        raise ValueError(f"research route {index} precisa ser objeto")
    required = {
        "route_id", "question", "purpose", "research_profile_id", "research_profile_version",
        "required_evidence_kinds", "reason",
    }
    optional = {
        "entity_ids", "preferred_source_ids", "preferred_domains", "languages", "time_window",
        "versions_configurations", "known_evidence_ids", "exclusions",
    }
    if required - route.keys() or route.keys() - required - optional:
        raise ValueError(f"research route {index} tem campos ausentes ou desconhecidos")
    for field, maximum in (("route_id", 128), ("question", 2_000), ("purpose", 2_000), ("reason", 2_000),
                           ("research_profile_id", 128), ("research_profile_version", 64)):
        value = route.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError(f"research route {index}.{field} é inválido")
    if not isinstance(route["required_evidence_kinds"], (list, tuple)) or not route["required_evidence_kinds"]:
        raise ValueError(f"research route {index} precisa de required_evidence_kinds explícitos")
    kinds = route["required_evidence_kinds"]
    if any(not isinstance(kind, str) or kind not in EPISTEMIC_STATUSES for kind in kinds):
        raise ValueError(f"research route {index} contém tipo epistêmico fora do contrato")
    if (route["research_profile_id"], route["research_profile_version"]) not in _profile_index():
        raise ValueError(f"research route {index} referencia perfil não registrado")
    normalized = dict(route)
    for field in ("entity_ids", "preferred_source_ids", "preferred_domains", "languages", "known_evidence_ids", "exclusions"):
        value = normalized.setdefault(field, [])
        if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"research route {index}.{field} precisa ser uma lista de strings")
        normalized[field] = list(value)
    for field in ("time_window", "versions_configurations"):
        value = normalized.setdefault(field, {})
        if not isinstance(value, Mapping):
            raise ValueError(f"research route {index}.{field} precisa ser objeto")
        normalized[field] = dict(value)
    return normalized


def validate_policy(policy: Any, *, story_id: str, role_id: str, persona_id: str | None) -> dict[str, Any]:
    if not isinstance(policy, Mapping) or policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise ValueError("ResearchMediationPolicy.v1 ausente ou inválida")
    if role_id != "persona_writer" or not persona_id:
        raise ValueError("mediação automática exige persona_writer e persona aprovada")
    if set(policy) != {"schema_version", "story_revision_id", "routes"}:
        raise ValueError("ResearchMediationPolicy tem campos ausentes ou desconhecidos")
    revision_id = policy.get("story_revision_id")
    if not isinstance(revision_id, str) or not revision_id.strip() or len(revision_id) > 128:
        raise ValueError("ResearchMediationPolicy precisa vincular story_revision_id")
    routes_raw = policy.get("routes")
    if not isinstance(routes_raw, (list, tuple)) or not routes_raw or len(routes_raw) > 16:
        raise ValueError("ResearchMediationPolicy precisa de 1 a 16 rotas explícitas")
    routes = [_validate_route(route, index) for index, route in enumerate(routes_raw, start=1)]
    route_ids = [route["route_id"] for route in routes]
    if len(route_ids) != len(set(route_ids)):
        raise ValueError("ResearchMediationPolicy contém route_id duplicado")
    if any(not _normalized(route["question"]) or not _normalized(route["purpose"]) for route in routes):
        raise ValueError("ResearchMediationPolicy contém rota sem question/purpose")
    return {"schema_version": POLICY_SCHEMA_VERSION, "story_revision_id": revision_id, "routes": routes}


def mediate_requested_research(
    suggestions: Any,
    *,
    policy: Mapping[str, Any] | None,
    parent_task_id: str,
    story_id: str,
    role_id: str,
    persona_id: str | None,
) -> dict[str, Any]:
    """Return one typed request at most; unmatched or incompatible pairs stay pending."""
    base: dict[str, Any] = {
        "mediation_version": MEDIATION_VERSION,
        "status": "none_requested",
        "policy_sha256": stable_hash(json_dumps(_plain(policy))) if policy is not None else None,
        "requested_research_count": len(suggestions) if isinstance(suggestions, (list, tuple)) else None,
        "suggestions": [
            {
                "suggestion_index": index,
                "question": item.get("question") if isinstance(item, Mapping) and isinstance(item.get("question"), str) else None,
                "purpose": item.get("purpose") if isinstance(item, Mapping) and isinstance(item.get("purpose"), str) else None,
                "shape": "object" if isinstance(item, Mapping) else type(item).__name__,
            }
            for index, item in enumerate(suggestions, start=1)
        ] if isinstance(suggestions, (list, tuple)) else [],
        "accepted_route_ids": [],
        "pending_research": [],
        "deduplicated_suggestions": [],
        "ignored_model_fields": [],
        "request": None,
    }
    if not isinstance(suggestions, (list, tuple)) or not suggestions:
        return base
    if policy is None:
        base["status"] = "hold_missing_motor_policy"
        base["pending_research"] = [
            {"suggestion_index": index, "reason": "trusted_motor_policy_missing"}
            for index, _ in enumerate(suggestions, start=1)
        ]
        return base
    try:
        validated = validate_policy(policy, story_id=story_id, role_id=role_id, persona_id=persona_id)
    except ValueError as error:
        base["status"] = "hold_invalid_motor_policy"
        base["pending_research"] = [{"reason": str(error)}]
        return base

    route_index = {
        (_normalized(route["question"]), _normalized(route["purpose"])): route
        for route in validated["routes"]
    }
    matched: list[tuple[int, dict[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for index, suggestion in enumerate(suggestions, start=1):
        if index > MAX_SUGGESTIONS:
            base["pending_research"].append({"suggestion_index": index, "reason": "per_result_pair_limit"})
            continue
        if not isinstance(suggestion, Mapping):
            base["pending_research"].append({"suggestion_index": index, "reason": "suggestion_not_object"})
            continue
        question = suggestion.get("question")
        purpose = suggestion.get("purpose")
        extra_fields = sorted(str(key) for key in suggestion.keys() - {"question", "purpose"})
        if extra_fields:
            base["ignored_model_fields"].append({"suggestion_index": index, "fields": extra_fields})
        if (
            not isinstance(question, str) or not question.strip() or len(question) > 2_000
            or not isinstance(purpose, str) or not purpose.strip() or len(purpose) > 2_000
        ):
            base["pending_research"].append({"suggestion_index": index, "reason": "question_or_purpose_invalid"})
            continue
        key = (_normalized(question), _normalized(purpose))
        if key in seen:
            base["deduplicated_suggestions"].append(index)
            continue
        seen.add(key)
        route = route_index.get(key)
        if route is None:
            base["pending_research"].append({"suggestion_index": index, "reason": "no_exact_brief_route_match"})
            continue
        matched.append((index, route))

    if not matched:
        base["status"] = "hold_unmapped_suggestions"
        return base

    # Policy order is the explicit priority. Only compatible routes share one request.
    priority_order = {route["route_id"]: index for index, route in enumerate(validated["routes"])}
    matched.sort(key=lambda item: priority_order[item[1]["route_id"]])
    first_route = matched[0][1]
    group_key = (
        first_route["research_profile_id"], first_route["research_profile_version"],
        tuple(first_route["required_evidence_kinds"]),
        tuple(first_route["entity_ids"]), tuple(first_route["preferred_source_ids"]),
        tuple(first_route["preferred_domains"]), tuple(first_route["languages"]),
        json_dumps(first_route["time_window"]), json_dumps(first_route["versions_configurations"]),
        tuple(first_route["known_evidence_ids"]), tuple(first_route["exclusions"]),
    )
    selected: list[dict[str, Any]] = []
    for suggestion_index, route in matched:
        route_key = (
            route["research_profile_id"], route["research_profile_version"],
            tuple(route["required_evidence_kinds"]), tuple(route["entity_ids"]),
            tuple(route["preferred_source_ids"]), tuple(route["preferred_domains"]),
            tuple(route["languages"]), json_dumps(route["time_window"]),
            json_dumps(route["versions_configurations"]), tuple(route["known_evidence_ids"]),
            tuple(route["exclusions"]),
        )
        if route_key != group_key:
            base["pending_research"].append({
                "suggestion_index": suggestion_index,
                "route_id": route["route_id"],
                "reason": "incompatible_profile_or_evidence_kinds",
            })
            continue
        if len(selected) >= MAX_SUGGESTIONS:
            base["pending_research"].append({
                "suggestion_index": suggestion_index,
                "route_id": route["route_id"],
                "reason": "request_query_limit",
            })
            continue
        selected.append(route)

    if not selected:
        base["status"] = "hold_no_compatible_routes"
        return base

    route_ids = [route["route_id"] for route in selected]
    queries = [route["question"].strip() for route in selected]
    profile = _profile_index()[(first_route["research_profile_id"], first_route["research_profile_version"])]
    if RADAR_INDEX_SCOPE not in profile.allowed_scopes:
        base["status"] = "hold_profile_disallows_local_index"
        base["pending_research"] = [{"route_id": route_id, "reason": "profile_disallows_read_radar_index"} for route_id in route_ids]
        return base

    policy_version = MEDIATION_VERSION
    request_binding = {
        "parent_task_id": parent_task_id,
        "story_id": story_id,
        "story_revision_id": validated["story_revision_id"],
        "route_ids": route_ids,
        "queries": queries,
        "profile": [first_route["research_profile_id"], first_route["research_profile_version"]],
        "policy_version": policy_version,
    }
    binding_hash = stable_hash(json_dumps(request_binding))
    request_id = str(uuid.uuid5(_NAMESPACE, binding_hash))
    reason = " ".join(dict.fromkeys(route["reason"].strip() for route in selected))[:2_000]
    request = ResearchRequest.from_mapping({
        "schema_version": "1.1",
        "request_id": request_id,
        "parent_task_id": parent_task_id,
        "story_id": story_id,
        "story_revision_id": validated["story_revision_id"],
        "requester_role_id": role_id,
        "requester_persona_id": persona_id,
        "research_profile_id": first_route["research_profile_id"],
        "research_profile_version": first_route["research_profile_version"],
        "question": queries[0],
        "queries": queries,
        "entity_ids": first_route["entity_ids"],
        "required_evidence_kinds": first_route["required_evidence_kinds"],
        "preferred_source_ids": first_route["preferred_source_ids"],
        "preferred_domains": first_route["preferred_domains"],
        "languages": first_route["languages"] or ["pt-BR"],
        "time_window": first_route["time_window"],
        "versions_configurations": first_route["versions_configurations"],
        "known_evidence_ids": first_route["known_evidence_ids"],
        "exclusions": first_route["exclusions"],
        "max_sources": MAX_SOURCES,
        "max_requests": MAX_REQUESTS,
        "max_bytes": MAX_BYTES,
        "max_duration_seconds": MAX_DURATION_SECONDS,
        "reason": reason,
        "allowed_scope": [RADAR_INDEX_SCOPE],
        "idempotency_key": f"research-{binding_hash[:48]}",
        "human_gate_if_sensitive": False,
    })
    base["accepted_route_ids"] = route_ids
    base["status"] = "enqueued_index_only" if not base["pending_research"] else "partial_index_only_pending"
    base["request"] = request.to_dict()
    return base
