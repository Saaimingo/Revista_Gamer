"""Incremental Radar ingestion over the existing connector and isolated store.

This layer is deterministic: it persists validators, metadata fingerprints and
observation events, but never invokes an agent or the existing task dispatcher.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit, urlunsplit

from .db import stable_hash
from .radar_connectors import (
    ConnectorPolicyError,
    FeedItem,
    FetchResult,
    HTMLPageMetadata,
    RadarConnectorService,
    SourceProfile,
)
from .radar_store import RadarStore, RadarStoreError, _url


@dataclass(frozen=True)
class IncrementalDocumentResult:
    document_id: str
    canonical_url: str
    event_id: str
    event_type: str
    is_new: bool
    material_change: bool
    requires_triage: bool
    duplicate_snapshot: bool
    republication_group_id: str | None = None


@dataclass(frozen=True)
class IncrementalFetchResult:
    fetch: FetchResult
    documents: tuple[IncrementalDocumentResult, ...]
    skipped_without_safe_url: int = 0
    fetch_event_id: str | None = None
    ingest_status: str = "not_attempted"
    documents_persisted: int = 0
    rejection_reason_counts: Mapping[str, int] = field(default_factory=dict)
    outcome_code: str | None = None

    @property
    def requires_triage(self) -> bool:
        return any(document.requires_triage for document in self.documents)


def canonicalize_content_url(value: str) -> str:
    """Normalize URL host/default path/fragment while preserving every query pair."""
    checked = _url(value, "canonical_url")
    if checked is None:
        raise RadarStoreError("canonical_url é obrigatório.")
    parts = urlsplit(checked)
    host = parts.hostname
    if not host:
        raise RadarStoreError("canonical_url precisa conter host.")
    host = host.casefold().rstrip(".")
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    try:
        port = parts.port
    except ValueError as error:
        raise RadarStoreError("canonical_url contém porta inválida.") from error
    if port not in (None, 443):
        raise RadarStoreError("canonical_url exige HTTPS na porta padrão 443.")
    netloc = host
    path = parts.path or "/"
    return urlunsplit(("https", netloc, path, parts.query, ""))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_digest(*parts: str) -> str:
    return stable_hash(json.dumps(parts, ensure_ascii=False, separators=(",", ":")))


def _normalized_text(text: str) -> str:
    return " ".join(text.split())


def _published_time(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    try:
        parsed_date = date.fromisoformat(text)
        return parsed_date.isoformat()
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def _as_feed_items(fetch: FetchResult) -> tuple[FeedItem, ...]:
    if fetch.feed_items:
        return fetch.feed_items
    metadata = fetch.metadata
    if isinstance(metadata, tuple) and all(isinstance(item, FeedItem) for item in metadata):
        return metadata
    if isinstance(metadata, HTMLPageMetadata) and metadata.title:
        return (FeedItem(metadata.title, metadata.canonical_url or fetch.final_url, None, None),)
    items: list[FeedItem] = []

    def visit(value: Any, depth: int = 0) -> None:
        if depth > 8 or len(items) >= 10_000:
            return
        if isinstance(value, Mapping):
            title = value.get("title") or value.get("name") or value.get("tag_name")
            url = value.get("html_url") or value.get("human_url") or value.get("link") or value.get("url")
            if isinstance(title, str) and title.strip() and isinstance(url, str):
                byline = value.get("author") or value.get("publisher")
                external_id = value.get("id") or value.get("slug") or value.get("tag_name")
                published_at = value.get("published_at") or value.get("updated_at") or value.get("release_date")
                technical_candidate = value.get("api_url") or value.get("url")
                technical_url = (
                    technical_candidate if isinstance(technical_candidate, str) and technical_candidate != url else None
                )
                items.append(FeedItem(
                    title.strip()[:1_000], url, str(external_id)[:500] if external_id is not None else None,
                    str(published_at)[:256] if published_at is not None else None,
                    str(byline)[:500] if byline is not None else None,
                    origin_url=(
                        value.get("origin_url") or value.get("source_url")
                        if isinstance(value.get("origin_url") or value.get("source_url"), str) else None
                    ),
                    technical_url=technical_url,
                ))
                return
            for nested in value.values():
                if isinstance(nested, (Mapping, list, tuple)):
                    visit(nested, depth + 1)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                visit(nested, depth + 1)

    visit(metadata)
    return tuple(items)


class IncrementalRadarService:
    """Fetch with a source-shared validator cache and append document history."""

    def __init__(self, *, store: RadarStore, connector: RadarConnectorService):
        self.store = store
        self.connector = connector

    def fetch(
        self, profile: SourceProfile, *, now: str | datetime | None = None,
        url: str | None = None, before_external_request: Callable[[], None] | None = None,
        mission_id: str | None = None, mission_request_limit: int | None = None,
    ) -> IncrementalFetchResult:
        target_url = canonicalize_content_url(url or profile.target_url())
        source = self.store.get_row("radar_sources", "source_id", profile.source_id)
        if source is None:
            raise RadarStoreError("Fonte precisa estar registrada no RadarStore antes da coleta.")
        if source["access_policy"] != "allowed" or source["rights_status"] == "blocked":
            raise RadarStoreError("Fonte sem política de acesso permitida no registro do RadarStore.")
        if profile.schema_version == "1.1":
            try:
                registered_metadata = json.loads(source["metadata_json"])
            except (TypeError, json.JSONDecodeError) as error:
                raise RadarStoreError("Metadados registrados da fonte não são JSON válido.") from error
            source_type_by_class = {
                "official": {"official", "public_api"},
                "independent": {"publisher", "creator", "public_api"},
                "community": {"community"},
                "replicator": {"publisher", "creator"},
            }
            if (
                not isinstance(registered_metadata, Mapping)
                or registered_metadata.get("source_class") != profile.source_class
                or registered_metadata.get("source_owner") != profile.source_owner
                or registered_metadata.get("profile_version") != profile.profile_version
                or source["display_name"] != profile.source_name
                or source["source_type"] not in source_type_by_class[profile.source_class or ""]
                or source["access_policy"] != profile.access_policy
                or source["rights_status"] != profile.rights_status
                or (source["language"] or "").casefold() != str(profile.language or "").casefold()
            ):
                raise RadarStoreError("SourceProfile diverge da política versionada registrada no RadarStore.")
        cached = self.store.get_fetch_cache(source_id=profile.source_id, request_url=target_url)

        profile_hash = profile.policy_sha256()

        def persist_transport_receipt(receipt: Mapping[str, Any]) -> str:
            return self.store.record_fetch_event(
                source_id=str(receipt["source_id"]), request_url=str(receipt["request_url"]),
                observed_at=str(receipt["observed_at"]), fetch_status=str(receipt["fetch_status"]),
                response_sha256=receipt.get("response_sha256"), request_id=str(receipt["request_id"]),
                http_status=receipt.get("http_status"), final_url=receipt.get("final_url"),
                content_type=receipt.get("content_type"), payload_bytes=int(receipt.get("payload_bytes", 0)),
                transport_status="response_received", parse_status="not_attempted",
                parser_schema_id=profile.parser_schema_id or "legacy_public_api_projection_v1",
                source_profile_hash=profile_hash, profile_version=profile.profile_version,
            )

        fetched = self.connector.fetch(
            profile, url=target_url,
            etag=cached["etag"] if cached else None,
            last_modified=cached["last_modified"] if cached else None,
            now=now,
            before_external_request=before_external_request,
            on_response_received=persist_transport_receipt,
            mission_id=mission_id, mission_request_limit=mission_request_limit,
        )
        fetch_event_id = fetched.fetch_event_id
        if fetch_event_id is None:
            fetch_event_id = self.store.record_fetch_event(
                source_id=profile.source_id, request_url=target_url, observed_at=fetched.fetched_at,
                fetch_status=fetched.status, response_sha256=fetched.payload_sha256,
                etag=fetched.etag, last_modified=fetched.last_modified, retry_at=fetched.retry_at,
                request_id=fetched.request_id, http_status=fetched.http_status, final_url=fetched.final_url,
                content_type=fetched.content_type, payload_bytes=fetched.payload_bytes,
                transport_status=fetched.transport_status, parse_status=fetched.parse_status,
                parser_schema_id=fetched.parser_schema_id, parse_reason_code=fetched.parse_reason_code,
                candidate_count=fetched.candidate_count, rejected_count=fetched.rejected_count,
                rejected_reason_counts=fetched.rejected_reason_counts,
                source_profile_hash=profile_hash, profile_version=profile.profile_version,
            )
        self.store.record_fetch_processing_event(
            fetch_event_id=fetch_event_id, request_id=fetched.request_id, stage="parse",
            status=fetched.parse_status, candidate_count=fetched.candidate_count,
            rejected_count=fetched.rejected_count, documents_persisted=0,
            reason_counts=fetched.rejected_reason_counts, outcome_code=fetched.parse_reason_code,
            parser_schema_id=fetched.parser_schema_id, recorded_at=fetched.fetched_at,
        )
        documents: list[IncrementalDocumentResult] = []
        skipped = 0
        rejection_reasons = dict(fetched.rejected_reason_counts)
        try:
            if fetched.status == "observed":
                for item in _as_feed_items(fetched):
                    if not item.url:
                        skipped += 1
                        rejection_reasons["candidate_missing_safe_human_url"] = rejection_reasons.get("candidate_missing_safe_human_url", 0) + 1
                        continue
                    try:
                        document_url = canonicalize_content_url(item.url)
                        origin_url = canonicalize_content_url(item.origin_url) if item.origin_url else None
                    except RadarStoreError:
                        skipped += 1
                        rejection_reasons["candidate_url_rejected_by_policy"] = rejection_reasons.get("candidate_url_rejected_by_policy", 0) + 1
                        continue
                    publisher = source["display_name"]
                    language = source["language"] or "und"
                    normalized_title = _normalized_text(item.title)
                    segment_hashes = tuple(item.body_segment_hashes)
                    normalized_body_hash = _sha("\u0000".join(segment_hashes)) if segment_hashes else ""
                    exact_document_hash = item.content_sha256 or _sha(f"{item.title}\u0000{item.body_sha256 or ''}")
                    normalized_document_hash = item.normalized_sha256 or _sha(f"{normalized_title}\u0000{normalized_body_hash}")
                    document_id = _stable_digest("document", profile.source_id, document_url)[:32]
                    snapshot_id = _stable_digest(
                        "snapshot", profile.source_id, document_url, fetched.fetched_at,
                        exact_document_hash, normalized_document_hash,
                    )
                    observation = self.store.observe_document_snapshot(
                        document_id=document_id, source_id=profile.source_id, canonical_url=document_url,
                        publisher=publisher, language=language, fetched_at=fetched.fetched_at,
                        content_sha256=exact_document_hash, normalized_sha256=normalized_document_hash,
                        title=item.title, source_snapshot_id=snapshot_id,
                        body_sha256=item.body_sha256, body_segment_hashes=segment_hashes,
                        body_char_count=item.body_char_count, origin_url=origin_url,
                        resolved_url=document_url, byline=item.byline, published_at=_published_time(item.published_at),
                        etag=fetched.etag, last_modified=fetched.last_modified,
                    )
                    group_id, existing_group_member = self._link_republication(
                        observation["document_id"], item, document_url, origin_url, fetched.fetched_at,
                    )
                    requires_triage = bool(observation["material_change"] and not existing_group_member)
                    documents.append(IncrementalDocumentResult(
                        document_id=observation["document_id"], canonical_url=document_url,
                        event_id=observation["event_id"], event_type=observation["event_type"],
                        is_new=observation["is_new"], material_change=observation["material_change"],
                        requires_triage=requires_triage, duplicate_snapshot=observation["duplicate_snapshot"],
                        republication_group_id=group_id,
                    ))
        except Exception as error:
            reason_code = getattr(error, "code", None)
            if not isinstance(reason_code, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", reason_code):
                reason_code = "ingest_error"
            self.store.record_fetch_processing_event(
                fetch_event_id=fetch_event_id, request_id=fetched.request_id, stage="ingest",
                status="error", candidate_count=fetched.candidate_count or len(_as_feed_items(fetched)),
                rejected_count=skipped + fetched.rejected_count, documents_persisted=len(documents),
                reason_counts={**rejection_reasons, reason_code: rejection_reasons.get(reason_code, 0) + 1},
                outcome_code=reason_code, parser_schema_id=fetched.parser_schema_id,
                recorded_at=fetched.fetched_at,
                artifact_refs=[{"document_id": item.document_id, "event_id": item.event_id} for item in documents],
            )
            raise

        if fetched.transport_status in {"response_received", "uncertain"}:
            self.store.save_fetch_cache(
                source_id=profile.source_id, request_url=target_url, fetched_at=fetched.fetched_at,
                fetch_status=fetched.status,
                etag=fetched.etag or (cached["etag"] if cached and fetched.status != "observed" else None),
                last_modified=fetched.last_modified or (cached["last_modified"] if cached and fetched.status != "observed" else None),
                response_sha256=fetched.payload_sha256 or (cached["response_sha256"] if cached else None),
            )
        if fetched.status != "observed":
            ingest_status = "not_attempted"
            outcome_code = fetched.error_code
        elif documents and (skipped or fetched.rejected_count):
            ingest_status, outcome_code = "partial", "candidate_rejected"
        elif documents:
            ingest_status, outcome_code = "ingested", None
        elif fetched.candidate_count == 0 and not fetched.feed_items and not _as_feed_items(fetched):
            ingest_status, outcome_code = "no_new_story", "no_candidate_records"
        else:
            ingest_status, outcome_code = "no_new_story", "no_safe_document_candidate"
        self.store.record_fetch_processing_event(
            fetch_event_id=fetch_event_id, request_id=fetched.request_id, stage="ingest",
            status=ingest_status, candidate_count=fetched.candidate_count or len(_as_feed_items(fetched)),
            rejected_count=skipped + fetched.rejected_count, documents_persisted=len(documents),
            reason_counts=rejection_reasons, outcome_code=outcome_code,
            parser_schema_id=fetched.parser_schema_id, recorded_at=fetched.fetched_at,
            artifact_refs=[
                {"document_id": document.document_id, "event_id": document.event_id}
                for document in documents
            ],
        )
        return IncrementalFetchResult(
            fetched, tuple(documents), skipped, fetch_event_id=fetch_event_id,
            ingest_status=ingest_status, documents_persisted=len(documents),
            rejection_reason_counts=rejection_reasons, outcome_code=outcome_code,
        )

    def _link_republication(
        self, document_id: str, item: FeedItem, document_url: str,
        origin_url: str | None, linked_at: str,
    ) -> tuple[str | None, bool]:
        basis: str | None = None
        relation: str | None = None
        evidence: dict[str, Any] = {}
        identity = ""
        matching_documents: list[dict[str, Any]] = []
        if origin_url and origin_url != document_url:
            basis = "canonical_origin"
            relation = "origin"
            identity = _sha(origin_url)
            evidence = {"origin_url": origin_url}
        elif item.body_sha256 and item.body_char_count >= 80 and item.byline:
            normalized_byline = _normalized_text(item.byline).casefold()
            matching_documents = [
                document for document in self.store.list_rows(
                    "radar_documents", where_column="body_sha256", where_value=item.body_sha256,
                )
                if document["document_id"] != document_id
                and _normalized_text(document["title"]).casefold() == _normalized_text(item.title).casefold()
                and document["byline"] is not None
                and _normalized_text(document["byline"]).casefold() == normalized_byline
                and int(document["body_char_count"]) >= 80
            ]
            if not matching_documents:
                return None, False
            basis = "identical_body_same_byline"
            relation = "identical_copy"
            identity = _sha("\u0000".join((_normalized_text(item.title), item.body_sha256, normalized_byline)))
            evidence = {
                "body_sha256": item.body_sha256,
                "byline_sha256": _sha(normalized_byline),
                "title_sha256": _sha(_normalized_text(item.title)),
            }
        if basis is None or relation is None:
            return None, False
        group_id = _stable_digest("republication", basis, identity)[:32]
        before = self.store.list_republication_members(group_id=group_id)
        has_other_member = bool(matching_documents) or any(
            member["document_id"] != document_id for member in before
        )
        self.store.link_republication_member(
            group_id=group_id, basis=basis, identity_sha256=identity, document_id=document_id,
            relation=relation, evidence=evidence, linked_at=linked_at,
        )
        if basis == "identical_body_same_byline":
            for candidate in matching_documents:
                self.store.link_republication_member(
                    group_id=group_id, basis=basis, identity_sha256=identity,
                    document_id=candidate["document_id"], relation=relation,
                    evidence=evidence, linked_at=linked_at,
                )
        return group_id, has_other_member
