"""Safe conversion of natural-language research needs into scoped requests."""

from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Mapping
from typing import Any

from .agent_contracts import EPISTEMIC_STATUSES, ResearchRequest
from .db import json_dumps, stable_hash
from .research_service import DEFAULT_RESEARCH_PROFILES, PUBLIC_SOURCES_SCOPE, RADAR_INDEX_SCOPE


POLICY_SCHEMA_VERSION = "ResearchMediationPolicy.v1"
MEDIATION_VERSION = "1.2.0"
_REQUEST_ID_COMPAT_VERSION = "1.1.0"
MAX_SUGGESTIONS = 2
MAX_SOURCES = 5
MAX_REQUESTS = 1
MAX_BYTES = 65_536
MAX_DURATION_SECONDS = 45
_SPACE = re.compile(r"\s+")
_URL = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_NAMESPACE = uuid.UUID("e9d729dd-4bdf-5e1c-aea5-d2e2452e0572")
_STOP_WORDS = frozenset({
    "a", "as", "ao", "aos", "com", "da", "das", "de", "do", "dos", "e", "em", "entre", "foram",
    "how", "is", "na", "nas", "no", "nos", "o", "of", "os", "ou", "para", "por", "que", "qual",
    "quais", "the", "um", "uma", "what", "when", "where", "which", "who", "with", "did", "was", "were",
    "can", "could", "please", "me", "my", "it", "this", "that", "their", "they", "about", "more",
})
_SYNONYM_GROUPS = (
    frozenset({"release", "releases", "released", "launch", "launched", "lancamento", "lancou"}),
    frozenset({"version", "versions", "tag", "build", "versao", "versoes"}),
    frozenset({"change", "changes", "changelog", "notes", "novidades", "mudanca", "mudancas", "alteracoes"}),
    frozenset({"date", "published", "publish", "publication", "data", "publicado", "publicacao"}),
    frozenset({"official", "upstream", "maintainer", "maintainers", "officially", "oficial", "oficiais"}),
)


def _normalized(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    return _SPACE.sub(" ", " ".join(_TOKEN.findall(plain))).strip()


def _tokens(value: str) -> set[str]:
    raw = {token for token in _TOKEN.findall(_normalized(value)) if token not in _STOP_WORDS and len(token) > 2}
    expanded = set(raw)
    for group in _SYNONYM_GROUPS:
        if raw.intersection(group):
            expanded.update(group)
    return expanded


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(nested) for nested in value]
    return value


def _profile_index() -> dict[tuple[str, str], Any]:
    return {(profile.profile_id, profile.version): profile for profile in DEFAULT_RESEARCH_PROFILES}


def _text(value: Any, name: str, maximum: int = 2_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} precisa ser texto nÃ£o vazio de atÃ© {maximum} caracteres")
    text = value.strip()
    if any(ord(char) < 32 and char not in "\t\n\r" for char in text) or _URL.search(text):
        raise ValueError(f"{name} nÃ£o pode conter controle ou URL fornecida pelo modelo")
    return text


