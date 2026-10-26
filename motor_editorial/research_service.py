"""Shared, cache-first research service over the Radar's local evidence index.

No provider is active by default. An explicitly injected provider may extend the
local index later, under a versioned profile, request scope, and hard budget.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping, Protocol, Sequence
from urllib.parse import urlsplit

from .agent_contracts import (
    ArtifactReference,
    RESEARCH_STATUSES,
    ResearchPacket,
    ResearchRequest,
)
from .radar_store import RadarStore, RadarStoreError


RADAR_INDEX_SCOPE = "read:radar_index"
PUBLIC_SOURCES_SCOPE = "read:registered_public_sources"
RESEARCH_PROFILE_VERSION = "1.0.0"
_SUPPORTED_SCOPES = frozenset({RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE})
_STOP_WORDS = frozenset({
    "a", "as", "ao", "aos", "com", "da", "das", "de", "do", "dos", "e", "em", "entre", "for", "foram",
    "how", "is", "na", "nas", "no", "nos", "o", "of", "os", "ou", "para", "por", "que", "qual", "quais",
    "the", "um", "uma", "what", "when", "where", "which", "who", "with",
})
_TOKEN_RE = re.compile(r"[\w%]+", re.UNICODE)


@dataclass(frozen=True)
class ResearchProfile:
    profile_id: str
    version: str
    focus: tuple[str, ...]
    allowed_scopes: tuple[str, ...] = (RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE)
    min_match_ratio: float = 0.20


DEFAULT_RESEARCH_PROFILES = (
    ResearchProfile("radar.general.v1", RESEARCH_PROFILE_VERSION, ("general",), min_match_ratio=0.15),
    ResearchProfile("research.hardware.v1", RESEARCH_PROFILE_VERSION, ("hardware", "benchmark", "method")),
    ResearchProfile("research.games.v1", RESEARCH_PROFILE_VERSION, ("games", "patch", "mechanics", "interviews")),
    ResearchProfile("research.creators.v1", RESEARCH_PROFILE_VERSION, ("creators", "mods", "changelog", "license")),
)


@dataclass(frozen=True)
class ResearchBudget:
    max_sources: int
    max_requests: int
    max_bytes: int
    max_duration_seconds: int
    allowed_scope: tuple[str, ...]
    preferred_source_ids: tuple[str, ...]
    preferred_domains: tuple[str, ...]


@dataclass(frozen=True)
class ResearchProviderResult:
    """A connector adapter returns persisted Radar IDs, never unverified text."""

    status: str
    document_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    retry_at: str | None = None
    requests_used: int = 0
    bytes_read: int = 0
    sources_considered: int = 0
    elapsed_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.status not in RESEARCH_STATUSES:
            raise ValueError("ResearchProviderResult.status inválido.")
        for name in ("requests_used", "bytes_read", "sources_considered"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} precisa ser inteiro não negativo.")
        if isinstance(self.elapsed_seconds, bool) or not isinstance(self.elapsed_seconds, (int, float)):
            raise ValueError("elapsed_seconds precisa ser numérico.")
        if not math.isfinite(float(self.elapsed_seconds)) or self.elapsed_seconds < 0:
            raise ValueError("elapsed_seconds precisa ser finito e não negativo.")


        for name in ("document_ids", "claim_ids", "missing_evidence", "constraints"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{name} must be a tuple of non-empty text values.")
        if len(set(self.document_ids)) != len(self.document_ids) or len(set(self.claim_ids)) != len(self.claim_ids):
            raise ValueError("ResearchProviderResult cannot contain duplicate IDs.")
        if len(set(self.missing_evidence)) != len(self.missing_evidence) or len(set(self.constraints)) != len(self.constraints):
            raise ValueError("ResearchProviderResult cannot contain duplicate status text.")
        if any(len(value) > 500 for group in (self.missing_evidence, self.constraints) for value in group):
            raise ValueError("ResearchProviderResult status text exceeds 500 characters.")
        if self.retry_at is not None and not isinstance(self.retry_at, str):
            raise ValueError("retry_at must be an ISO-8601 string or None.")


class ResearchProvider(Protocol):
    def search(
        self,
        request: ResearchRequest,
        profile: ResearchProfile,
        *,
        cached_document_ids: tuple[str, ...],
        budget: ResearchBudget,
    ) -> ResearchProviderResult: ...


@dataclass(frozen=True)
class ResearchExecutionResult:
    request_id: str
    story_id: str
    story_revision_id: str | None
    packet: ResearchPacket
    packet_id: str | None
    cache_hit: bool
    index_hit_count: int
    provider_called: bool


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


def _normalized(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in folded if not unicodedata.combining(char))


def _tokens(value: str) -> set[str]:
    return {
        token for token in _TOKEN_RE.findall(_normalized(value))
        if token not in _STOP_WORDS and (len(token) > 2 or token.isdigit())
    }


def _flatten_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [item for nested in value.values() for item in _flatten_text(nested)]
    if isinstance(value, (list, tuple)):
        return [item for nested in value for item in _flatten_text(nested)]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [str(value)]
    return []


def _request_terms(request: ResearchRequest) -> tuple[set[str], tuple[str, ...]]:
    phrases = tuple(query for query in request.queries if query.strip())
    values = [request.question, *request.queries, *_flatten_text(request.versions_configurations)]
    return set().union(*(_tokens(value) for value in values)) if values else set(), phrases


def _day(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _domain_matches(host: str, requested: str) -> bool:
    normalized_host = host.casefold().rstrip(".")
    normalized_domain = requested.casefold().strip().rstrip(".")
    return normalized_host == normalized_domain or normalized_host.endswith("." + normalized_domain)


class ResearchService:
    """Search one shared Radar index, then optionally call a scoped adapter."""

    def __init__(
        self,
        *,
        store: RadarStore,
        provider: ResearchProvider | None = None,
        profiles: Sequence[ResearchProfile] = DEFAULT_RESEARCH_PROFILES,
    ):
        self.store = store
        self.provider = provider
        profile_list = tuple(profiles)
        profile_map = {(profile.profile_id, profile.version): profile for profile in profile_list}
        if len(profile_map) != len(profile_list):
            raise ValueError("ResearchProfile duplicado.")
        if not profile_map:
            raise ValueError("ResearchService exige ao menos um ResearchProfile.")
        self.profiles = profile_map

    def execute(self, request: ResearchRequest, *, now: str | datetime | None = None) -> ResearchExecutionResult:
        if not isinstance(request, ResearchRequest):
            raise ValueError("ResearchService exige ResearchRequest versionado.")
        fetched_at = _utc_iso(now)
        self.store.save_research_request(request, now=fetched_at)
        cached = self._cached_packet(request.request_id, fetched_at)
        if cached is not None:
            packet_id, packet = cached
            return ResearchExecutionResult(
                request_id=request.request_id, story_id=request.story_id,
                story_revision_id=request.story_revision_id, packet=packet, packet_id=packet_id,
                cache_hit=True, index_hit_count=len(packet.document_refs), provider_called=False,
            )

        profile = self.profiles.get((request.research_profile_id, request.research_profile_version))
        blocked_reason = self._validate_request(request, profile)
        if blocked_reason is not None:
            packet_id, packet = self._save_packet(
                request, status="blocked", fetched_at=fetched_at,
                missing=request.required_evidence_kinds, constraints=(blocked_reason,),
            )
            return self._result(request, packet, packet_id=packet_id, index_hits=0, provider_called=False)

        assert profile is not None
        local_documents = self._search_index(request, profile)
        local_ids = tuple(document["document_id"] for document in local_documents)
        references, claims, lineage, excerpts, last_material = self._evidence_for_documents(local_documents)
        claim_rows = {row["claim_id"]: row for row in self.store.list_rows("radar_claims")}
        local_evidence_kinds = {claim_rows[claim_id]["epistemic_status"] for claim_id in claims}
        missing_evidence = tuple(kind for kind in request.required_evidence_kinds if kind not in local_evidence_kinds)
        status = "found" if local_documents and not missing_evidence else ("partial" if local_documents else "not_found")
        constraints: list[str] = []
        if local_documents and missing_evidence:
            constraints.append("shared Radar index has documents, but the claim ledger lacks required evidence kinds")
        if missing_evidence and PUBLIC_SOURCES_SCOPE not in request.allowed_scope:
            constraints.append("required evidence was not found in local Radar; external search scope was not granted")
        elif missing_evidence and self.provider is None:
            constraints.append("only the shared Radar index was searched; no external retriever is configured")

        provider_called = False
        retry_at: str | None = None
        packet_ids = list(references)
        packet_claims = list(claims)
        cached_source_ids = {str(document["source_id"]) for document in local_documents}
        remaining_source_budget = max(0, request.max_sources - len(cached_source_ids))
        if self.provider is not None and PUBLIC_SOURCES_SCOPE in request.allowed_scope and remaining_source_budget == 0:
            constraints.append("source budget was consumed by shared Radar cache hits")
        if (
            self.provider is not None
            and PUBLIC_SOURCES_SCOPE in request.allowed_scope
            and PUBLIC_SOURCES_SCOPE in profile.allowed_scopes
            and remaining_source_budget > 0
            and missing_evidence
        ):
            provider_called = True
            budget = ResearchBudget(
                max_sources=remaining_source_budget, max_requests=request.max_requests,
                max_bytes=request.max_bytes, max_duration_seconds=request.max_duration_seconds,
                allowed_scope=tuple(request.allowed_scope),
                preferred_source_ids=tuple(request.preferred_source_ids),
                preferred_domains=tuple(request.preferred_domains),
            )
            try:
                provider_result = self.provider.search(
                    request, profile, cached_document_ids=local_ids, budget=budget,
                )
            except Exception as error:
                provider_result = ResearchProviderResult(
                    status="blocked", constraints=(f"retriever unavailable ({type(error).__name__})",),
                )
            if not isinstance(provider_result, ResearchProviderResult):
                violation = "retriever returned an invalid ResearchProviderResult"
                provider_result = ResearchProviderResult(status="blocked", constraints=(violation,))
            else:
                violation = self._budget_violation(budget, provider_result)
                if set(provider_result.missing_evidence) - set(request.required_evidence_kinds):
                    violation = "retriever returned an unrequested missing_evidence category"
            provider_documents: list[dict[str, Any]] = []
            if violation is None:
                try:
                    provider_documents = self._validate_provider_references(request, provider_result, profile)
                except RadarStoreError as error:
                    violation = str(error)
            if violation is None:
                combined_source_ids = cached_source_ids | {str(document["source_id"]) for document in provider_documents}
                if len(combined_source_ids) > request.max_sources:
                    violation = "retriever exceeded max_sources after shared-cache hits"
            if violation is None:
                if provider_result.status == "found" and not (provider_documents or provider_result.claim_ids):
                    violation = "retriever returned found without a persisted evidence reference"
            if violation is not None:
                status = "partial" if packet_ids or packet_claims else "blocked"
                constraints.append(violation)
                missing_evidence = tuple(request.required_evidence_kinds)
            else:
                provider_references, provider_claims, provider_lineage, provider_excerpts, provider_last_material = (
                    self._evidence_for_documents(provider_documents, claim_ids=provider_result.claim_ids)
                )
                by_ref = {item.ref: item for item in [*packet_ids, *provider_references]}
                packet_ids = list(by_ref.values())
                packet_claims = sorted(set(packet_claims).union(provider_claims, provider_result.claim_ids))
                lineage_by_key = {
                    (
                        entry.get("document_id"), entry.get("source_id"), entry.get("claim_id"),
                        entry.get("origin_group_id"), entry.get("relation_type"), entry.get("based_on_source_id"),
                    ): entry
                    for entry in [*lineage, *provider_lineage]
                }
                lineage = [lineage_by_key[key] for key in sorted(lineage_by_key, key=lambda item: tuple(str(part or "") for part in item))]
                excerpts = list(dict.fromkeys([*excerpts, *provider_excerpts]))
                last_material = max((value for value in (last_material, provider_last_material) if value), default=None)
                available_claim_kinds = {
                    claim_rows.get(claim_id, {}).get("epistemic_status")
                    for claim_id in packet_claims
                }
                reported_missing = set(provider_result.missing_evidence)
                missing_evidence = tuple(
                    kind for kind in request.required_evidence_kinds
                    if kind not in available_claim_kinds
                    or (kind in reported_missing and kind not in local_evidence_kinds)
                )
                if provider_result.constraints:
                    constraints.append("external retriever reported additional constraints")
                retry_at = provider_result.retry_at
                if provider_result.status == "found" and not missing_evidence:
                    status = "found"
                elif provider_result.status == "rate_limited" and not packet_ids and not packet_claims:
                    status = "rate_limited"
                elif provider_result.status == "blocked" and not packet_ids and not packet_claims:
                    status = "blocked"
                elif packet_ids or packet_claims:
                    status = "partial"
                else:
                    status = provider_result.status

        packet_id, packet = self._save_packet(
            request, status=status, fetched_at=fetched_at,
            document_refs=packet_ids, claim_refs=packet_claims, source_lineage=lineage,
            excerpts=excerpts, new_material_since=last_material,
            missing=missing_evidence, constraints=constraints, retry_at=retry_at,
        )
        return self._result(
            request, packet, packet_id=packet_id, index_hits=len(local_documents), provider_called=provider_called,
        )

    def _validate_request(self, request: ResearchRequest, profile: ResearchProfile | None) -> str | None:
        if profile is None:
            return "research profile/version is not registered"
        if request.schema_version != "1.1" or not request.story_revision_id:
            return "request must bind ResearchRequest v1.1 to a story revision"
        if request.requester_role_id == "persona_writer" and not request.requester_persona_id:
            return "persona_writer request must identify the approved journalist profile"
        if RADAR_INDEX_SCOPE not in request.allowed_scope:
            return "request scope does not authorize the shared Radar index"
        if set(request.allowed_scope) - set(profile.allowed_scopes) or set(request.allowed_scope) - _SUPPORTED_SCOPES:
            return "request scope exceeds the selected ResearchProfile"
        start_value = request.time_window.get("from", request.time_window.get("start"))
        end_value = request.time_window.get("to", request.time_window.get("end"))
        start = _day(start_value)
        end = _day(end_value)
        if (start_value is not None and start is None) or (end_value is not None and end is None):
            return "request time_window contains an invalid ISO date"
        if start is not None and end is not None and start > end:
            return "request time_window starts after it ends"
        return None

    def _cached_packet(self, request_id: str, now: str) -> tuple[str, ResearchPacket] | None:
        rows = self.store.list_rows(
            "radar_research_packets", where_column="request_id", where_value=request_id,
        )
        if not rows:
            return None
        latest = max(rows, key=lambda row: int(row["version"]))
        packet = ResearchPacket.from_mapping(json.loads(latest["packet_json"]))
        if packet.retry_at:
            retry_at = datetime.fromisoformat(packet.retry_at.replace("Z", "+00:00"))
            current = datetime.fromisoformat(now.replace("Z", "+00:00"))
            if current >= retry_at:
                return None
        return latest["packet_id"], packet

    def _search_index(self, request: ResearchRequest, profile: ResearchProfile) -> list[dict[str, Any]]:
        terms, phrases = _request_terms(request)
        sources = {row["source_id"]: row for row in self.store.list_rows("radar_sources")}
        documents = {row["document_id"]: row for row in self.store.list_rows("radar_documents")}
        if not terms and not request.entity_ids:
            return []

        links_by_document: dict[str, set[str]] = defaultdict(set)
        documents_by_entity: dict[str, set[str]] = defaultdict(set)
        for link in self.store.list_rows("radar_document_entities"):
            links_by_document[link["document_id"]].add(link["entity_id"])
            documents_by_entity[link["entity_id"]].add(link["document_id"])

        start = _day(request.time_window.get("from", request.time_window.get("start")))
        end = _day(request.time_window.get("to", request.time_window.get("end")))
        excluded = tuple(_normalized(item) for item in request.exclusions)
        allowed_languages = {item.casefold() for item in request.languages}
        known_evidence = set(request.known_evidence_ids)
        candidates: dict[str, float] = {}

        def text_score(value: str) -> float:
            normalized = _normalized(value)
            overlap = len(terms.intersection(_tokens(value))) / max(1, len(terms))
            if any(_normalized(phrase) in normalized for phrase in phrases):
                overlap = max(overlap, profile.min_match_ratio)
            return overlap

        def document_allowed(document: Mapping[str, Any]) -> bool:
            source = sources.get(str(document["source_id"]))
            if source is None or source["access_policy"] != "allowed" or source["rights_status"] == "blocked":
                return False
            if document["access_policy"] != "allowed" or document["rights_status"] == "blocked":
                return False
            if request.preferred_source_ids and document["source_id"] not in request.preferred_source_ids:
                return False
            host = urlsplit(document["canonical_url"]).hostname or ""
            if request.preferred_domains and not any(_domain_matches(host, item) for item in request.preferred_domains):
                return False
            if allowed_languages and (document["language"] or "und").casefold() not in allowed_languages:
                return False
            published = _day(document["published_at"])
            if start and (published is None or published < start):
                return False
            if end and (published is None or published > end):
                return False
            document_id = str(document["document_id"])
            if document_id in known_evidence or f"radar://document/{document_id}" in known_evidence:
                return False
            if document["source_id"] in known_evidence:
                return False
            source = sources[str(document["source_id"])]
            text = _normalized(" ".join((
                document["title"] or "", document["summary_snippet"] or "", document["canonical_url"],
                source["display_name"], source["domain"],
            )))
            if any(item and item in text for item in excluded):
                return False
            return True

        focus_terms = _tokens(" ".join(profile.focus))
        for document_id, document in documents.items():
            if not document_allowed(document):
                continue
            source = sources[str(document["source_id"])]
            searchable = " ".join((
                document["title"] or "", document["summary_snippet"] or "", document["canonical_url"],
                source["display_name"], source["domain"],
            ))
            score = text_score(searchable)
            entity_match = bool(set(request.entity_ids).intersection(links_by_document.get(document_id, set())))
            if entity_match:
                score = max(score, profile.min_match_ratio)
            if score >= profile.min_match_ratio:
                focus_overlap = len(focus_terms.intersection(_tokens(str(document["title"])))) / max(1, len(focus_terms))
                candidates[document_id] = score + focus_overlap * 0.1

        entity_names = {row["entity_id"]: row["canonical_name"] for row in self.store.list_rows("radar_entities")}
        aliases: dict[str, list[str]] = defaultdict(list)
        for alias in self.store.list_rows("radar_entity_aliases"):
            aliases[alias["entity_id"]].append(alias["alias"])
        matched_entities = set(request.entity_ids)
        for entity_id, name in entity_names.items():
            names = [str(name), *aliases.get(entity_id, [])]
            if any(text_score(value) >= profile.min_match_ratio for value in names):
                matched_entities.add(entity_id)
        for entity_id in matched_entities:
            for document_id in documents_by_entity.get(entity_id, set()):
                document = documents.get(document_id)
                if document is not None and document_allowed(document):
                    candidates[document_id] = max(candidates.get(document_id, 0.0), profile.min_match_ratio + 0.05)

        topic_documents: dict[str, set[str]] = defaultdict(set)
        topic_entities: dict[str, set[str]] = defaultdict(set)
        for link in self.store.list_rows("radar_document_topics"):
            topic_documents[link["topic_id"]].add(link["document_id"])
        for link in self.store.list_rows("radar_topic_entities"):
            topic_entities[link["topic_id"]].add(link["entity_id"])
        topics_by_id = {row["topic_id"]: row for row in self.store.list_rows("radar_topics")}
        for topic_id, topic in topics_by_id.items():
            score = text_score(str(topic["title"]))
            entity_match = bool(matched_entities.intersection(topic_entities.get(topic_id, set())))
            if score < profile.min_match_ratio and not entity_match:
                continue
            for document_id in topic_documents.get(topic_id, set()):
                document = documents.get(document_id)
                if document is not None and document_allowed(document):
                    candidates[document_id] = max(candidates.get(document_id, 0.0), max(score, profile.min_match_ratio))

        claims_by_id = {row["claim_id"]: row for row in self.store.list_rows("radar_claims")}
        claim_documents: dict[str, set[str]] = defaultdict(set)
        for claim in claims_by_id.values():
            if claim.get("source_document_id"):
                claim_documents[claim["claim_id"]].add(str(claim["source_document_id"]))
        claim_sources = self.store.list_rows("radar_claim_sources")
        for link in claim_sources:
            if link.get("document_id"):
                claim_documents[link["claim_id"]].add(str(link["document_id"]))
        events_by_claim: dict[str, list[str]] = defaultdict(list)
        for event in self.store.list_rows("radar_claim_events"):
            events_by_claim[event["claim_id"]].append(str(event["reason"]))
        for claim_id, claim in claims_by_id.items():
            if claim_id in known_evidence or f"radar://claim/{claim_id}" in known_evidence:
                continue
            event_reasons = events_by_claim.get(claim_id, [])
            claim_text = " ".join((str(claim["statement"]), *event_reasons))
            score = text_score(claim_text)
            topic_match = text_score(str(topics_by_id.get(claim["topic_id"], {}).get("title", ""))) >= profile.min_match_ratio
            entity_match = bool(matched_entities.intersection(topic_entities.get(claim["topic_id"], set())))
            if score < profile.min_match_ratio and not topic_match and not entity_match:
                continue
            for document_id in claim_documents.get(claim_id, set()):
                document = documents.get(document_id)
                if document is not None and document_allowed(document):
                    claim_score = max(score, profile.min_match_ratio)
                    candidates[document_id] = max(candidates.get(document_id, 0.0), claim_score + 0.1)

        ranked = [(score, documents[document_id]) for document_id, score in candidates.items()]
        ranked.sort(key=lambda item: (str(item[1]["fetched_at"]), str(item[1]["document_id"])), reverse=True)
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected: list[dict[str, Any]] = []
        selected_sources: set[str] = set()
        for _score, document in ranked:
            source_id = str(document["source_id"])
            if source_id not in selected_sources:
                if len(selected_sources) >= request.max_sources:
                    continue
                selected_sources.add(source_id)
            selected.append(document)
            if len(selected) >= request.max_sources:
                break
        return selected

    def _evidence_for_documents(
        self, documents: Sequence[Mapping[str, Any]], *, claim_ids: Sequence[str] = (),
    ) -> tuple[list[ArtifactReference], list[str], list[dict[str, Any]], list[str], str | None]:
        source_map = {row["source_id"]: row for row in self.store.list_rows("radar_sources")}
        document_map = {row["document_id"]: row for row in self.store.list_rows("radar_documents")}
        allowed_documents: dict[str, Mapping[str, Any]] = {}
        for candidate in documents:
            document_id = str(candidate["document_id"])
            document = document_map.get(document_id)
            source = source_map.get(str(candidate["source_id"]), {})
            if document is None or source.get("access_policy") != "allowed" or source.get("rights_status") == "blocked":
                continue
            if document.get("access_policy") != "allowed" or document.get("rights_status") == "blocked":
                continue
            allowed_documents[document_id] = document

        document_ids = set(allowed_documents)
        source_ids = {str(document["source_id"]) for document in allowed_documents.values()}
        all_claims = {row["claim_id"]: row for row in self.store.list_rows("radar_claims")}
        claim_sources = self.store.list_rows("radar_claim_sources")
        relevant_claims = set(claim_ids)
        relevant_claims.update(
            claim["claim_id"] for claim in all_claims.values()
            if claim.get("source_document_id") in document_ids
        )
        relevant_claims.update(
            row["claim_id"] for row in claim_sources if row.get("document_id") in document_ids
        )
        republish_by_document: dict[str, list[str]] = defaultdict(list)
        for member in self.store.list_rows("radar_republication_members"):
            republish_by_document[member["document_id"]].append(member["group_id"])

        references: list[ArtifactReference] = []
        lineage: list[dict[str, Any]] = []
        excerpts: list[str] = []
        material_dates: list[datetime] = []
        for document_id, document in sorted(allowed_documents.items()):
            references.append(ArtifactReference(
                ref=f"radar://document/{document_id}", sha256=str(document["content_sha256"]),
            ))
            if document.get("title"):
                excerpts.append(str(document["title"])[:300])
            source = source_map[str(document["source_id"])]
            lineage.append({
                "document_id": document_id,
                "source_id": document["source_id"],
                "publisher": document["publisher"],
                "url": document["canonical_url"],
                "republication_group_ids": sorted(republish_by_document.get(document_id, [])),
                "access_policy": source.get("access_policy"),
            })
            if document.get("modified_at"):
                parsed = datetime.fromisoformat(str(document["modified_at"]).replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    material_dates.append(parsed.astimezone(timezone.utc))

        accepted_claims: list[str] = []
        for claim_id in sorted(relevant_claims):
            claim = all_claims.get(claim_id)
            if claim is None:
                continue
            links = [link for link in claim_sources if link["claim_id"] == claim_id]
            has_allowed_lineage = False
            source_document_id = claim.get("source_document_id")
            if source_document_id in document_ids:
                source_document = allowed_documents[str(source_document_id)]
                lineage.append({
                    "claim_id": claim_id,
                    "epistemic_status": claim["epistemic_status"],
                    "source_id": source_document["source_id"],
                    "document_id": source_document_id,
                    "relation_type": "source_document",
                })
                has_allowed_lineage = True
            for link in links:
                linked_document_id = link.get("document_id")
                source = source_map.get(str(link["source_id"]), {})
                if source.get("access_policy") != "allowed" or source.get("rights_status") == "blocked":
                    continue
                if linked_document_id is not None and linked_document_id not in document_ids:
                    continue
                if str(link["source_id"]) not in source_ids:
                    continue
                lineage.append({
                    "claim_id": claim_id,
                    "epistemic_status": claim["epistemic_status"],
                    "origin_group_id": link["origin_group_id"],
                    "source_id": link["source_id"],
                    "document_id": linked_document_id,
                    "relation_type": link["relation_type"],
                    "based_on_source_id": link.get("based_on_source_id"),
                })
                has_allowed_lineage = True
            if has_allowed_lineage:
                accepted_claims.append(claim_id)
                statement = claim.get("statement")
                if isinstance(statement, str) and statement.strip():
                    excerpts.append(f"{claim.get('epistemic_status', 'unverified_or_disputed')}: {statement[:600]}")
                new_information_since = claim.get("new_information_since")
                if new_information_since:
                    try:
                        parsed = datetime.fromisoformat(str(new_information_since).replace("Z", "+00:00"))
                    except ValueError:
                        parsed = None
                    if parsed is not None and parsed.tzinfo is not None:
                        material_dates.append(parsed.astimezone(timezone.utc))

        material_events = self.store.list_rows("radar_observation_events")
        for event in material_events:
            if event["document_id"] not in document_ids or event["event_type"] not in {
                "first_seen", "title_changed", "body_changed", "corrected",
            }:
                continue
            parsed = datetime.fromisoformat(str(event["observed_at"]).replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                material_dates.append(parsed.astimezone(timezone.utc))

        newest_material = max(material_dates, default=None)
        return (
            references,
            accepted_claims,
            lineage,
            list(dict.fromkeys(excerpts))[:100],
            newest_material.isoformat(timespec="seconds") if newest_material else None,
        )

    def _validate_provider_references(
        self, request: ResearchRequest, result: ResearchProviderResult, profile: ResearchProfile,
    ) -> list[dict[str, Any]]:
        known_docs = {row["document_id"]: row for row in self.store.list_rows("radar_documents")}
        sources = {row["source_id"]: row for row in self.store.list_rows("radar_sources")}
        known_claims = {row["claim_id"]: row for row in self.store.list_rows("radar_claims")}
        claim_sources = self.store.list_rows("radar_claim_sources")
        excluded = tuple(_normalized(item) for item in request.exclusions)
        known_evidence = set(request.known_evidence_ids)
        allowed_languages = {item.casefold() for item in request.languages}
        start = _day(request.time_window.get("from", request.time_window.get("start")))
        end = _day(request.time_window.get("to", request.time_window.get("end")))
        terms, phrases = _request_terms(request)
        entity_documents = {
            row["document_id"] for row in self.store.list_rows("radar_document_entities")
            if row["entity_id"] in request.entity_ids
        }

        def document_allowed(document_id: str, *, must_match: bool = True) -> dict[str, Any]:
            document = known_docs.get(document_id)
            if document is None:
                raise RadarStoreError("Retriever referenced a document absent from the Radar index.")
            source = sources.get(document["source_id"], {})
            if source.get("access_policy") != "allowed" or source.get("rights_status") == "blocked":
                raise RadarStoreError("Retriever referenced a source without allowed policy.")
            if document["access_policy"] != "allowed" or document["rights_status"] == "blocked":
                raise RadarStoreError("Retriever referenced a document without allowed policy.")
            if request.preferred_source_ids and document["source_id"] not in request.preferred_source_ids:
                raise RadarStoreError("Retriever exceeded preferred_source_ids.")
            host = urlsplit(document["canonical_url"]).hostname or ""
            if request.preferred_domains and not any(_domain_matches(host, domain) for domain in request.preferred_domains):
                raise RadarStoreError("Retriever exceeded preferred_domains.")
            if allowed_languages and (document["language"] or "und").casefold() not in allowed_languages:
                raise RadarStoreError("Retriever exceeded the requested language filter.")
            published = _day(document["published_at"])
            if start and (published is None or published < start):
                raise RadarStoreError("Retriever exceeded the requested start date.")
            if end and (published is None or published > end):
                raise RadarStoreError("Retriever exceeded the requested end date.")
            if document_id in known_evidence or f"radar://document/{document_id}" in known_evidence:
                raise RadarStoreError("Retriever returned evidence already known to the request.")
            if document["source_id"] in known_evidence:
                raise RadarStoreError("Retriever returned a source already known to the request.")
            source = sources[str(document["source_id"])]
            text = _normalized(" ".join((
                document["title"] or "", document["summary_snippet"] or "", document["canonical_url"],
                source["display_name"], source["domain"],
            )))
            if any(item and item in text for item in excluded):
                raise RadarStoreError("Retriever returned evidence excluded by the request.")
            if must_match:
                overlap = len(terms.intersection(_tokens(text))) / max(1, len(terms))
                phrase_match = any(_normalized(phrase) in text for phrase in phrases)
                entity_match = document_id in entity_documents
                if not phrase_match and not entity_match and overlap < profile.min_match_ratio:
                    raise RadarStoreError("Retriever returned a document unrelated to the research question.")
            return document

        docs_by_id: dict[str, dict[str, Any]] = {}
        for document_id in result.document_ids:
            docs_by_id[document_id] = document_allowed(document_id)

        for claim_id in result.claim_ids:
            claim = known_claims.get(claim_id)
            if claim is None:
                raise RadarStoreError("Retriever referenced a claim absent from the Radar ledger.")
            claim_text = _normalized(str(claim.get("statement", "")))
            claim_overlap = len(terms.intersection(_tokens(claim_text))) / max(1, len(terms))
            if not any(_normalized(phrase) in claim_text for phrase in phrases) and claim_overlap < profile.min_match_ratio:
                raise RadarStoreError("Retriever returned a claim unrelated to the research question.")
            if claim_id in known_evidence or f"radar://claim/{claim_id}" in known_evidence:
                raise RadarStoreError("Retriever returned a claim already known to the request.")
            support_ids = set()
            if claim.get("source_document_id"):
                support_ids.add(str(claim["source_document_id"]))
            support_ids.update(
                str(link["document_id"])
                for link in claim_sources
                if link["claim_id"] == claim_id and link.get("document_id")
            )
            if not support_ids:
                raise RadarStoreError("Retriever returned a claim without a linked source document.")
            for support_id in sorted(support_ids):
                docs_by_id.setdefault(support_id, document_allowed(support_id, must_match=False))

        return list(docs_by_id.values())

    @staticmethod
    def _budget_violation(budget: ResearchBudget, result: ResearchProviderResult) -> str | None:
        if result.requests_used > budget.max_requests:
            return "retriever exceeded max_requests; external result blocked"
        if result.bytes_read > budget.max_bytes:
            return "retriever exceeded max_bytes; external result blocked"
        if result.sources_considered > budget.max_sources:
            return "retriever exceeded max_sources; external result blocked"
        if result.elapsed_seconds > budget.max_duration_seconds:
            return "retriever exceeded max_duration_seconds; external result blocked"
        if result.retry_at is not None:
            try:
                retry_at = datetime.fromisoformat(result.retry_at.replace("Z", "+00:00"))
            except ValueError:
                return "retriever returned an invalid retry_at timestamp"
            if retry_at.tzinfo is None or retry_at.utcoffset() is None:
                return "retriever retry_at must include a timezone"
        return None

    def _save_packet(
        self,
        request: ResearchRequest,
        *,
        status: str,
        fetched_at: str,
        document_refs: Sequence[ArtifactReference] = (),
        claim_refs: Sequence[str] = (),
        source_lineage: Sequence[Mapping[str, Any]] = (),
        excerpts: Sequence[str] = (),
        new_material_since: str | None = None,
        missing: Sequence[str] = (),
        constraints: Sequence[str] = (),
        retry_at: str | None = None,
    ) -> tuple[str, ResearchPacket]:
        packet = ResearchPacket.create(
            request_id=request.request_id, status=status,
            document_refs=[item.to_dict() for item in document_refs], claim_refs=list(claim_refs),
            source_lineage=list(source_lineage), new_material_since=new_material_since,
            relevant_excerpts_short=list(excerpts), missing_evidence=list(missing),
            constraints=list(constraints), retry_at=retry_at, fetched_at=fetched_at,
        )
        rows = self.store.list_rows(
            "radar_research_packets", where_column="request_id", where_value=request.request_id,
        )
        version = max((int(row["version"]) for row in rows), default=0) + 1
        packet_id = self.store.save_research_packet(packet, version=version)
        return packet_id, packet

    @staticmethod
    def _result(
        request: ResearchRequest, packet: ResearchPacket, *, packet_id: str | None,
        index_hits: int, provider_called: bool, cache_hit: bool = False,
    ) -> ResearchExecutionResult:
        return ResearchExecutionResult(
            request_id=request.request_id, story_id=request.story_id,
            story_revision_id=request.story_revision_id, packet=packet, packet_id=packet_id,
            cache_hit=cache_hit, index_hit_count=index_hits, provider_called=provider_called,
        )