def _domain(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 253 or ":" in value or "/" in value or "@" in value:
        raise ValueError(f"{name} precisa ser um hostname exato")
    normalized = value.rstrip(".").casefold()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", normalized):
        raise ValueError(f"{name} precisa ser um hostname ASCII exato")
    if ".." in normalized or any(not label or len(label) > 63 for label in normalized.split(".")):
        raise ValueError(f"{name} possui rÃ³tulo de hostname invÃ¡lido")
    return normalized


def _validate_route(route: Any, index: int) -> dict[str, Any]:
    if not isinstance(route, Mapping):
        raise ValueError(f"research route {index} precisa ser objeto")
    required = {
        "route_id", "question", "purpose", "research_profile_id", "research_profile_version",
        "required_evidence_kinds", "reason",
    }
    optional = {
        "entity_ids", "preferred_source_ids", "preferred_domains", "languages", "time_window",
        "versions_configurations", "known_evidence_ids", "exclusions", "intent_terms", "allowed_scope",
    }
    if required - route.keys() or route.keys() - required - optional:
        raise ValueError(f"research route {index} tem campos ausentes ou desconhecidos")
    normalized = dict(route)
    for field, maximum in (("route_id", 128), ("question", 2_000), ("purpose", 2_000), ("reason", 2_000),
                           ("research_profile_id", 128), ("research_profile_version", 64)):
        normalized[field] = _text(normalized.get(field), f"research route {index}.{field}", maximum)
    if (normalized["research_profile_id"], normalized["research_profile_version"]) not in _profile_index():
        raise ValueError(f"research route {index} referencia perfil nÃ£o registrado")
    kinds = normalized["required_evidence_kinds"]
    if not isinstance(kinds, (list, tuple)) or not kinds or any(kind not in EPISTEMIC_STATUSES for kind in kinds):
        raise ValueError(f"research route {index} precisa de required_evidence_kinds registrados")
    scopes = normalized.setdefault("allowed_scope", [RADAR_INDEX_SCOPE])
    if not isinstance(scopes, (list, tuple)) or not scopes or any(
        not isinstance(scope, str) or scope not in {RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE} for scope in scopes
    ):
        raise ValueError(f"research route {index}.allowed_scope excede as permissÃµes conhecidas")
    normalized["allowed_scope"] = list(dict.fromkeys(scopes))
    for field in ("entity_ids", "preferred_source_ids", "languages", "known_evidence_ids", "exclusions"):
        value = normalized.setdefault(field, [])
        if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) or len(item) > 500 for item in value):
            raise ValueError(f"research route {index}.{field} precisa ser uma lista de strings curtas")
        normalized[field] = list(dict.fromkeys(value))
    domains = normalized.setdefault("preferred_domains", [])
    if not isinstance(domains, (list, tuple)):
        raise ValueError(f"research route {index}.preferred_domains precisa ser uma lista")
    normalized["preferred_domains"] = [_domain(item, f"research route {index}.preferred_domains") for item in domains]
    intent_terms = normalized.setdefault("intent_terms", [])
    if not isinstance(intent_terms, (list, tuple)) or any(
        not isinstance(item, str) or not item.strip() or len(item) > 160 for item in intent_terms
    ):
        raise ValueError(f"research route {index}.intent_terms precisa ser uma lista de termos curtos")
    normalized["intent_terms"] = list(intent_terms)
    for field in ("time_window", "versions_configurations"):
        value = normalized.setdefault(field, {})
        if not isinstance(value, Mapping):
            raise ValueError(f"research route {index}.{field} precisa ser objeto")
        normalized[field] = dict(value)
    return normalized


def validate_policy(policy: Any, *, story_id: str, role_id: str, persona_id: str | None) -> dict[str, Any]:
    if not isinstance(policy, Mapping) or policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise ValueError("ResearchMediationPolicy.v1 ausente ou invÃ¡lida")
    if role_id != "persona_writer" or not persona_id:
        raise ValueError("mediaÃ§Ã£o automÃ¡tica exige persona_writer e persona aprovada")
    required = {"schema_version", "story_revision_id", "routes"}
    optional = {"authorization_ref", "authorized_domains"}
    if required - policy.keys() or policy.keys() - required - optional:
        raise ValueError("ResearchMediationPolicy tem campos ausentes ou desconhecidos")
    revision_id = _text(policy.get("story_revision_id"), "story_revision_id", 128)
    routes_raw = policy.get("routes")
    if not isinstance(routes_raw, (list, tuple)) or not routes_raw or len(routes_raw) > 16:
        raise ValueError("ResearchMediationPolicy precisa de 1 a 16 rotas explÃ­citas")
    routes = [_validate_route(route, index) for index, route in enumerate(routes_raw, start=1)]
    route_ids = [route["route_id"] for route in routes]
    if len(route_ids) != len(set(route_ids)):
        raise ValueError("ResearchMediationPolicy contÃ©m route_id duplicado")
    if any(not _normalized(route["question"]) or not _normalized(route["purpose"]) for route in routes):
        raise ValueError("ResearchMediationPolicy contÃ©m rota sem question/purpose")

    external_routes = [route for route in routes if PUBLIC_SOURCES_SCOPE in route["allowed_scope"]]
    if external_routes:
        authorization_ref = _text(policy.get("authorization_ref"), "authorization_ref", 128)
        if not re.fullmatch(r"(?:issue|github-issue)[:#-][0-9]+", authorization_ref, flags=re.IGNORECASE):
            raise ValueError("Pesquisa externa exige uma autorizaÃ§Ã£o de Issue versionada")
        domains_raw = policy.get("authorized_domains")
        if not isinstance(domains_raw, (list, tuple)) or not domains_raw:
            raise ValueError("Pesquisa externa exige allowlist de domÃ­nios exatos")
        domains = [_domain(item, "authorized_domains") for item in domains_raw]
        if len(domains) != len(set(domains)):
            raise ValueError("authorized_domains contÃ©m domÃ­nio repetido")
        for route in external_routes:
            if not route["preferred_source_ids"] or not route["preferred_domains"]:
                raise ValueError("Pesquisa externa exige source_ids e domains confiÃ¡veis")
            if set(route["preferred_domains"]) - set(domains):
                raise ValueError("Rota excede os domÃ­nios autorizados pela Issue")
    else:
        authorization_ref = policy.get("authorization_ref")
        domains = policy.get("authorized_domains", [])
        if authorization_ref is not None or domains:
            raise ValueError("AutorizaÃ§Ã£o externa declarada sem rota de pesquisa pÃºblica")
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "story_revision_id": revision_id,
        "authorization_ref": authorization_ref,
        "authorized_domains": domains,
        "routes": routes,
    }


def _route_score(question: str, purpose: str, route: Mapping[str, Any]) -> tuple[int, float]:
    normalized_pair = (_normalized(question), _normalized(purpose))
    if normalized_pair == (_normalized(str(route["question"])), _normalized(str(route["purpose"]))):
        return 999, 1.0
    query_tokens = _tokens(f"{question} {purpose}")
    anchors = set().union(*(_tokens(str(item)) for item in route.get("intent_terms", ()))) if route.get("intent_terms") else set()
    anchors.update(_tokens(f"{route['question']} {route['purpose']}"))
    overlap = len(query_tokens & anchors)
    # Keep confidence within [0, 1]. A five-token cap let long queries and
    # synonym expansion produce scores above one, which could outrank an
    # exact match on a different route during the one-request budget choice.
    denominator = max(1, len(query_tokens))
    return overlap, overlap / denominator


def _routes_compatible(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    """Only consolidate requests that share the same trusted retrieval boundary."""

    fields = (
        "research_profile_id", "research_profile_version", "required_evidence_kinds",
        "entity_ids", "preferred_source_ids", "preferred_domains", "languages", "time_window",
        "versions_configurations", "known_evidence_ids", "exclusions", "allowed_scope",
    )
    return all(left.get(field) == right.get(field) for field in fields)


def mediate_requested_research(
    suggestions: Any,
    *,
    policy: Mapping[str, Any] | None,
    parent_task_id: str,
    story_id: str,
    role_id: str,
    persona_id: str | None,
) -> dict[str, Any]:
    """Map paraphrased questions through trusted route constraints; never trust model scope."""
    base: dict[str, Any] = {
        "mediation_version": MEDIATION_VERSION,
        "status": "none_requested",
        "policy_sha256": stable_hash(json_dumps(_plain(policy))) if policy is not None else None,
        "authorization_ref": policy.get("authorization_ref") if isinstance(policy, Mapping) else None,
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
        "accepted_route_ids": [], "pending_research": [], "deduplicated_suggestions": [],
        "ignored_model_fields": [], "request": None,
    }
    if not isinstance(suggestions, (list, tuple)) or not suggestions:
        return base
    if policy is None:
        base["status"] = "hold_missing_motor_policy"
        base["pending_research"] = [{"suggestion_index": index, "reason": "trusted_motor_policy_missing"}
                                    for index, _ in enumerate(suggestions, start=1)]
        return base
    try:
        validated = validate_policy(policy, story_id=story_id, role_id=role_id, persona_id=persona_id)
    except (TypeError, ValueError) as error:
        base["status"] = "hold_invalid_motor_policy"
        base["pending_research"] = [{"reason": str(error)}]
        return base

    accepted: list[tuple[int, dict[str, Any], str, str, int, float]] = []
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
        try:
            question = _text(question, "question")
            purpose = _text(purpose, "purpose")
        except ValueError:
            base["pending_research"].append({"suggestion_index": index, "reason": "question_or_purpose_invalid"})
            continue
        key = (_normalized(question), _normalized(purpose))
        if key in seen:
            base["deduplicated_suggestions"].append(index)
            continue
        seen.add(key)
        scored = sorted(
            ((_route_score(question, purpose, route), route) for route in validated["routes"]),
            key=lambda item: (-item[0][0], -item[0][1], str(item[1]["route_id"])),
        )
        (overlap, score), route = scored[0]
        second_score = scored[1][0][1] if len(scored) > 1 else 0.0
        if overlap < 2 or score < 0.25 or (len(scored) > 1 and score - second_score < 0.10):
            base["pending_research"].append({"suggestion_index": index, "reason": "no_confident_trusted_intent_match"})
            continue
        accepted.append((index, route, question, purpose, overlap, score))

    if not accepted:
        base["status"] = "hold_unmapped_suggestions"
        return base
    accepted.sort(key=lambda item: (-item[5], item[0]))
    suggestion_index, route, question, purpose, overlap, score = accepted[0]
    consolidated = [accepted[0]]
    for item in accepted[1:]:
        item_index, item_route, item_question, item_purpose, _item_overlap, _item_score = item
        if _routes_compatible(route, item_route):
            consolidated.append(item)
        else:
            base["pending_research"].append({
                "suggestion_index": item_index,
                "question": item_question,
                "purpose": item_purpose,
                "route_id": item_route["route_id"],
                "reason": "incompatible_trusted_route_within_request_budget",
            })
    consolidated.sort(key=lambda item: item[0])
    profile = _profile_index()[(route["research_profile_id"], route["research_profile_version"])]
    allowed_scope = tuple(route["allowed_scope"])
    if RADAR_INDEX_SCOPE not in profile.allowed_scopes or set(allowed_scope) - set(profile.allowed_scopes):
        base["status"] = "hold_profile_disallows_requested_scope"
        base["pending_research"] = [{"suggestion_index": suggestion_index, "reason": "profile_scope_mismatch"}]
        return base
    request_queries = list(dict.fromkeys(
        query
        for item in consolidated
        for query in (item[2], item[3])
    ))
    route_ids = list(dict.fromkeys(item[1]["route_id"] for item in consolidated))
    if len(consolidated) == 1:
        # Keep archived one-question IDs stable so recovery reuses the same
        # request and never spends the source quota again.
        binding = {
            "parent_task_id": parent_task_id, "story_id": story_id,
            "story_revision_id": validated["story_revision_id"], "route_id": route["route_id"],
            "question": question, "purpose": purpose,
            "profile": [route["research_profile_id"], route["research_profile_version"]],
            "policy_version": _REQUEST_ID_COMPAT_VERSION,
        }
    else:
        binding = {
            "parent_task_id": parent_task_id, "story_id": story_id,
            "story_revision_id": validated["story_revision_id"], "route_ids": route_ids,
            "queries": request_queries,
            "profile": [route["research_profile_id"], route["research_profile_version"]],
            "policy_version": MEDIATION_VERSION,
        }
    binding_hash = stable_hash(json_dumps(binding))
    request = ResearchRequest.from_mapping({
        "schema_version": "1.1",
        "request_id": str(uuid.uuid5(_NAMESPACE, binding_hash)),
        "parent_task_id": parent_task_id, "story_id": story_id,
        "story_revision_id": validated["story_revision_id"],
        "requester_role_id": role_id, "requester_persona_id": persona_id,
        "research_profile_id": route["research_profile_id"],
        "research_profile_version": route["research_profile_version"],
        "question": question, "queries": request_queries,
        "entity_ids": route["entity_ids"], "required_evidence_kinds": route["required_evidence_kinds"],
        "preferred_source_ids": route["preferred_source_ids"], "preferred_domains": route["preferred_domains"],
        "languages": route["languages"] or ["pt-BR"], "time_window": route["time_window"],
        "versions_configurations": route["versions_configurations"],
        "known_evidence_ids": route["known_evidence_ids"], "exclusions": route["exclusions"],
        "max_sources": MAX_SOURCES, "max_requests": MAX_REQUESTS,
        "max_bytes": MAX_BYTES, "max_duration_seconds": MAX_DURATION_SECONDS,
        "reason": (
            f"{route['reason'].strip()} Consolidated suggestion indices: "
            f"{','.join(str(item[0]) for item in consolidated)}; purposes are preserved in queries."
        )[:2_000],
        "allowed_scope": list(allowed_scope),
        "idempotency_key": f"research-{binding_hash[:48]}", "human_gate_if_sensitive": False,
    })
    base["accepted_route_ids"] = route_ids
    base["matched_intent_overlap"] = overlap
    base["matched_intent_score"] = round(score, 4)
    base["consolidated_suggestion_indices"] = [item[0] for item in consolidated]
    base["status"] = "enqueued_public_and_index" if PUBLIC_SOURCES_SCOPE in allowed_scope else "enqueued_index_only"
    base["request"] = request.to_dict()
    return base
