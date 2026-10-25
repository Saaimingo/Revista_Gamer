"""Isolated SQLite source, observation, claim, research, and candidate ledger.

This store requires an explicit path and refuses the legacy application runtime
database. Radar records live in a separately versioned, radar_-namespaced file;
agent tasks remain in the existing AgentQueue/TaskDispatcher ledger.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from collections.abc import Iterable, Mapping
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from .agent_contracts import (
    SUPPORTED_RESEARCH_REQUEST_SCHEMA_VERSIONS,
    ResearchPacket,
    ResearchRequest,
)
from .db import json_dumps, normalize_text, stable_hash
from .orchestration import _assert_no_credentials


RADAR_SCHEMA_VERSION = 7
_HASH_RE = re.compile(r"^[a-f0-9]{64}$")
_LANGUAGE_TAG_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_SENSITIVE_URL_KEYS = {
    "access_token", "refresh_token", "id_token", "token", "oauth_token", "api_key", "apikey", "key",
    "access_key", "client_secret", "secret", "signature", "sig", "auth", "credential", "credentials",
    "x_amz_credential", "x_amz_signature", "x_amz_security_token", "password", "cookie", "authorization",
    "code", "code_verifier", "authorization_code",
}
_SOURCE_TYPES = {"official", "publisher", "creator", "community", "public_api", "unknown"}
_ACCESS_POLICIES = {"unreviewed", "allowed", "blocked", "suspended"}
_RIGHTS_STATUSES = {"unknown", "pending", "authorized", "blocked"}
_RETENTION_POLICIES = {"metadata_only", "short_excerpt"}
_FETCH_STATUSES = {"observed", "not_modified", "removed", "forbidden", "rate_limited", "error"}
_EPISTEMIC_STATUSES = {
    "official_statement", "named_person_statement", "independent_measurement", "community_report",
    "attributed_rumor", "unverified_or_disputed", "editorial_interpretation",
}
_CLAIM_EVENT_TYPES = {
    "evidence_added", "origin_traced", "republication_linked", "content_confirmed",
    "content_partially_confirmed", "content_contradicted", "content_withdrawn", "correction_recorded",
    "dispute_recorded", "superseded",
}
_CONTENT_STATUSES = {"confirmed", "partially_confirmed", "contradicted", "withdrawn"}
_QUEUE_LANES = {"principal", "reserva", "monitoramento", "descartada"}
_CANDIDATE_EVALUATION_STATES = {"eligible", "blocked", "needs_evaluation"}
_CANDIDATE_EVENT_KINDS = {
    "candidate_created", "candidate_updated", "lane_changed", "evaluation_reactivated",
    "evaluation_resolved", "manual_swap",
}

RUNTIME_DB_PATH = (Path(__file__).parent / "runtime" / "motor.sqlite3").resolve()


class RadarStoreError(ValueError):
    """Raised when Radar data or schema state fails its local contract."""


def _text(value: Any, name: str, *, maximum: int = 4_000, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise RadarStoreError(f"{name} precisa ser texto não vazio (máximo {maximum}).")
    value = value.strip()
    _assert_no_credentials(value, name)
    return value


def _timestamp(value: Any, name: str, *, optional: bool = False) -> str | None:
    text = _text(value, name, maximum=64, optional=optional)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise RadarStoreError(f"{name} precisa ser ISO-8601.") from error
    if parsed.tzinfo is None:
        raise RadarStoreError(f"{name} precisa declarar fuso horário.")
    return text


def _date_or_timestamp(value: Any, name: str, *, optional: bool = False) -> str | None:
    text = _text(value, name, maximum=64, optional=optional)
    if text is None:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            date.fromisoformat(text)
        except ValueError as error:
            raise RadarStoreError(f"{name} precisa ser data ISO-8601 válida.") from error
        return text
    return _timestamp(text, name)


def _language_tag(value: Any, name: str) -> str:
    text = _text(value, name, maximum=32)
    if text is None or not _LANGUAGE_TAG_RE.fullmatch(text):
        raise RadarStoreError(f"{name} precisa ser uma etiqueta de idioma compatível com BCP 47 simplificado.")
    subtags = text.split("-")
    canonical = [subtags[0].lower()]
    for subtag in subtags[1:]:
        if len(subtag) == 4 and subtag.isalpha():
            canonical.append(subtag.title())
        elif (len(subtag) == 2 and subtag.isalpha()) or (len(subtag) == 3 and subtag.isdigit()):
            canonical.append(subtag.upper())
        else:
            canonical.append(subtag.lower())
    return "-".join(canonical)


def _contains_contact_data(value: str) -> bool:
    if re.search(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", value):
        return True
    for match in re.finditer(r"(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)", value):
        if sum(character.isdigit() for character in match.group(0)) >= 9:
            return True
    return False


def _temporal_instant(value: str | None) -> datetime | None:
    if value is None:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return datetime.fromisoformat(f"{value}T00:00:00+00:00")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RadarStoreError("Intervalo de cargo exige fuso horário em timestamps.")
    return parsed.astimezone(timezone.utc)


def _require_public_document(connection: sqlite3.Connection, document_id: str) -> sqlite3.Row:
    row = connection.execute(
        """SELECT d.document_id, d.source_id AS document_source_id, d.language, d.access_policy,
                  s.access_policy AS source_access_policy, s.source_type
           FROM radar_documents d JOIN radar_sources s ON s.source_id=d.source_id
           WHERE d.document_id=?""",
        (document_id,),
    ).fetchone()
    if row is None or row["access_policy"] != "allowed" or row["source_access_policy"] != "allowed":
        raise RadarStoreError("Proveniência exige documento e fonte com acesso público permitido.")
    return row


def _require_public_source(connection: sqlite3.Connection, source_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT source_id, source_type, access_policy FROM radar_sources WHERE source_id=?",
        (source_id,),
    ).fetchone()
    if row is None or row["access_policy"] != "allowed":
        raise RadarStoreError("Proveniência de alegação exige uma fonte pública permitida.")
    return row


def _sha256(value: Any, name: str, *, optional: bool = False) -> str | None:
    text = _text(value, name, maximum=64, optional=optional)
    if text is None:
        return None
    if not _HASH_RE.fullmatch(text):
        raise RadarStoreError(f"{name} precisa ser SHA-256 hexadecimal minúsculo.")
    return text


def _url(value: Any, name: str, *, optional: bool = False) -> str | None:
    text = _text(value, name, maximum=4_000, optional=optional)
    if text is None:
        return None
    parts = urlsplit(text)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise RadarStoreError(f"{name} precisa ser URL HTTPS sem credenciais.")
    query_keys = {key.casefold().replace("-", "_") for key, _ in parse_qsl(parts.query, keep_blank_values=True)}
    if query_keys & _SENSITIVE_URL_KEYS:
        raise RadarStoreError(f"{name} não pode conter parâmetros de credencial.")
    return text


def _json(value: Any, name: str, *, max_bytes: int = 64_000) -> str:
    _assert_no_credentials(value, name)
    try:
        encoded = json_dumps(value)
    except (TypeError, ValueError) as error:
        raise RadarStoreError(f"{name} não é JSON válido.") from error
    if len(encoded.encode("utf-8")) > max_bytes:
        raise RadarStoreError(f"{name} excede o limite de {max_bytes} bytes.")
    return encoded


def _validate_resolved_path(path: Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if resolved == RUNTIME_DB_PATH:
        raise RadarStoreError("RadarStore não pode abrir o banco runtime do Motor Editorial.")
    return resolved


_SCHEMA_V1_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS radar_sources (
        source_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        canonical_url TEXT NOT NULL UNIQUE,
        domain TEXT NOT NULL,
        source_type TEXT NOT NULL CHECK (source_type IN ('official','publisher','creator','community','public_api','unknown')),
        access_policy TEXT NOT NULL DEFAULT 'unreviewed' CHECK (access_policy IN ('unreviewed','allowed','blocked','suspended')),
        rights_status TEXT NOT NULL DEFAULT 'unknown' CHECK (rights_status IN ('unknown','pending','authorized','blocked')),
        language TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_sources_domain ON radar_sources(domain, access_policy)",
    """CREATE TABLE IF NOT EXISTS radar_documents (
        document_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL REFERENCES radar_sources(source_id) ON DELETE RESTRICT,
        canonical_url TEXT NOT NULL,
        resolved_url TEXT,
        publisher TEXT NOT NULL,
        byline TEXT,
        language TEXT NOT NULL,
        published_at TEXT,
        modified_at TEXT,
        fetched_at TEXT NOT NULL,
        etag TEXT,
        last_modified TEXT,
        content_sha256 TEXT NOT NULL CHECK (length(content_sha256)=64),
        normalized_sha256 TEXT NOT NULL CHECK (length(normalized_sha256)=64),
        title TEXT NOT NULL,
        summary_snippet TEXT NOT NULL DEFAULT '',
        outbound_primary_refs_json TEXT NOT NULL DEFAULT '[]',
        access_policy TEXT NOT NULL DEFAULT 'unreviewed' CHECK (access_policy IN ('unreviewed','allowed','blocked','suspended')),
        rights_status TEXT NOT NULL DEFAULT 'unknown' CHECK (rights_status IN ('unknown','pending','authorized','blocked')),
        content_retention TEXT NOT NULL DEFAULT 'metadata_only' CHECK (content_retention IN ('metadata_only','short_excerpt')),
        fetch_status TEXT NOT NULL CHECK (fetch_status IN ('observed','not_modified','removed','forbidden','rate_limited','error')),
        retry_after TEXT,
        UNIQUE(source_id, canonical_url),
        UNIQUE(document_id, source_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_documents_source_fetched ON radar_documents(source_id, fetched_at)",
    "CREATE INDEX IF NOT EXISTS idx_radar_documents_content_hash ON radar_documents(content_sha256)",
    """CREATE TABLE IF NOT EXISTS radar_observation_events (
        event_id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        source_id TEXT NOT NULL,
        event_type TEXT NOT NULL CHECK (event_type IN ('first_seen','repeated','title_changed','body_changed','corrected','removed','url_changed','origin_linked','fetch_error')),
        observed_at TEXT NOT NULL,
        previous_content_sha256 TEXT,
        current_content_sha256 TEXT,
        source_snapshot_id TEXT UNIQUE,
        diff_json TEXT NOT NULL DEFAULT '{}',
        FOREIGN KEY(document_id, source_id) REFERENCES radar_documents(document_id, source_id) ON DELETE RESTRICT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_observations_document_time ON radar_observation_events(document_id, observed_at)",
    """CREATE TABLE IF NOT EXISTS radar_entities (
        entity_id TEXT PRIMARY KEY,
        entity_kind TEXT NOT NULL CHECK (entity_kind IN ('person','organization','game','hardware','project','creator','mod','company','other')),
        canonical_name TEXT NOT NULL,
        normalized_name TEXT NOT NULL,
        language TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(entity_kind, normalized_name, language)
    )""",
    """CREATE TABLE IF NOT EXISTS radar_entity_aliases (
        alias_id TEXT PRIMARY KEY,
        entity_id TEXT NOT NULL REFERENCES radar_entities(entity_id) ON DELETE CASCADE,
        alias TEXT NOT NULL,
        normalized_alias TEXT NOT NULL,
        language TEXT NOT NULL,
        source_document_id TEXT REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
        created_at TEXT NOT NULL,
        UNIQUE(entity_id, normalized_alias, language)
    )""",
    """CREATE TABLE IF NOT EXISTS radar_topics (
        topic_id TEXT PRIMARY KEY,
        canonical_key TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','merged','closed')),
        merged_into_topic_id TEXT REFERENCES radar_topics(topic_id) ON DELETE RESTRICT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS radar_topic_entities (
        topic_id TEXT NOT NULL REFERENCES radar_topics(topic_id) ON DELETE CASCADE,
        entity_id TEXT NOT NULL REFERENCES radar_entities(entity_id) ON DELETE RESTRICT,
        relation_type TEXT NOT NULL,
        source_document_id TEXT REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
        PRIMARY KEY(topic_id, entity_id, relation_type)
    )""",
    """CREATE TABLE IF NOT EXISTS radar_document_entities (
        document_id TEXT NOT NULL REFERENCES radar_documents(document_id) ON DELETE CASCADE,
        entity_id TEXT NOT NULL REFERENCES radar_entities(entity_id) ON DELETE RESTRICT,
        relation_type TEXT NOT NULL,
        PRIMARY KEY(document_id, entity_id, relation_type)
    )""",
    """CREATE TABLE IF NOT EXISTS radar_document_topics (
        document_id TEXT NOT NULL REFERENCES radar_documents(document_id) ON DELETE CASCADE,
        topic_id TEXT NOT NULL REFERENCES radar_topics(topic_id) ON DELETE RESTRICT,
        relation_type TEXT NOT NULL,
        PRIMARY KEY(document_id, topic_id, relation_type)
    )""",
    """CREATE TABLE IF NOT EXISTS radar_claims (
        claim_id TEXT PRIMARY KEY,
        topic_id TEXT NOT NULL REFERENCES radar_topics(topic_id) ON DELETE RESTRICT,
        statement TEXT NOT NULL,
        epistemic_status TEXT NOT NULL CHECK (epistemic_status IN ('official_statement','named_person_statement','independent_measurement','community_report','attributed_rumor','unverified_or_disputed','editorial_interpretation')),
        asserted_by_entity_id TEXT REFERENCES radar_entities(entity_id) ON DELETE RESTRICT,
        reported_by_source_id TEXT NOT NULL REFERENCES radar_sources(source_id) ON DELETE RESTRICT,
        earliest_traceable_source_id TEXT REFERENCES radar_sources(source_id) ON DELETE RESTRICT,
        source_document_id TEXT REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
        first_seen_at TEXT NOT NULL,
        statement_date TEXT,
        published_at TEXT,
        url TEXT,
        confidence_in_attribution REAL NOT NULL CHECK (confidence_in_attribution >= 0 AND confidence_in_attribution <= 1),
        confidence_in_content REAL CHECK (confidence_in_content IS NULL OR (confidence_in_content >= 0 AND confidence_in_content <= 1)),
        evidence_refs_json TEXT NOT NULL DEFAULT '[]',
        republished_by_json TEXT NOT NULL DEFAULT '[]',
        independent_origin_groups_json TEXT NOT NULL DEFAULT '[]',
        disputed_by_json TEXT NOT NULL DEFAULT '[]',
        superseded_by TEXT REFERENCES radar_claims(claim_id) ON DELETE RESTRICT,
        new_information_since TEXT,
        editorial_review_status TEXT NOT NULL DEFAULT 'unreviewed',
        version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_claims_topic_status ON radar_claims(topic_id, epistemic_status)",
    """CREATE TABLE IF NOT EXISTS radar_claim_sources (
        claim_id TEXT NOT NULL REFERENCES radar_claims(claim_id) ON DELETE RESTRICT,
        source_id TEXT NOT NULL REFERENCES radar_sources(source_id) ON DELETE RESTRICT,
        document_id TEXT REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
        relation_type TEXT NOT NULL CHECK (relation_type IN ('origin','republished','independent','supports','disputes','statement')),
        origin_group_id TEXT NOT NULL,
        linked_at TEXT NOT NULL,
        PRIMARY KEY(claim_id, source_id, relation_type)
    )""",
    """CREATE TABLE IF NOT EXISTS radar_claim_events (
        event_id TEXT PRIMARY KEY,
        claim_id TEXT NOT NULL REFERENCES radar_claims(claim_id) ON DELETE RESTRICT,
        event_type TEXT NOT NULL CHECK (event_type IN ('evidence_added','origin_traced','republication_linked','content_confirmed','content_partially_confirmed','content_contradicted','content_withdrawn','correction_recorded','dispute_recorded','superseded')),
        content_status TEXT CHECK (content_status IS NULL OR content_status IN ('confirmed','partially_confirmed','contradicted','withdrawn')),
        event_source_id TEXT REFERENCES radar_sources(source_id) ON DELETE RESTRICT,
        event_document_id TEXT REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
        occurred_at TEXT NOT NULL,
        reason TEXT NOT NULL,
        evidence_refs_json TEXT NOT NULL DEFAULT '[]',
        details_json TEXT NOT NULL DEFAULT '{}'
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_claim_events_claim_time ON radar_claim_events(claim_id, occurred_at)",
    """CREATE TRIGGER IF NOT EXISTS radar_observation_events_no_update
        BEFORE UPDATE ON radar_observation_events BEGIN SELECT RAISE(ABORT, 'observation events are append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_observation_events_no_delete
        BEFORE DELETE ON radar_observation_events BEGIN SELECT RAISE(ABORT, 'observation events are append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_claim_events_no_update
        BEFORE UPDATE ON radar_claim_events BEGIN SELECT RAISE(ABORT, 'claim events are append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_claim_events_no_delete
        BEFORE DELETE ON radar_claim_events BEGIN SELECT RAISE(ABORT, 'claim events are append-only'); END""",
    """CREATE TABLE IF NOT EXISTS radar_research_requests (
        request_id TEXT PRIMARY KEY,
        idempotency_key TEXT NOT NULL UNIQUE,
        parent_task_id TEXT NOT NULL,
        story_id TEXT NOT NULL,
        requester_role_id TEXT NOT NULL,
        requester_persona_id TEXT,
        profile_id TEXT NOT NULL,
        profile_version TEXT NOT NULL,
        request_json TEXT NOT NULL,
        content_hash TEXT NOT NULL CHECK (length(content_hash)=64),
        state TEXT NOT NULL DEFAULT 'queued' CHECK (state IN ('queued','running','completed','blocked','cancelled','uncertain')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS radar_research_packets (
        packet_id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL REFERENCES radar_research_requests(request_id) ON DELETE RESTRICT,
        version INTEGER NOT NULL CHECK (version >= 1),
        status TEXT NOT NULL CHECK (status IN ('found','partial','not_found','blocked','rate_limited')),
        packet_json TEXT NOT NULL,
        content_hash TEXT NOT NULL CHECK (length(content_hash)=64),
        fetched_at TEXT NOT NULL,
        retry_at TEXT,
        UNIQUE(request_id, version)
    )""",
    """CREATE TABLE IF NOT EXISTS radar_candidates (
        candidate_id TEXT PRIMARY KEY,
        topic_id TEXT NOT NULL REFERENCES radar_topics(topic_id) ON DELETE RESTRICT,
        story_id TEXT,
        edition_id TEXT,
        queue_lane TEXT NOT NULL CHECK (queue_lane IN ('principal','reserva','monitoramento','descartada')),
        reason TEXT NOT NULL,
        depth_available TEXT NOT NULL,
        evidence_risk TEXT NOT NULL,
        last_material_change TEXT,
        priority REAL NOT NULL DEFAULT 0,
        source_packet_id TEXT REFERENCES radar_research_packets(packet_id) ON DELETE RESTRICT,
        human_override_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(topic_id, edition_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_candidates_lane_priority ON radar_candidates(edition_id, queue_lane, priority DESC)",
    """CREATE TABLE IF NOT EXISTS radar_candidate_events (
        event_id TEXT PRIMARY KEY,
        candidate_id TEXT NOT NULL REFERENCES radar_candidates(candidate_id) ON DELETE RESTRICT,
        from_lane TEXT CHECK (from_lane IS NULL OR from_lane IN ('principal','reserva','monitoramento','descartada')),
        to_lane TEXT NOT NULL CHECK (to_lane IN ('principal','reserva','monitoramento','descartada')),
        actor TEXT NOT NULL,
        reason TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        evidence_json TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TRIGGER IF NOT EXISTS radar_candidate_events_no_update
        BEFORE UPDATE ON radar_candidate_events BEGIN SELECT RAISE(ABORT, 'candidate events are append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_candidate_events_no_delete
        BEFORE DELETE ON radar_candidate_events BEGIN SELECT RAISE(ABORT, 'candidate events are append-only'); END""",
)

_SCHEMA_V2_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_radar_documents_body_sha256 ON radar_documents(body_sha256)",
    """CREATE TABLE IF NOT EXISTS radar_fetch_events (
        fetch_event_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL REFERENCES radar_sources(source_id) ON DELETE RESTRICT,
        request_url TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        fetch_status TEXT NOT NULL CHECK (fetch_status IN ('observed','not_modified','removed','forbidden','rate_limited','error','blocked')),
        response_sha256 TEXT CHECK (response_sha256 IS NULL OR length(response_sha256)=64),
        etag TEXT,
        last_modified TEXT,
        retry_at TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_fetch_events_source_time ON radar_fetch_events(source_id, observed_at)",
    """CREATE TRIGGER IF NOT EXISTS radar_fetch_events_no_update
        BEFORE UPDATE ON radar_fetch_events BEGIN SELECT RAISE(ABORT, 'fetch events are append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_fetch_events_no_delete
        BEFORE DELETE ON radar_fetch_events BEGIN SELECT RAISE(ABORT, 'fetch events are append-only'); END""",
    """CREATE TABLE IF NOT EXISTS radar_fetch_cache (
        source_id TEXT NOT NULL REFERENCES radar_sources(source_id) ON DELETE RESTRICT,
        request_url TEXT NOT NULL,
        etag TEXT,
        last_modified TEXT,
        last_fetched_at TEXT NOT NULL,
        response_sha256 TEXT CHECK (response_sha256 IS NULL OR length(response_sha256)=64),
        fetch_status TEXT NOT NULL CHECK (fetch_status IN ('observed','not_modified','removed','forbidden','rate_limited','error','blocked')),
        PRIMARY KEY(source_id, request_url)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_fetch_cache_fetched ON radar_fetch_cache(last_fetched_at)",
    """CREATE TABLE IF NOT EXISTS radar_republication_groups (
        group_id TEXT PRIMARY KEY,
        basis TEXT NOT NULL CHECK (basis IN ('canonical_origin','identical_body_same_byline')),
        identity_sha256 TEXT NOT NULL CHECK (length(identity_sha256)=64),
        evidence_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(basis, identity_sha256)
    )""",
    """CREATE TABLE IF NOT EXISTS radar_republication_members (
        group_id TEXT NOT NULL REFERENCES radar_republication_groups(group_id) ON DELETE RESTRICT,
        document_id TEXT NOT NULL REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
        relation TEXT NOT NULL CHECK (relation IN ('origin','identical_copy')),
        evidence_json TEXT NOT NULL,
        linked_at TEXT NOT NULL,
        PRIMARY KEY(group_id, document_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_republication_members_document ON radar_republication_members(document_id)",
    """CREATE TRIGGER IF NOT EXISTS radar_republication_members_no_update
        BEFORE UPDATE ON radar_republication_members BEGIN SELECT RAISE(ABORT, 'republication links are append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_republication_members_no_delete
        BEFORE DELETE ON radar_republication_members BEGIN SELECT RAISE(ABORT, 'republication links are append-only'); END""",
)

_SCHEMA_V3_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS radar_entity_roles (
        role_id TEXT PRIMARY KEY,
        entity_id TEXT NOT NULL REFERENCES radar_entities(entity_id) ON DELETE RESTRICT,
        role_kind TEXT NOT NULL CHECK (role_kind IN ('producer','director','developer','designer','writer','artist','composer','actor','voice_actor','executive','other')),
        role_title TEXT NOT NULL,
        organization_entity_id TEXT REFERENCES radar_entities(entity_id) ON DELETE RESTRICT,
        project_entity_id TEXT REFERENCES radar_entities(entity_id) ON DELETE RESTRICT,
        valid_from TEXT,
        valid_to TEXT,
        source_document_id TEXT NOT NULL REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
        evidence_context TEXT NOT NULL CHECK (evidence_context IN ('interview_quote','interview_byline','company_press_release','official_bio','credits','other_public_source')),
        recorded_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_entity_roles_person_time ON radar_entity_roles(entity_id, valid_from, valid_to)",
    "CREATE INDEX IF NOT EXISTS idx_radar_entity_roles_project ON radar_entity_roles(project_entity_id, role_kind)",
    """CREATE TRIGGER IF NOT EXISTS radar_entity_roles_no_update
        BEFORE UPDATE ON radar_entity_roles BEGIN SELECT RAISE(ABORT, 'role evidence is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_entity_roles_no_delete
        BEFORE DELETE ON radar_entity_roles BEGIN SELECT RAISE(ABORT, 'role evidence is append-only'); END""",
    """CREATE TABLE IF NOT EXISTS radar_interviews (
        interview_id TEXT PRIMARY KEY,
        subject_entity_id TEXT NOT NULL REFERENCES radar_entities(entity_id) ON DELETE RESTRICT,
        original_document_id TEXT NOT NULL REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
        original_language TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        UNIQUE(subject_entity_id, original_document_id)
    )""",
    """CREATE TABLE IF NOT EXISTS radar_interview_variants (
        interview_id TEXT NOT NULL REFERENCES radar_interviews(interview_id) ON DELETE RESTRICT,
        document_id TEXT NOT NULL REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
        relation_type TEXT NOT NULL CHECK (relation_type IN ('translation','transcript','republication')),
        based_on_document_id TEXT NOT NULL REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
        language TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        PRIMARY KEY(interview_id, document_id),
        CHECK (document_id <> based_on_document_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_interview_variants_based_on ON radar_interview_variants(based_on_document_id)",
    """CREATE TRIGGER IF NOT EXISTS radar_interviews_no_update
        BEFORE UPDATE ON radar_interviews BEGIN SELECT RAISE(ABORT, 'interview identity is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_interviews_no_delete
        BEFORE DELETE ON radar_interviews BEGIN SELECT RAISE(ABORT, 'interview identity is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_interview_variants_no_update
        BEFORE UPDATE ON radar_interview_variants BEGIN SELECT RAISE(ABORT, 'interview variants are append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_interview_variants_no_delete
        BEFORE DELETE ON radar_interview_variants BEGIN SELECT RAISE(ABORT, 'interview variants are append-only'); END""",
)

_SCHEMA_V4_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_radar_claim_sources_lineage ON radar_claim_sources(claim_id, origin_group_id, based_on_source_id)",
    """CREATE TRIGGER IF NOT EXISTS radar_claims_no_update
        BEFORE UPDATE ON radar_claims BEGIN SELECT RAISE(ABORT, 'claims are append-only; record a claim event'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_claims_no_delete
        BEFORE DELETE ON radar_claims BEGIN SELECT RAISE(ABORT, 'claims are append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_claim_sources_no_update
        BEFORE UPDATE ON radar_claim_sources BEGIN SELECT RAISE(ABORT, 'claim source links are append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_claim_sources_no_delete
        BEFORE DELETE ON radar_claim_sources BEGIN SELECT RAISE(ABORT, 'claim source links are append-only'); END""",
)

_SCHEMA_V5_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS radar_domain_quota_events (
        event_id TEXT PRIMARY KEY,
        request_key TEXT NOT NULL UNIQUE,
        domain TEXT NOT NULL,
        quota_date TEXT NOT NULL,
        timezone_name TEXT NOT NULL,
        quota_limit INTEGER NOT NULL CHECK (quota_limit >= 1),
        reserved_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_radar_domain_quota_period ON radar_domain_quota_events(domain, timezone_name, quota_date)",
    """CREATE TRIGGER IF NOT EXISTS radar_domain_quota_events_no_update
        BEFORE UPDATE ON radar_domain_quota_events BEGIN SELECT RAISE(ABORT, 'quota reservations are append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS radar_domain_quota_events_no_delete
        BEFORE DELETE ON radar_domain_quota_events BEGIN SELECT RAISE(ABORT, 'quota reservations are append-only'); END""",
)


class RadarStore:
    """Explicit-path, independently versioned SQLite store for Radar data."""

    def __init__(self, db_path: Path):
        self.db_path = _validate_resolved_path(Path(db_path))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def initialize(self) -> None:
        with closing(self.connect()) as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > RADAR_SCHEMA_VERSION:
                raise RadarStoreError(
                    f"Radar schema v{version} é posterior ao suportado (v{RADAR_SCHEMA_VERSION})."
                )
            if version == 0:
                self._migrate_v0_to_v1(connection)
                self._migrate_v1_to_v2(connection)
                self._migrate_v2_to_v3(connection)
                self._migrate_v3_to_v4(connection)
                version = 4
            elif version == 1:
                self._migrate_v1_to_v2(connection)
                self._migrate_v2_to_v3(connection)
                self._migrate_v3_to_v4(connection)
                version = 4
            elif version == 2:
                self._migrate_v2_to_v3(connection)
                self._migrate_v3_to_v4(connection)
                version = 4
            elif version == 3:
                self._migrate_v3_to_v4(connection)
                version = 4
            if version == 4:
                self._migrate_v4_to_v5(connection)
                version = 5
            if version == 5:
                self._migrate_v5_to_v6(connection)
                version = 6
            if version == 6:
                self._migrate_v6_to_v7(connection)
                version = 7
            if version == RADAR_SCHEMA_VERSION:
                check = connection.execute("PRAGMA quick_check").fetchone()[0]
                if check != "ok":
                    raise RadarStoreError("Verificação SQLite do Radar falhou.")
                tables = {
                    row["name"] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                required = {
                    "radar_sources", "radar_documents", "radar_observation_events", "radar_entities",
                    "radar_entity_aliases", "radar_topics", "radar_topic_entities", "radar_document_entities",
                    "radar_document_topics", "radar_claims", "radar_claim_sources", "radar_claim_events",
                    "radar_research_requests", "radar_research_packets", "radar_candidates", "radar_candidate_events",
                    "radar_fetch_events", "radar_fetch_cache", "radar_republication_groups", "radar_republication_members",
                    "radar_entity_roles", "radar_interviews", "radar_interview_variants",
                    "radar_domain_quota_events",
                }
                if not required.issubset(tables):
                    raise RadarStoreError("Banco marcado como Radar v7 sem as tabelas obrigatórias.")
                unrelated = {name for name in tables if not name.startswith(("radar_", "sqlite_"))}
                if unrelated:
                    raise RadarStoreError("Banco Radar v4 contém tabelas fora do namespace reservado.")
                claim_source_columns = {
                    row["name"] for row in connection.execute("PRAGMA table_info(radar_claim_sources)").fetchall()
                }
                if "based_on_source_id" not in claim_source_columns:
                    raise RadarStoreError("Banco marcado como Radar v7 sem a coluna de linhagem de alegações.")
                request_columns = {
                    row["name"] for row in connection.execute("PRAGMA table_info(radar_research_requests)").fetchall()
                }
                if "story_revision_id" not in request_columns:
                    raise RadarStoreError("Banco marcado como Radar v7 sem vínculo de revisão da pauta.")
                candidate_columns = {
                    row["name"] for row in connection.execute("PRAGMA table_info(radar_candidates)").fetchall()
                }
                candidate_event_columns = {
                    row["name"] for row in connection.execute("PRAGMA table_info(radar_candidate_events)").fetchall()
                }
                if not {"evaluation_state", "membership_locked"}.issubset(candidate_columns) or not {
                    "event_kind", "from_evaluation_state", "to_evaluation_state",
                }.issubset(candidate_event_columns):
                    raise RadarStoreError("Banco marcado como Radar v7 sem estados/eventos da carteira.")
                portfolio_triggers = {
                    row["name"] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='trigger'"
                    ).fetchall()
                }
                if not {
                    "radar_candidates_reactivate_on_observation",
                    "radar_candidates_reactivate_on_claim_event",
                }.issubset(portfolio_triggers):
                    raise RadarStoreError("Banco Radar v7 sem gatilhos de reavaliação de carteira.")
                return
            raise RadarStoreError(f"Versão de schema Radar não suportada: {version}.")

    @staticmethod
    def _migrate_v0_to_v1(connection: sqlite3.Connection) -> None:
        connection.execute("BEGIN IMMEDIATE")
        try:
            old_tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            unexpected = {name for name in old_tables if not name.startswith("sqlite_")} - {"radar_sources_v0"}
            if unexpected:
                raise RadarStoreError(
                    "Migração v0 recusada: o arquivo contém tabelas fora do fixture do Radar."
                )
            for statement in _SCHEMA_V1_STATEMENTS:
                connection.execute(statement)
            if "radar_sources_v0" in old_tables:
                rows = connection.execute(
                    "SELECT source_id, display_name, canonical_url, created_at FROM radar_sources_v0 ORDER BY source_id"
                ).fetchall()
                for row in rows:
                    source_id = _text(row["source_id"], "legacy.source_id", maximum=256)
                    display_name = _text(row["display_name"], "legacy.display_name", maximum=500)
                    canonical_url = _url(row["canonical_url"], "legacy.canonical_url")
                    created_at = _timestamp(row["created_at"], "legacy.created_at")
                    parts = urlsplit(canonical_url or "")
                    connection.execute(
                        """INSERT INTO radar_sources
                           (source_id, display_name, canonical_url, domain, source_type,
                            access_policy, rights_status, metadata_json, created_at, updated_at)
                           VALUES (?, ?, ?, ?, 'unknown', 'unreviewed', 'unknown', '{}', ?, ?)""",
                        (source_id, display_name, canonical_url,
                         (parts.hostname or "unknown").casefold(), created_at, created_at),
                    )
                connection.execute("DROP TABLE radar_sources_v0")
            connection.execute("PRAGMA user_version = 1")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
        connection.execute("BEGIN IMMEDIATE")
        try:
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            unexpected = {name for name in tables if not name.startswith(("radar_", "sqlite_"))}
            if unexpected or "radar_documents" not in tables or "radar_sources" not in tables:
                raise RadarStoreError("Migração v1→v2 recusada: banco não corresponde ao namespace do Radar.")
            document_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(radar_documents)").fetchall()
            }
            additive_columns = (
                ("body_sha256", "TEXT"),
                ("body_segment_hashes_json", "TEXT NOT NULL DEFAULT '[]'"),
                ("body_char_count", "INTEGER NOT NULL DEFAULT 0 CHECK (body_char_count >= 0)"),
                ("origin_url", "TEXT"),
            )
            for name, declaration in additive_columns:
                if name not in document_columns:
                    connection.execute(f"ALTER TABLE radar_documents ADD COLUMN {name} {declaration}")
            for statement in _SCHEMA_V2_STATEMENTS:
                connection.execute(statement)
            connection.execute("PRAGMA user_version = 2")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _migrate_v2_to_v3(connection: sqlite3.Connection) -> None:
        """Add sourced role/interview records and allow evidenced homonyms."""
        connection.execute("PRAGMA foreign_keys = OFF")
        try:
            connection.execute("BEGIN IMMEDIATE")
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            unexpected = {name for name in tables if not name.startswith(("radar_", "sqlite_"))}
            if unexpected or "radar_entities" not in tables or "radar_documents" not in tables:
                raise RadarStoreError("Migração v2→v3 recusada: banco não corresponde ao namespace do Radar.")
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(radar_entities)").fetchall()
            }
            expected = {
                "entity_id", "entity_kind", "canonical_name", "normalized_name", "language",
                "metadata_json", "created_at", "updated_at",
            }
            if not expected.issubset(columns):
                raise RadarStoreError("Migração v2→v3 recusada: schema de entidades inesperado.")
            connection.execute(
                """CREATE TABLE radar_entities_v3 (
                    entity_id TEXT PRIMARY KEY,
                    entity_kind TEXT NOT NULL CHECK (entity_kind IN ('person','organization','game','hardware','project','creator','mod','company','other')),
                    canonical_name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    language TEXT NOT NULL,
                    identity_source_document_id TEXT REFERENCES radar_documents(document_id) ON DELETE RESTRICT,
                    identity_context TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(entity_kind, normalized_name, language, identity_context)
                )"""
            )
            connection.execute(
                """INSERT INTO radar_entities_v3
                   (entity_id, entity_kind, canonical_name, normalized_name, language,
                    identity_source_document_id, identity_context, metadata_json, created_at, updated_at)
                   SELECT entity_id, entity_kind, canonical_name, normalized_name, language,
                          NULL, '', metadata_json, created_at, updated_at
                   FROM radar_entities"""
            )
            connection.execute("DROP TABLE radar_entities")
            connection.execute("ALTER TABLE radar_entities_v3 RENAME TO radar_entities")
            for statement in _SCHEMA_V3_STATEMENTS:
                connection.execute(statement)
            connection.execute("PRAGMA user_version = 3")
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RadarStoreError("Migração Radar v2→v3 deixou referências sem destino.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.execute("PRAGMA foreign_keys = ON")

    @staticmethod
    def _migrate_v3_to_v4(connection: sqlite3.Connection) -> None:
        """Add explicit source lineage and immutable claim records."""
        try:
            connection.execute("BEGIN IMMEDIATE")
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            unexpected = {name for name in tables if not name.startswith(("radar_", "sqlite_"))}
            if unexpected or not {"radar_claims", "radar_claim_sources", "radar_claim_events"}.issubset(tables):
                raise RadarStoreError("Migração v3→v4 recusada: banco não corresponde ao namespace do Radar.")
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(radar_claim_sources)").fetchall()
            }
            expected = {"claim_id", "source_id", "document_id", "relation_type", "origin_group_id", "linked_at"}
            if not expected.issubset(columns) or "based_on_source_id" in columns:
                raise RadarStoreError("Migração v3→v4 recusada: schema de linhagem de alegações inesperado.")
            connection.execute(
                """ALTER TABLE radar_claim_sources
                   ADD COLUMN based_on_source_id TEXT REFERENCES radar_sources(source_id) ON DELETE RESTRICT"""
            )
            for statement in _SCHEMA_V4_STATEMENTS:
                connection.execute(statement)
            connection.execute("PRAGMA user_version = 4")
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RadarStoreError("Migração Radar v3→v4 deixou referências sem destino.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _migrate_v4_to_v5(connection: sqlite3.Connection) -> None:
        """Add the durable append-only reservation ledger for per-domain quotas."""
        try:
            connection.execute("BEGIN IMMEDIATE")
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            unexpected = {name for name in tables if not name.startswith(("radar_", "sqlite_"))}
            if unexpected or not {"radar_sources", "radar_claim_sources"}.issubset(tables):
                raise RadarStoreError("Migração v4→v5 recusada: banco não corresponde ao namespace do Radar.")
            claim_source_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(radar_claim_sources)").fetchall()
            }
            if "based_on_source_id" not in claim_source_columns:
                raise RadarStoreError("Migração v4→v5 recusada: linhagem de alegações incompleta.")
            for statement in _SCHEMA_V5_STATEMENTS:
                connection.execute(statement)
            connection.execute("PRAGMA user_version = 5")
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RadarStoreError("Migração Radar v4→v5 deixou referências sem destino.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _migrate_v5_to_v6(connection: sqlite3.Connection) -> None:
        """Add an indexed story-revision link to durable research requests."""
        connection.execute("BEGIN IMMEDIATE")
        try:
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            unexpected = {name for name in tables if not name.startswith(("radar_", "sqlite_"))}
            if unexpected or "radar_research_requests" not in tables:
                raise RadarStoreError("Migração v5→v6 recusada: banco não corresponde ao namespace do Radar.")
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(radar_research_requests)").fetchall()
            }
            if "story_revision_id" not in columns:
                connection.execute("ALTER TABLE radar_research_requests ADD COLUMN story_revision_id TEXT")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_radar_research_story_revision "
                "ON radar_research_requests(story_id, story_revision_id, created_at)"
            )
            connection.execute("PRAGMA user_version = 6")
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RadarStoreError("Migração Radar v5→v6 deixou referências sem destino.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _migrate_v6_to_v7(connection: sqlite3.Connection) -> None:
        """Add explicit candidate evaluation states and typed audit events."""
        connection.execute("BEGIN IMMEDIATE")
        try:
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            unexpected = {name for name in tables if not name.startswith(("radar_", "sqlite_"))}
            if unexpected or not {"radar_candidates", "radar_candidate_events"}.issubset(tables):
                raise RadarStoreError("Migração v6→v7 recusada: banco não corresponde ao namespace do Radar.")
            candidate_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(radar_candidates)").fetchall()
            }
            if "evaluation_state" not in candidate_columns:
                connection.execute(
                    "ALTER TABLE radar_candidates ADD COLUMN evaluation_state TEXT NOT NULL "
                    "DEFAULT 'eligible' CHECK (evaluation_state IN ('eligible','blocked','needs_evaluation'))"
                )
            if "membership_locked" not in candidate_columns:
                connection.execute(
                    "ALTER TABLE radar_candidates ADD COLUMN membership_locked INTEGER NOT NULL "
                    "DEFAULT 0 CHECK (membership_locked IN (0,1))"
                )
            event_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(radar_candidate_events)").fetchall()
            }
            if "event_kind" not in event_columns:
                connection.execute(
                    "ALTER TABLE radar_candidate_events ADD COLUMN event_kind TEXT NOT NULL "
                    "DEFAULT 'lane_changed' CHECK (event_kind IN "
                    "('candidate_created','candidate_updated','lane_changed','evaluation_reactivated',"
                    "'evaluation_resolved','manual_swap'))"
                )
            if "from_evaluation_state" not in event_columns:
                connection.execute("ALTER TABLE radar_candidate_events ADD COLUMN from_evaluation_state TEXT")
            if "to_evaluation_state" not in event_columns:
                connection.execute("ALTER TABLE radar_candidate_events ADD COLUMN to_evaluation_state TEXT")
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS radar_candidates_reactivate_on_observation
                   AFTER INSERT ON radar_observation_events
                   WHEN NEW.event_type IN ('first_seen','title_changed','body_changed','corrected','removed','url_changed','origin_linked')
                   BEGIN
                     INSERT INTO radar_candidate_events
                       (event_id,candidate_id,from_lane,to_lane,actor,reason,occurred_at,evidence_json,event_kind,
                        from_evaluation_state,to_evaluation_state)
                     SELECT lower(hex(randomblob(16))), c.candidate_id, c.queue_lane,
                       CASE WHEN c.membership_locked=0 AND c.story_id IS NULL
                                  AND c.queue_lane IN ('principal','reserva')
                            THEN 'monitoramento' ELSE c.queue_lane END,
                       'radar.observation', 'Mudança material de documento reabre avaliação.', NEW.observed_at,
                       json_object('topic_id',c.topic_id,'evidence_kind','observation_event',
                                   'evidence_event_id',NEW.event_id,'evidence_event_type',NEW.event_type),
                       'evaluation_reactivated', c.evaluation_state, 'needs_evaluation'
                     FROM radar_candidates c
                     JOIN radar_document_topics dt ON dt.topic_id=c.topic_id
                     WHERE dt.document_id=NEW.document_id;
                     UPDATE radar_candidates
                       SET evaluation_state='needs_evaluation',
                           queue_lane=CASE WHEN membership_locked=0 AND story_id IS NULL
                                                  AND queue_lane IN ('principal','reserva')
                                           THEN 'monitoramento' ELSE queue_lane END,
                           last_material_change=NEW.observed_at, updated_at=NEW.observed_at
                       WHERE topic_id IN (SELECT topic_id FROM radar_document_topics WHERE document_id=NEW.document_id);
                   END"""
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS radar_candidates_reactivate_on_claim_event
                   AFTER INSERT ON radar_claim_events
                   WHEN NEW.event_type IN ('evidence_added','origin_traced','content_confirmed','content_partially_confirmed',
                     'content_contradicted','content_withdrawn','correction_recorded','dispute_recorded','superseded')
                   BEGIN
                     INSERT INTO radar_candidate_events
                       (event_id,candidate_id,from_lane,to_lane,actor,reason,occurred_at,evidence_json,event_kind,
                        from_evaluation_state,to_evaluation_state)
                     SELECT lower(hex(randomblob(16))), c.candidate_id, c.queue_lane,
                       CASE WHEN c.membership_locked=0 AND c.story_id IS NULL
                                  AND c.queue_lane IN ('principal','reserva')
                            THEN 'monitoramento' ELSE c.queue_lane END,
                       'radar.claim', 'Mudança material de alegação reabre avaliação.', NEW.occurred_at,
                       json_object('topic_id',c.topic_id,'evidence_kind','claim_event',
                                   'evidence_event_id',NEW.event_id,'evidence_event_type',NEW.event_type),
                       'evaluation_reactivated', c.evaluation_state, 'needs_evaluation'
                     FROM radar_candidates c
                     JOIN radar_claims cl ON cl.topic_id=c.topic_id
                     WHERE cl.claim_id=NEW.claim_id;
                     UPDATE radar_candidates
                       SET evaluation_state='needs_evaluation',
                           queue_lane=CASE WHEN membership_locked=0 AND story_id IS NULL
                                                  AND queue_lane IN ('principal','reserva')
                                           THEN 'monitoramento' ELSE queue_lane END,
                           last_material_change=NEW.occurred_at, updated_at=NEW.occurred_at
                       WHERE topic_id IN (SELECT topic_id FROM radar_claims WHERE claim_id=NEW.claim_id);
                   END"""
            )
            connection.execute("PRAGMA user_version = 7")
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RadarStoreError("Migração Radar v6→v7 deixou referências sem destino.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def reserve_domain_request(
        self,
        *,
        domain: str,
        quota_date: str,
        timezone_name: str,
        quota_limit: int,
        request_key: str,
        reserved_at: str,
    ) -> bool:
        """Atomically reserve one outbound request under a local-day domain cap."""
        from .radar_policy import normalize_domain

        domain = normalize_domain(domain)
        quota_date = _text(quota_date, "quota_date", maximum=10)  # type: ignore[assignment]
        try:
            date.fromisoformat(quota_date)  # type: ignore[arg-type]
        except ValueError as error:
            raise RadarStoreError("quota_date precisa ser uma data ISO válida.") from error
        timezone_name = _text(timezone_name, "timezone_name", maximum=128)  # type: ignore[assignment]
        request_key = _text(request_key, "request_key", maximum=256)  # type: ignore[assignment]
        reserved_at = _timestamp(reserved_at, "reserved_at")  # type: ignore[assignment]
        if isinstance(quota_limit, bool) or not isinstance(quota_limit, int) or quota_limit < 1:
            raise RadarStoreError("quota_limit precisa ser inteiro positivo.")
        with closing(self.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT domain, quota_date, timezone_name FROM radar_domain_quota_events WHERE request_key=?",
                    (request_key,),
                ).fetchone()
                if existing is not None:
                    if (existing["domain"], existing["quota_date"], existing["timezone_name"]) != (
                        domain, quota_date, timezone_name,
                    ):
                        raise RadarStoreError("request_key já foi usado por outra reserva de quota.")
                    connection.commit()
                    return True
                used = connection.execute(
                    """SELECT COUNT(*) FROM radar_domain_quota_events
                       WHERE domain=? AND quota_date=? AND timezone_name=?""",
                    (domain, quota_date, timezone_name),
                ).fetchone()[0]
                if used >= quota_limit:
                    connection.commit()
                    return False
                connection.execute(
                    """INSERT INTO radar_domain_quota_events
                       (event_id, request_key, domain, quota_date, timezone_name, quota_limit, reserved_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), request_key, domain, quota_date, timezone_name, quota_limit, reserved_at),
                )
                connection.commit()
                return True
            except Exception:
                connection.rollback()
                raise

    def domain_quota_usage(self, *, domain: str, quota_date: str, timezone_name: str) -> int:
        from .radar_policy import normalize_domain

        normalized = normalize_domain(domain)
        with closing(self.connect()) as connection:
            row = connection.execute(
                """SELECT COUNT(*) FROM radar_domain_quota_events
                   WHERE domain=? AND quota_date=? AND timezone_name=?""",
                (normalized, quota_date, timezone_name),
            ).fetchone()
            return int(row[0])

    @staticmethod
    def backup_database(source: Path, destination: Path) -> Path:
        source_path = _validate_resolved_path(Path(source))
        destination_path = _validate_resolved_path(Path(destination))
        if source_path == destination_path:
            raise RadarStoreError("Backup precisa apontar para outro arquivo.")
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        if destination_path.exists():
            raise FileExistsError(destination_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(source_path)) as source_db, closing(sqlite3.connect(destination_path)) as backup_db:
            source_db.backup(backup_db)
        return destination_path

    @staticmethod
    def restore_backup(backup: Path, destination: Path) -> Path:
        return RadarStore.backup_database(backup, destination)

    def backup_to(self, destination: Path) -> Path:
        return self.backup_database(self.db_path, destination)

    def table_names(self) -> set[str]:
        with closing(self.connect()) as connection:
            return {
                row["name"] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

    def register_source(
        self, *, source_id: str, display_name: str, canonical_url: str, source_type: str = "unknown",
        access_policy: str = "unreviewed", rights_status: str = "unknown", language: str | None = None,
        metadata: Mapping[str, Any] | None = None, now: str,
    ) -> None:
        source_id = _text(source_id, "source_id", maximum=256)  # type: ignore[assignment]
        display_name = _text(display_name, "display_name", maximum=500)  # type: ignore[assignment]
        canonical_url = _url(canonical_url, "canonical_url")  # type: ignore[assignment]
        if source_type not in _SOURCE_TYPES or access_policy not in _ACCESS_POLICIES or rights_status not in _RIGHTS_STATUSES:
            raise RadarStoreError("Estado ou tipo de fonte fora do catálogo permitido.")
        language = _text(language, "language", maximum=32, optional=True)
        now = _timestamp(now, "now")  # type: ignore[assignment]
        domain = (urlsplit(canonical_url).hostname or "unknown").casefold()
        metadata_json = _json(dict(metadata or {}), "source_metadata")
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    """INSERT INTO radar_sources
                       (source_id, display_name, canonical_url, domain, source_type, access_policy,
                        rights_status, language, metadata_json, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source_id, display_name, canonical_url, domain, source_type, access_policy,
                     rights_status, language, metadata_json, now, now),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("source_id ou canonical_url já registrado.") from error

    def register_document(
        self, *, document_id: str, source_id: str, canonical_url: str, publisher: str,
        language: str, fetched_at: str, content_sha256: str, normalized_sha256: str,
        title: str, summary_snippet: str = "", resolved_url: str | None = None, byline: str | None = None,
        published_at: str | None = None, modified_at: str | None = None, etag: str | None = None,
        last_modified: str | None = None, outbound_primary_refs: Iterable[str] = (),
        access_policy: str = "unreviewed", rights_status: str = "unknown",
        content_retention: str = "metadata_only", fetch_status: str = "observed", retry_after: str | None = None,
    ) -> None:
        document_id = _text(document_id, "document_id", maximum=256)  # type: ignore[assignment]
        source_id = _text(source_id, "source_id", maximum=256)  # type: ignore[assignment]
        canonical_url = _url(canonical_url, "canonical_url")  # type: ignore[assignment]
        resolved_url = _url(resolved_url, "resolved_url", optional=True)
        publisher = _text(publisher, "publisher", maximum=500)  # type: ignore[assignment]
        language = _text(language, "language", maximum=32)  # type: ignore[assignment]
        fetched_at = _timestamp(fetched_at, "fetched_at")  # type: ignore[assignment]
        published_at = _date_or_timestamp(published_at, "published_at", optional=True)
        modified_at = _date_or_timestamp(modified_at, "modified_at", optional=True)
        retry_after = _timestamp(retry_after, "retry_after", optional=True)
        content_sha256 = _sha256(content_sha256, "content_sha256")  # type: ignore[assignment]
        normalized_sha256 = _sha256(normalized_sha256, "normalized_sha256")  # type: ignore[assignment]
        title = _text(title, "title", maximum=1_000)  # type: ignore[assignment]
        summary_snippet = summary_snippet if isinstance(summary_snippet, str) else None
        if summary_snippet is None or len(summary_snippet) > 500:
            raise RadarStoreError("summary_snippet precisa ser texto de até 500 caracteres.")
        _assert_no_credentials(summary_snippet, "summary_snippet")
        byline = _text(byline, "byline", maximum=500, optional=True)
        etag = _text(etag, "etag", maximum=1_000, optional=True)
        last_modified = _text(last_modified, "last_modified", maximum=256, optional=True)
        if access_policy not in _ACCESS_POLICIES or rights_status not in _RIGHTS_STATUSES:
            raise RadarStoreError("Política de acesso ou estado de direitos inválido.")
        if content_retention not in _RETENTION_POLICIES or fetch_status not in _FETCH_STATUSES:
            raise RadarStoreError("Retenção ou estado de coleta inválido.")
        if content_retention == "short_excerpt" and rights_status != "authorized":
            raise RadarStoreError("Trecho curto exige direitos autorizados no registro.")
        if content_retention == "metadata_only" and summary_snippet:
            raise RadarStoreError("Resumo textual exige retenção short_excerpt e direitos autorizados.")
        refs = [_url(item, "outbound_primary_ref") for item in outbound_primary_refs]
        refs_json = _json(refs, "outbound_primary_refs")
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    """INSERT INTO radar_documents
                       (document_id, source_id, canonical_url, resolved_url, publisher, byline, language,
                        published_at, modified_at, fetched_at, etag, last_modified, content_sha256,
                        normalized_sha256, title, summary_snippet, outbound_primary_refs_json,
                        access_policy, rights_status, content_retention, fetch_status, retry_after)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (document_id, source_id, canonical_url, resolved_url, publisher, byline, language,
                     published_at, modified_at, fetched_at, etag, last_modified, content_sha256,
                     normalized_sha256, title, summary_snippet, refs_json, access_policy, rights_status,
                     content_retention, fetch_status, retry_after),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Documento repetido ou fonte de origem inexistente.") from error

    def get_document_by_source_url(self, *, source_id: str, canonical_url: str) -> dict[str, Any] | None:
        source_id = _text(source_id, "source_id", maximum=256)  # type: ignore[assignment]
        canonical_url = _url(canonical_url, "canonical_url")  # type: ignore[assignment]
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM radar_documents WHERE source_id=? AND canonical_url=?",
                (source_id, canonical_url),
            ).fetchone()
        return dict(row) if row is not None else None

    def record_fetch_event(
        self, *, source_id: str, request_url: str, observed_at: str, fetch_status: str,
        response_sha256: str | None = None, etag: str | None = None,
        last_modified: str | None = None, retry_at: str | None = None,
    ) -> str:
        source_id = _text(source_id, "source_id", maximum=256)  # type: ignore[assignment]
        request_url = _url(request_url, "request_url")  # type: ignore[assignment]
        observed_at = _timestamp(observed_at, "observed_at")  # type: ignore[assignment]
        response_sha256 = _sha256(response_sha256, "response_sha256", optional=True)
        etag = _text(etag, "etag", maximum=1_000, optional=True)
        last_modified = _text(last_modified, "last_modified", maximum=256, optional=True)
        retry_at = _timestamp(retry_at, "retry_at", optional=True)
        if fetch_status not in {"observed", "not_modified", "removed", "forbidden", "rate_limited", "error", "blocked"}:
            raise RadarStoreError("fetch_status inválido para histórico do Radar.")
        event_id = uuid.uuid4().hex
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    """INSERT INTO radar_fetch_events
                       (fetch_event_id, source_id, request_url, observed_at, fetch_status,
                        response_sha256, etag, last_modified, retry_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event_id, source_id, request_url, observed_at, fetch_status,
                     response_sha256, etag, last_modified, retry_at),
                )
                connection.commit()
                return event_id
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("FetchEvent sem fonte registrada ou inválido.") from error

    def get_fetch_cache(self, *, source_id: str, request_url: str) -> dict[str, Any] | None:
        source_id = _text(source_id, "source_id", maximum=256)  # type: ignore[assignment]
        request_url = _url(request_url, "request_url")  # type: ignore[assignment]
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM radar_fetch_cache WHERE source_id=? AND request_url=?",
                (source_id, request_url),
            ).fetchone()
        return dict(row) if row is not None else None

    def save_fetch_cache(
        self, *, source_id: str, request_url: str, fetched_at: str, fetch_status: str,
        etag: str | None = None, last_modified: str | None = None,
        response_sha256: str | None = None,
    ) -> None:
        source_id = _text(source_id, "source_id", maximum=256)  # type: ignore[assignment]
        request_url = _url(request_url, "request_url")  # type: ignore[assignment]
        fetched_at = _timestamp(fetched_at, "fetched_at")  # type: ignore[assignment]
        etag = _text(etag, "etag", maximum=1_000, optional=True)
        last_modified = _text(last_modified, "last_modified", maximum=256, optional=True)
        response_sha256 = _sha256(response_sha256, "response_sha256", optional=True)
        if fetch_status not in {"observed", "not_modified", "removed", "forbidden", "rate_limited", "error", "blocked"}:
            raise RadarStoreError("fetch_status inválido para cache incremental.")
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    """INSERT INTO radar_fetch_cache
                       (source_id, request_url, etag, last_modified, last_fetched_at, response_sha256, fetch_status)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(source_id, request_url) DO UPDATE SET
                         etag=excluded.etag, last_modified=excluded.last_modified,
                         last_fetched_at=excluded.last_fetched_at, response_sha256=excluded.response_sha256,
                         fetch_status=excluded.fetch_status""",
                    (source_id, request_url, etag, last_modified, fetched_at, response_sha256, fetch_status),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Cache incremental sem fonte registrada.") from error

    def observe_document_snapshot(
        self, *, document_id: str, source_id: str, canonical_url: str, publisher: str,
        language: str, fetched_at: str, content_sha256: str, normalized_sha256: str,
        title: str, source_snapshot_id: str, body_sha256: str | None = None,
        body_segment_hashes: Iterable[str] = (), body_char_count: int = 0,
        origin_url: str | None = None, resolved_url: str | None = None, byline: str | None = None,
        published_at: str | None = None, modified_at: str | None = None,
        etag: str | None = None, last_modified: str | None = None,
    ) -> dict[str, Any]:
        """Atomically upsert metadata and append an immutable observation event."""
        document_id = _text(document_id, "document_id", maximum=256)  # type: ignore[assignment]
        source_id = _text(source_id, "source_id", maximum=256)  # type: ignore[assignment]
        canonical_url = _url(canonical_url, "canonical_url")  # type: ignore[assignment]
        origin_url = _url(origin_url, "origin_url", optional=True)
        resolved_url = _url(resolved_url, "resolved_url", optional=True)
        publisher = _text(publisher, "publisher", maximum=500)  # type: ignore[assignment]
        language = _text(language, "language", maximum=32)  # type: ignore[assignment]
        fetched_at = _timestamp(fetched_at, "fetched_at")  # type: ignore[assignment]
        published_at = _date_or_timestamp(published_at, "published_at", optional=True)
        modified_at = _date_or_timestamp(modified_at, "modified_at", optional=True)
        content_sha256 = _sha256(content_sha256, "content_sha256")  # type: ignore[assignment]
        normalized_sha256 = _sha256(normalized_sha256, "normalized_sha256")  # type: ignore[assignment]
        body_sha256 = _sha256(body_sha256, "body_sha256", optional=True)
        title = _text(title, "title", maximum=1_000)  # type: ignore[assignment]
        source_snapshot_id = _text(source_snapshot_id, "source_snapshot_id", maximum=256)  # type: ignore[assignment]
        etag = _text(etag, "etag", maximum=1_000, optional=True)
        last_modified = _text(last_modified, "last_modified", maximum=256, optional=True)
        byline = _text(byline, "byline", maximum=500, optional=True)
        if isinstance(body_char_count, bool) or not isinstance(body_char_count, int) or not 0 <= body_char_count <= 1_000_000:
            raise RadarStoreError("body_char_count fora do limite.")
        if not body_sha256 and body_char_count:
            raise RadarStoreError("body_char_count exige hash de corpo.")
        segment_hashes = [_sha256(item, "body_segment_hash") for item in body_segment_hashes]
        if len(segment_hashes) > 256:
            raise RadarStoreError("Máximo de 256 hashes de segmentos por documento.")
        segments_json = _json(segment_hashes, "body_segment_hashes", max_bytes=32_000)

        with closing(self.connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                existing_event = connection.execute(
                    "SELECT event_id, document_id, event_type FROM radar_observation_events WHERE source_snapshot_id=?",
                    (source_snapshot_id,),
                ).fetchone()
                if existing_event is not None:
                    connection.rollback()
                    return {
                        "document_id": existing_event["document_id"], "event_id": existing_event["event_id"],
                        "event_type": existing_event["event_type"], "is_new": False,
                        "material_change": False, "duplicate_snapshot": True,
                    }
                source = connection.execute(
                    "SELECT access_policy, rights_status FROM radar_sources WHERE source_id=?", (source_id,)
                ).fetchone()
                if source is None:
                    raise RadarStoreError("Documento sem fonte registrada.")
                previous = connection.execute(
                    "SELECT * FROM radar_documents WHERE source_id=? AND canonical_url=?",
                    (source_id, canonical_url),
                ).fetchone()
                if previous is None:
                    collision = connection.execute(
                        "SELECT source_id FROM radar_documents WHERE document_id=?", (document_id,)
                    ).fetchone()
                    if collision is not None:
                        raise RadarStoreError("document_id já pertence a outra origem.")
                    connection.execute(
                        """INSERT INTO radar_documents
                           (document_id, source_id, canonical_url, resolved_url, publisher, byline, language,
                            published_at, modified_at, fetched_at, etag, last_modified, content_sha256,
                            normalized_sha256, title, summary_snippet, outbound_primary_refs_json,
                            access_policy, rights_status, content_retention, fetch_status, retry_after,
                            body_sha256, body_segment_hashes_json, body_char_count, origin_url)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '[]', ?, ?, 'metadata_only', 'observed', NULL, ?, ?, ?, ?)""",
                        (document_id, source_id, canonical_url, resolved_url, publisher, byline, language,
                         published_at, modified_at, fetched_at, etag, last_modified, content_sha256,
                         normalized_sha256, title, source["access_policy"], source["rights_status"],
                         body_sha256, segments_json, body_char_count, origin_url),
                    )
                    event_type = "first_seen"
                    material_change = True
                    previous_hash = None
                    previous_segments: list[str] = []
                    previous_title = None
                else:
                    if previous["document_id"] != document_id:
                        document_id = previous["document_id"]
                    previous_segments = json.loads(previous["body_segment_hashes_json"] or "[]")
                    previous_title = previous["title"]
                    previous_hash = previous["content_sha256"]
                    material_change = (
                        previous["normalized_sha256"] != normalized_sha256 or previous_title != title
                    )
                    event_type = "title_changed" if previous_title != title else "body_changed" if material_change else "repeated"
                    connection.execute(
                        """UPDATE radar_documents SET resolved_url=?, publisher=?, byline=?, language=?,
                             published_at=?, modified_at=?, fetched_at=?, etag=?, last_modified=?,
                             content_sha256=?, normalized_sha256=?, title=?, body_sha256=?,
                             body_segment_hashes_json=?, body_char_count=?, origin_url=?, fetch_status='observed',
                             retry_after=NULL WHERE document_id=?""",
                        (resolved_url, publisher, byline, language, published_at, modified_at, fetched_at,
                         etag, last_modified, content_sha256, normalized_sha256, title, body_sha256,
                         segments_json, body_char_count, origin_url, document_id),
                    )
                current_segments = list(segment_hashes)
                diff: dict[str, Any] = {}
                if previous_title != title:
                    diff["title"] = {"before": previous_title, "after": title}
                if previous is None or previous["body_sha256"] != body_sha256 or previous_segments != current_segments:
                    diff["body"] = {
                        "previous_sha256": None if previous is None else previous["body_sha256"],
                        "current_sha256": body_sha256,
                        "added_segment_hashes": sorted(set(current_segments) - set(previous_segments)),
                        "removed_segment_hashes": sorted(set(previous_segments) - set(current_segments)),
                    }
                if previous is not None and previous_hash != content_sha256:
                    diff["content_hash"] = {
                        "exact_changed": True,
                        "normalized_changed": previous["normalized_sha256"] != normalized_sha256,
                    }
                event_id = stable_hash(json_dumps({
                    "snapshot": source_snapshot_id, "document_id": document_id, "event": event_type,
                }))
                diff_json = _json(diff, "observation_diff")
                connection.execute(
                    """INSERT INTO radar_observation_events
                       (event_id, document_id, source_id, event_type, observed_at,
                        previous_content_sha256, current_content_sha256, source_snapshot_id, diff_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event_id, document_id, source_id, event_type, fetched_at, previous_hash,
                     content_sha256, source_snapshot_id, diff_json),
                )
                connection.commit()
                return {
                    "document_id": document_id, "event_id": event_id, "event_type": event_type,
                    "is_new": previous is None, "material_change": material_change,
                    "duplicate_snapshot": False, "diff": diff,
                }
            except Exception as error:
                connection.rollback()
                if isinstance(error, RadarStoreError):
                    raise
                if isinstance(error, sqlite3.IntegrityError):
                    raise RadarStoreError("Snapshot/documento duplicado ou incompatível.") from error
                raise

    def link_republication_member(
        self, *, group_id: str, basis: str, identity_sha256: str, document_id: str,
        relation: str, evidence: Mapping[str, Any], linked_at: str,
    ) -> None:
        group_id = _text(group_id, "group_id", maximum=256)  # type: ignore[assignment]
        identity_sha256 = _sha256(identity_sha256, "identity_sha256")  # type: ignore[assignment]
        document_id = _text(document_id, "document_id", maximum=256)  # type: ignore[assignment]
        linked_at = _timestamp(linked_at, "linked_at")  # type: ignore[assignment]
        if basis not in {"canonical_origin", "identical_body_same_byline"}:
            raise RadarStoreError("Base de republicação não permitida.")
        if relation not in {"origin", "identical_copy"}:
            raise RadarStoreError("Relação de republicação inválida.")
        evidence_json = _json(dict(evidence), "republication_evidence")
        group_evidence_json = _json({"basis": basis, "identity_sha256": identity_sha256}, "republication_group_evidence")
        with closing(self.connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """INSERT OR IGNORE INTO radar_republication_groups
                       (group_id, basis, identity_sha256, evidence_json, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (group_id, basis, identity_sha256, group_evidence_json, linked_at),
                )
                group = connection.execute(
                    "SELECT group_id FROM radar_republication_groups WHERE basis=? AND identity_sha256=?",
                    (basis, identity_sha256),
                ).fetchone()
                if group is None or group["group_id"] != group_id:
                    raise RadarStoreError("Identidade de grupo de republicação inconsistente.")
                connection.execute(
                    """INSERT OR IGNORE INTO radar_republication_members
                       (group_id, document_id, relation, evidence_json, linked_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (group_id, document_id, relation, evidence_json, linked_at),
                )
                connection.commit()
            except Exception as error:
                connection.rollback()
                if isinstance(error, RadarStoreError):
                    raise
                if isinstance(error, sqlite3.IntegrityError):
                    raise RadarStoreError("Membro de republicação sem documento/grupo ou incompatível.") from error
                raise

    def list_republication_members(self, *, group_id: str) -> list[dict[str, Any]]:
        group_id = _text(group_id, "group_id", maximum=256)  # type: ignore[assignment]
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM radar_republication_members WHERE group_id=? ORDER BY linked_at, document_id",
                (group_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_observation(
        self, *, event_id: str, document_id: str, source_id: str, event_type: str,
        observed_at: str, previous_content_sha256: str | None = None,
        current_content_sha256: str | None = None, source_snapshot_id: str | None = None,
        diff: Mapping[str, Any] | None = None,
    ) -> None:
        if event_type not in {"first_seen", "repeated", "title_changed", "body_changed", "corrected", "removed", "url_changed", "origin_linked", "fetch_error"}:
            raise RadarStoreError("Tipo de ObservationEvent inválido.")
        event_id = _text(event_id, "event_id", maximum=256)  # type: ignore[assignment]
        document_id = _text(document_id, "document_id", maximum=256)  # type: ignore[assignment]
        source_id = _text(source_id, "source_id", maximum=256)  # type: ignore[assignment]
        observed_at = _timestamp(observed_at, "observed_at")  # type: ignore[assignment]
        previous_content_sha256 = _sha256(previous_content_sha256, "previous_content_sha256", optional=True)
        current_content_sha256 = _sha256(current_content_sha256, "current_content_sha256", optional=True)
        source_snapshot_id = _text(source_snapshot_id, "source_snapshot_id", maximum=256, optional=True)
        diff_json = _json(dict(diff or {}), "observation_diff")
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    """INSERT INTO radar_observation_events
                       (event_id, document_id, source_id, event_type, observed_at,
                        previous_content_sha256, current_content_sha256, source_snapshot_id, diff_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event_id, document_id, source_id, event_type, observed_at, previous_content_sha256,
                     current_content_sha256, source_snapshot_id, diff_json),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("ObservationEvent sem documento/fonte compatíveis ou duplicado.") from error

    def register_entity(
        self, *, entity_id: str, entity_kind: str, canonical_name: str, language: str,
        metadata: Mapping[str, Any] | None = None, now: str,
        source_document_id: str | None = None, identity_context: str | None = None,
    ) -> None:
        if entity_kind not in {"person", "organization", "game", "hardware", "project", "creator", "mod", "company", "other"}:
            raise RadarStoreError("entity_kind inválido.")
        entity_id = _text(entity_id, "entity_id", maximum=256)  # type: ignore[assignment]
        canonical_name = _text(canonical_name, "canonical_name", maximum=500)  # type: ignore[assignment]
        language = _language_tag(language, "language")
        source_document_id = _text(source_document_id, "source_document_id", maximum=256, optional=True)
        raw_identity_context = _text(identity_context, "identity_context", maximum=300, optional=True)
        identity_context = normalize_text(raw_identity_context) if raw_identity_context else ""
        if entity_kind in {"person", "project"} and source_document_id is None:
            raise RadarStoreError("Pessoa/projeto público exige documento-fonte permitido.")
        if entity_kind == "person" and metadata:
            raise RadarStoreError("Perfil de pessoa aceita apenas nome, idioma, contexto profissional e documento-fonte; sem dados privados em metadata.")
        if entity_kind == "person" and raw_identity_context and _contains_contact_data(raw_identity_context):
            raise RadarStoreError("identity_context não pode conter contato pessoal.")
        now = _timestamp(now, "now")  # type: ignore[assignment]
        metadata_json = _json(dict(metadata or {}), "entity_metadata")
        with closing(self.connect()) as connection:
            try:
                if source_document_id is not None:
                    _require_public_document(connection, source_document_id)
                if entity_kind == "person":
                    same_name = connection.execute(
                        """SELECT identity_context FROM radar_entities
                           WHERE entity_kind='person' AND normalized_name=? AND language=?""",
                        (normalize_text(canonical_name), language),
                    ).fetchall()
                    if same_name and not identity_context:
                        raise RadarStoreError("Homônimo exige identity_context profissional para não fundir pessoas distintas.")
                    if any(row["identity_context"] == identity_context for row in same_name):
                        raise RadarStoreError("Pessoa com esse nome/contexto já existe; reutilize a entidade ou adicione alias.")
                connection.execute(
                    """INSERT INTO radar_entities
                       (entity_id, entity_kind, canonical_name, normalized_name, language,
                        identity_source_document_id, identity_context, metadata_json, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (entity_id, entity_kind, canonical_name, normalize_text(canonical_name), language,
                     source_document_id, identity_context, metadata_json, now, now),
                )
                connection.commit()
            except RadarStoreError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("entity_id/contexto de identidade repetido ou documento-fonte inexistente.") from error

    def add_entity_alias(
        self, *, alias_id: str, entity_id: str, alias: str, language: str,
        source_document_id: str | None = None, created_at: str,
    ) -> None:
        alias_id = _text(alias_id, "alias_id", maximum=256)  # type: ignore[assignment]
        entity_id = _text(entity_id, "entity_id", maximum=256)  # type: ignore[assignment]
        alias = _text(alias, "alias", maximum=500)  # type: ignore[assignment]
        language = _language_tag(language, "language")
        source_document_id = _text(source_document_id, "source_document_id", maximum=256, optional=True)
        if _contains_contact_data(alias):
            raise RadarStoreError("Alias não pode conter contato pessoal.")
        created_at = _timestamp(created_at, "created_at")  # type: ignore[assignment]
        with closing(self.connect()) as connection:
            try:
                entity = connection.execute(
                    "SELECT entity_kind FROM radar_entities WHERE entity_id=?", (entity_id,)
                ).fetchone()
                if entity is None:
                    raise RadarStoreError("Alias exige entidade registrada.")
                if entity["entity_kind"] in {"person", "project"} and source_document_id is None:
                    raise RadarStoreError("Alias público exige documento-fonte permitido.")
                if source_document_id is not None:
                    _require_public_document(connection, source_document_id)
                connection.execute(
                    """INSERT INTO radar_entity_aliases
                       (alias_id, entity_id, alias, normalized_alias, language, source_document_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (alias_id, entity_id, alias, normalize_text(alias), language, source_document_id, created_at),
                )
                connection.commit()
            except RadarStoreError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Alias duplicado ou entidade/fonte inexistente.") from error

    def add_entity_role(
        self, *, role_id: str, entity_id: str, role_kind: str, role_title: str,
        source_document_id: str, evidence_context: str, recorded_at: str,
        organization_entity_id: str | None = None, project_entity_id: str | None = None,
        valid_from: str | None = None, valid_to: str | None = None,
    ) -> None:
        role_id = _text(role_id, "role_id", maximum=256)  # type: ignore[assignment]
        entity_id = _text(entity_id, "entity_id", maximum=256)  # type: ignore[assignment]
        role_title = _text(role_title, "role_title", maximum=300)  # type: ignore[assignment]
        if _contains_contact_data(role_title):
            raise RadarStoreError("role_title não pode conter contato pessoal.")
        source_document_id = _text(source_document_id, "source_document_id", maximum=256)  # type: ignore[assignment]
        organization_entity_id = _text(organization_entity_id, "organization_entity_id", maximum=256, optional=True)
        project_entity_id = _text(project_entity_id, "project_entity_id", maximum=256, optional=True)
        valid_from = _date_or_timestamp(valid_from, "valid_from", optional=True)
        valid_to = _date_or_timestamp(valid_to, "valid_to", optional=True)
        recorded_at = _timestamp(recorded_at, "recorded_at")  # type: ignore[assignment]
        if valid_from and valid_to and _temporal_instant(valid_to) < _temporal_instant(valid_from):
            raise RadarStoreError("Intervalo de cargo termina antes do início.")
        if role_kind not in {"producer", "director", "developer", "designer", "writer", "artist", "composer", "actor", "voice_actor", "executive", "other"}:
            raise RadarStoreError("role_kind inválido.")
        if evidence_context not in {"interview_quote", "interview_byline", "company_press_release", "official_bio", "credits", "other_public_source"}:
            raise RadarStoreError("evidence_context inválido.")
        with closing(self.connect()) as connection:
            try:
                person = connection.execute("SELECT entity_kind FROM radar_entities WHERE entity_id=?", (entity_id,)).fetchone()
                if person is None or person["entity_kind"] != "person":
                    raise RadarStoreError("Cargo público deve pertencer a uma entidade person.")
                source = _require_public_document(connection, source_document_id)
                if organization_entity_id is not None:
                    organization = connection.execute(
                        "SELECT entity_kind FROM radar_entities WHERE entity_id=?", (organization_entity_id,)
                    ).fetchone()
                    if organization is None or organization["entity_kind"] not in {"organization", "company"}:
                        raise RadarStoreError("organization_entity_id precisa ser organização/empresa registrada.")
                if project_entity_id is not None:
                    project = connection.execute(
                        "SELECT entity_kind FROM radar_entities WHERE entity_id=?", (project_entity_id,)
                    ).fetchone()
                    if project is None or project["entity_kind"] not in {"project", "game"}:
                        raise RadarStoreError("project_entity_id precisa ser projeto/jogo registrado.")
                if evidence_context in {"interview_quote", "interview_byline"}:
                    interview_source = connection.execute(
                        """SELECT 1 FROM radar_interviews
                           WHERE subject_entity_id=? AND original_document_id=?
                           UNION ALL
                           SELECT 1 FROM radar_interview_variants v
                           JOIN radar_interviews i ON i.interview_id=v.interview_id
                           WHERE i.subject_entity_id=? AND v.document_id=?
                           LIMIT 1""",
                        (entity_id, source_document_id, entity_id, source_document_id),
                    ).fetchone()
                    if interview_source is None:
                        raise RadarStoreError("Contexto de entrevista exige documento registrado para essa pessoa e entrevista.")
                elif evidence_context == "company_press_release":
                    if organization_entity_id is None or source["source_type"] != "official":
                        raise RadarStoreError("Press release exige fonte oficial e organização identificada.")
                    company_link = connection.execute(
                        """SELECT 1 FROM radar_document_entities
                           WHERE document_id=? AND entity_id=? AND relation_type='press_release_from'""",
                        (source_document_id, organization_entity_id),
                    ).fetchone()
                    if company_link is None:
                        raise RadarStoreError("Press release precisa estar ligado à organização emissora.")
                duplicate = connection.execute(
                    """SELECT role_id FROM radar_entity_roles
                       WHERE entity_id=? AND role_kind=? AND role_title=?
                         AND organization_entity_id IS ? AND project_entity_id IS ?
                         AND valid_from IS ? AND valid_to IS ? AND source_document_id=?
                         AND evidence_context=?""",
                    (entity_id, role_kind, role_title, organization_entity_id, project_entity_id,
                     valid_from, valid_to, source_document_id, evidence_context),
                ).fetchone()
                if duplicate is not None:
                    raise RadarStoreError("Evidência de cargo já registrada; não duplicar a mesma atribuição.")
                connection.execute(
                    """INSERT INTO radar_entity_roles
                       (role_id, entity_id, role_kind, role_title, organization_entity_id,
                        project_entity_id, valid_from, valid_to, source_document_id,
                        evidence_context, recorded_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (role_id, entity_id, role_kind, role_title, organization_entity_id,
                     project_entity_id, valid_from, valid_to, source_document_id,
                     evidence_context, recorded_at),
                )
                connection.commit()
            except RadarStoreError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Cargo sem pessoa, organização/projeto ou documento-fonte compatível.") from error

    def list_entity_roles(self, *, entity_id: str) -> list[dict[str, Any]]:
        entity_id = _text(entity_id, "entity_id", maximum=256)  # type: ignore[assignment]
        return self.list_rows("radar_entity_roles", where_column="entity_id", where_value=entity_id)

    def register_interview(
        self, *, interview_id: str, subject_entity_id: str, original_document_id: str,
        original_language: str, recorded_at: str,
    ) -> None:
        interview_id = _text(interview_id, "interview_id", maximum=256)  # type: ignore[assignment]
        subject_entity_id = _text(subject_entity_id, "subject_entity_id", maximum=256)  # type: ignore[assignment]
        original_document_id = _text(original_document_id, "original_document_id", maximum=256)  # type: ignore[assignment]
        original_language = _language_tag(original_language, "original_language")
        recorded_at = _timestamp(recorded_at, "recorded_at")  # type: ignore[assignment]
        with closing(self.connect()) as connection:
            try:
                subject = connection.execute(
                    "SELECT entity_kind FROM radar_entities WHERE entity_id=?", (subject_entity_id,)
                ).fetchone()
                if subject is None or subject["entity_kind"] != "person":
                    raise RadarStoreError("Entrevista deve identificar uma pessoa pública registrada.")
                original = _require_public_document(connection, original_document_id)
                if _language_tag(original["language"], "document.language") != original_language:
                    raise RadarStoreError("Idioma original diverge do idioma do documento-fonte.")
                connection.execute(
                    """INSERT INTO radar_interviews
                       (interview_id, subject_entity_id, original_document_id, original_language, recorded_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (interview_id, subject_entity_id, original_document_id, original_language, recorded_at),
                )
                connection.commit()
            except RadarStoreError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Entrevista repetida ou com pessoa/documento incompatíveis.") from error

    def add_interview_variant(
        self, *, interview_id: str, document_id: str, relation_type: str,
        based_on_document_id: str, language: str, recorded_at: str,
    ) -> None:
        interview_id = _text(interview_id, "interview_id", maximum=256)  # type: ignore[assignment]
        document_id = _text(document_id, "document_id", maximum=256)  # type: ignore[assignment]
        based_on_document_id = _text(based_on_document_id, "based_on_document_id", maximum=256)  # type: ignore[assignment]
        language = _language_tag(language, "language")
        recorded_at = _timestamp(recorded_at, "recorded_at")  # type: ignore[assignment]
        if relation_type not in {"translation", "transcript", "republication"}:
            raise RadarStoreError("relation_type de variante de entrevista inválido.")
        with closing(self.connect()) as connection:
            try:
                interview = connection.execute(
                    "SELECT original_document_id FROM radar_interviews WHERE interview_id=?", (interview_id,)
                ).fetchone()
                if interview is None:
                    raise RadarStoreError("Entrevista não registrada.")
                document = _require_public_document(connection, document_id)
                based_on = _require_public_document(connection, based_on_document_id)
                if _language_tag(document["language"], "document.language") != language:
                    raise RadarStoreError("Idioma declarado diverge do documento da variante.")
                if based_on_document_id != interview["original_document_id"]:
                    prior_variant = connection.execute(
                        """SELECT 1 FROM radar_interview_variants
                           WHERE interview_id=? AND document_id=?""",
                        (interview_id, based_on_document_id),
                    ).fetchone()
                    if prior_variant is None:
                        raise RadarStoreError("Variante deve derivar do original ou de outra variante da mesma entrevista.")
                if document_id == interview["original_document_id"]:
                    raise RadarStoreError("Documento original não pode ser registrado como variante.")
                if (
                    _language_tag(document["language"], "document.language")
                    == _language_tag(based_on["language"], "based_on.language")
                    and relation_type == "translation"
                ):
                    raise RadarStoreError("Tradução precisa declarar idioma diferente da origem imediata.")
                connection.execute(
                    """INSERT INTO radar_interview_variants
                       (interview_id, document_id, relation_type, based_on_document_id, language, recorded_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (interview_id, document_id, relation_type, based_on_document_id, language, recorded_at),
                )
                connection.commit()
            except RadarStoreError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Variante de entrevista repetida ou com vínculo inválido.") from error

    def register_topic(self, *, topic_id: str, canonical_key: str, title: str, now: str) -> None:
        topic_id = _text(topic_id, "topic_id", maximum=256)  # type: ignore[assignment]
        canonical_key = _text(canonical_key, "canonical_key", maximum=500)  # type: ignore[assignment]
        title = _text(title, "title", maximum=1_000)  # type: ignore[assignment]
        now = _timestamp(now, "now")  # type: ignore[assignment]
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    """INSERT INTO radar_topics(topic_id, canonical_key, title, status, created_at, updated_at)
                       VALUES (?, ?, ?, 'active', ?, ?)""",
                    (topic_id, canonical_key, title, now, now),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("topic_id ou canonical_key já registrado.") from error

    def link_topic_entity(
        self, *, topic_id: str, entity_id: str, relation_type: str, source_document_id: str | None = None,
    ) -> None:
        relation_type = _text(relation_type, "relation_type", maximum=128)  # type: ignore[assignment]
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    "INSERT INTO radar_topic_entities(topic_id, entity_id, relation_type, source_document_id) VALUES (?, ?, ?, ?)",
                    (topic_id, entity_id, relation_type, source_document_id),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Topic/entity/fonte inválidos ou vínculo repetido.") from error

    def link_document_entity(self, *, document_id: str, entity_id: str, relation_type: str) -> None:
        relation_type = _text(relation_type, "relation_type", maximum=128)  # type: ignore[assignment]
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    "INSERT INTO radar_document_entities(document_id, entity_id, relation_type) VALUES (?, ?, ?)",
                    (document_id, entity_id, relation_type),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Documento/entidade inválidos ou vínculo repetido.") from error

    def link_document_topic(self, *, document_id: str, topic_id: str, relation_type: str) -> None:
        relation_type = _text(relation_type, "relation_type", maximum=128)  # type: ignore[assignment]
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    "INSERT INTO radar_document_topics(document_id, topic_id, relation_type) VALUES (?, ?, ?)",
                    (document_id, topic_id, relation_type),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Documento/topic inválidos ou vínculo repetido.") from error

    def register_claim(
        self, *, claim_id: str, topic_id: str, statement: str, epistemic_status: str,
        reported_by_source_id: str, first_seen_at: str, confidence_in_attribution: float,
        asserted_by_entity_id: str | None = None, earliest_traceable_source_id: str | None = None,
        source_document_id: str | None = None, statement_date: str | None = None,
        published_at: str | None = None, url: str | None = None, confidence_in_content: float | None = None,
        evidence_refs: Iterable[str] = (), republished_by: Iterable[str] = (),
        independent_origin_groups: Iterable[str] = (), disputed_by: Iterable[str] = (),
        superseded_by: str | None = None, new_information_since: str | None = None,
        editorial_review_status: str = "unreviewed", version: int = 1,
    ) -> None:
        if epistemic_status not in _EPISTEMIC_STATUSES:
            raise RadarStoreError("epistemic_status inválido.")
        for name, score in (("confidence_in_attribution", confidence_in_attribution), ("confidence_in_content", confidence_in_content)):
            if score is None and name == "confidence_in_content":
                continue
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
                raise RadarStoreError(f"{name} precisa estar entre 0 e 1.")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise RadarStoreError("version precisa ser inteiro positivo.")
        claim_id = _text(claim_id, "claim_id", maximum=256)  # type: ignore[assignment]
        topic_id = _text(topic_id, "topic_id", maximum=256)  # type: ignore[assignment]
        statement = _text(statement, "statement", maximum=4_000)  # type: ignore[assignment]
        reported_by_source_id = _text(reported_by_source_id, "reported_by_source_id", maximum=256)  # type: ignore[assignment]
        first_seen_at = _timestamp(first_seen_at, "first_seen_at")  # type: ignore[assignment]
        asserted_by_entity_id = _text(asserted_by_entity_id, "asserted_by_entity_id", maximum=256, optional=True)
        earliest_traceable_source_id = _text(earliest_traceable_source_id, "earliest_traceable_source_id", maximum=256, optional=True)
        source_document_id = _text(source_document_id, "source_document_id", maximum=256, optional=True)
        statement_date = _date_or_timestamp(statement_date, "statement_date", optional=True)
        published_at = _date_or_timestamp(published_at, "published_at", optional=True)
        url = _url(url, "url", optional=True)
        superseded_by = _text(superseded_by, "superseded_by", maximum=256, optional=True)
        new_information_since = _text(new_information_since, "new_information_since", maximum=256, optional=True)
        evidence_json = _json(list(evidence_refs), "evidence_refs")
        republished_json = _json(list(republished_by), "republished_by")
        origin_groups_json = _json(list(independent_origin_groups), "independent_origin_groups")
        disputed_json = _json(list(disputed_by), "disputed_by")
        editorial_review_status = _text(editorial_review_status, "editorial_review_status", maximum=64)  # type: ignore[assignment]
        with closing(self.connect()) as connection:
            try:
                _require_public_source(connection, reported_by_source_id)
                if earliest_traceable_source_id is not None:
                    _require_public_source(connection, earliest_traceable_source_id)
                if source_document_id is not None:
                    document = _require_public_document(connection, source_document_id)
                    if document["document_source_id"] != reported_by_source_id:
                        raise RadarStoreError("Documento da alegação não pertence à fonte que a reportou.")
                if epistemic_status in {"official_statement", "named_person_statement"}:
                    if asserted_by_entity_id is None or source_document_id is None:
                        raise RadarStoreError("Declaração oficial/pessoal exige entidade declaradora e documento público.")
                    asserted_entity = connection.execute(
                        "SELECT entity_kind FROM radar_entities WHERE entity_id=?", (asserted_by_entity_id,)
                    ).fetchone()
                    expected_kind = "person" if epistemic_status == "named_person_statement" else None
                    if epistemic_status == "official_statement":
                        if asserted_entity is None or asserted_entity["entity_kind"] not in {"organization", "company"}:
                            raise RadarStoreError("Declaração oficial exige organização/empresa declaradora registrada.")
                    elif asserted_entity is None or asserted_entity["entity_kind"] != expected_kind:
                        raise RadarStoreError("Declaração pessoal exige pessoa declaradora registrada.")
                    statement_link = connection.execute(
                        """SELECT 1 FROM radar_document_entities
                           WHERE document_id=? AND entity_id=? AND relation_type='statement_by'""",
                        (source_document_id, asserted_by_entity_id),
                    ).fetchone()
                    if statement_link is None:
                        raise RadarStoreError("Documento público precisa atribuir a declaração à entidade declaradora.")
                connection.execute(
                    """INSERT INTO radar_claims
                       (claim_id, topic_id, statement, epistemic_status, asserted_by_entity_id,
                        reported_by_source_id, earliest_traceable_source_id, source_document_id,
                        first_seen_at, statement_date, published_at, url, confidence_in_attribution,
                        confidence_in_content, evidence_refs_json, republished_by_json,
                        independent_origin_groups_json, disputed_by_json, superseded_by,
                        new_information_since, editorial_review_status, version)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (claim_id, topic_id, statement, epistemic_status, asserted_by_entity_id,
                     reported_by_source_id, earliest_traceable_source_id, source_document_id, first_seen_at,
                     statement_date, published_at, url, confidence_in_attribution, confidence_in_content,
                     evidence_json, republished_json, origin_groups_json, disputed_json, superseded_by,
                     new_information_since, editorial_review_status, version),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Claim com topic/source/entity/document inválido ou claim_id repetido.") from error

    def link_claim_source(
        self, *, claim_id: str, source_id: str, relation_type: str, origin_group_id: str,
        linked_at: str, document_id: str | None = None, based_on_source_id: str | None = None,
    ) -> None:
        if relation_type not in {"origin", "republished", "independent", "supports", "disputes", "statement"}:
            raise RadarStoreError("relation_type de claim/source inválido.")
        claim_id = _text(claim_id, "claim_id", maximum=256)  # type: ignore[assignment]
        source_id = _text(source_id, "source_id", maximum=256)  # type: ignore[assignment]
        linked_at = _timestamp(linked_at, "linked_at")  # type: ignore[assignment]
        origin_group_id = _text(origin_group_id, "origin_group_id", maximum=256)  # type: ignore[assignment]
        document_id = _text(document_id, "document_id", maximum=256)  # type: ignore[assignment]
        based_on_source_id = _text(based_on_source_id, "based_on_source_id", maximum=256, optional=True)
        with closing(self.connect()) as connection:
            try:
                claim = connection.execute(
                    "SELECT reported_by_source_id, earliest_traceable_source_id FROM radar_claims WHERE claim_id=?",
                    (claim_id,),
                ).fetchone()
                if claim is None:
                    raise RadarStoreError("Claim/source exige uma alegação registrada.")
                _require_public_source(connection, source_id)
                document = _require_public_document(connection, document_id)
                if document["document_source_id"] != source_id:
                    raise RadarStoreError("Documento de proveniência não pertence à fonte vinculada.")
                if relation_type == "origin":
                    expected_origin = claim["earliest_traceable_source_id"] or claim["reported_by_source_id"]
                    if source_id != expected_origin:
                        raise RadarStoreError("Fonte origin precisa ser a origem rastreável ou a fonte reportadora.")
                if relation_type in {"origin", "independent"}:
                    if based_on_source_id is not None:
                        raise RadarStoreError("Origem independente não pode derivar de outra fonte.")
                    group_exists = connection.execute(
                        "SELECT 1 FROM radar_claim_sources WHERE claim_id=? AND origin_group_id=? LIMIT 1",
                        (claim_id, origin_group_id),
                    ).fetchone()
                    if group_exists is not None:
                        raise RadarStoreError("Cada nova origem independente precisa de grupo de origem próprio.")
                elif relation_type == "republished" and based_on_source_id is None:
                    raise RadarStoreError("Republicação exige vínculo explícito com a fonte de origem/intermediária.")
                if based_on_source_id is not None:
                    if based_on_source_id == source_id:
                        raise RadarStoreError("Fonte não pode ser sua própria origem intermediária.")
                    parent = connection.execute(
                        """SELECT 1 FROM radar_claim_sources
                           WHERE claim_id=? AND source_id=? AND origin_group_id=? LIMIT 1""",
                        (claim_id, based_on_source_id, origin_group_id),
                    ).fetchone()
                    if parent is None:
                        raise RadarStoreError("Fonte-base precisa estar registrada na mesma linhagem de alegação.")
                elif relation_type not in {"origin", "independent"}:
                    group_exists = connection.execute(
                        "SELECT 1 FROM radar_claim_sources WHERE claim_id=? AND origin_group_id=? LIMIT 1",
                        (claim_id, origin_group_id),
                    ).fetchone()
                    if group_exists is not None:
                        raise RadarStoreError("Fonte derivada exige base explícita; nova origem exige grupo próprio.")
                connection.execute(
                    """INSERT INTO radar_claim_sources
                       (claim_id, source_id, document_id, relation_type, origin_group_id, linked_at,
                        based_on_source_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (claim_id, source_id, document_id, relation_type, origin_group_id, linked_at,
                     based_on_source_id),
                )
                connection.commit()
            except RadarStoreError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Vínculo de origem inválido ou já registrado.") from error

    def record_claim_event(
        self, *, event_id: str, claim_id: str, event_type: str, occurred_at: str,
        reason: str, event_source_id: str | None = None, event_document_id: str | None = None,
        content_status: str | None = None, evidence_refs: Iterable[str] = (), details: Mapping[str, Any] | None = None,
    ) -> None:
        if event_type not in _CLAIM_EVENT_TYPES:
            raise RadarStoreError("event_type de alegação inválido.")
        if content_status is not None and content_status not in _CONTENT_STATUSES:
            raise RadarStoreError("content_status inválido.")
        expected_content_status = {
            "content_confirmed": "confirmed",
            "content_partially_confirmed": "partially_confirmed",
            "content_contradicted": "contradicted",
            "content_withdrawn": "withdrawn",
        }.get(event_type)
        if expected_content_status is not None and content_status != expected_content_status:
            raise RadarStoreError(f"{event_type} exige content_status={expected_content_status}.")
        if event_type in {"evidence_added", "origin_traced", "republication_linked", "superseded"} and content_status is not None:
            raise RadarStoreError(f"{event_type} não altera content_status.")
        event_id = _text(event_id, "event_id", maximum=256)  # type: ignore[assignment]
        claim_id = _text(claim_id, "claim_id", maximum=256)  # type: ignore[assignment]
        occurred_at = _timestamp(occurred_at, "occurred_at")  # type: ignore[assignment]
        reason = _text(reason, "reason", maximum=2_000)  # type: ignore[assignment]
        event_source_id = _text(event_source_id, "event_source_id", maximum=256, optional=True)
        event_document_id = _text(event_document_id, "event_document_id", maximum=256, optional=True)
        evidence_json = _json(list(evidence_refs), "evidence_refs")
        details_json = _json(dict(details or {}), "claim_event_details")
        evidence_event = event_type != "superseded"
        if evidence_event and (event_source_id is None or event_document_id is None):
            raise RadarStoreError("Evento de alegação exige fonte, documento público e razão.")
        if (event_source_id is None) != (event_document_id is None):
            raise RadarStoreError("Fonte e documento do evento devem ser informados juntos.")
        with closing(self.connect()) as connection:
            try:
                claim = connection.execute("SELECT claim_id FROM radar_claims WHERE claim_id=?", (claim_id,)).fetchone()
                if claim is None:
                    raise RadarStoreError("Evento exige alegação registrada.")
                if event_source_id is not None and event_document_id is not None:
                    _require_public_source(connection, event_source_id)
                    document = _require_public_document(connection, event_document_id)
                    if document["document_source_id"] != event_source_id:
                        raise RadarStoreError("Documento do evento não pertence à fonte declarada.")
                connection.execute(
                    """INSERT INTO radar_claim_events
                       (event_id, claim_id, event_type, content_status, event_source_id, event_document_id,
                        occurred_at, reason, evidence_refs_json, details_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event_id, claim_id, event_type, content_status, event_source_id, event_document_id,
                     occurred_at, reason, evidence_json, details_json),
                )
                connection.commit()
            except RadarStoreError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("ClaimEvent inválido ou duplicado.") from error

    def save_research_request(self, request: ResearchRequest, *, now: str) -> str:
        if not isinstance(request, ResearchRequest):
            raise RadarStoreError("ResearchRequest precisa usar o contrato versionado E02.")
        if not isinstance(request.schema_version, str) or request.schema_version not in SUPPORTED_RESEARCH_REQUEST_SCHEMA_VERSIONS:
            raise RadarStoreError("Versao de ResearchRequest nao suportada pelo RadarStore.")
        if request.schema_version == "1.1" and not request.story_revision_id:
            raise RadarStoreError("ResearchRequest v1.1 exige vínculo com revisão da pauta.")
        if request.schema_version == "1.0" and request.story_revision_id is not None:
            raise RadarStoreError("story_revision_id exige ResearchRequest v1.1.")
        now = _timestamp(now, "now")  # type: ignore[assignment]
        data = request.to_dict()
        request_json = _json(data, "research_request")
        content_hash = stable_hash(request_json)
        with closing(self.connect()) as connection:
            existing = connection.execute(
                "SELECT request_id, content_hash FROM radar_research_requests WHERE idempotency_key=?",
                (request.idempotency_key,),
            ).fetchone()
            if existing:
                if existing["request_id"] == request.request_id and existing["content_hash"] == content_hash:
                    return request.request_id
                raise RadarStoreError("Idempotency key de pesquisa já usada com outro conteúdo.")
            try:
                connection.execute(
                    """INSERT INTO radar_research_requests
                       (request_id, idempotency_key, parent_task_id, story_id, story_revision_id, requester_role_id,
                        requester_persona_id, profile_id, profile_version, request_json, content_hash,
                        state, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)""",
                    (request.request_id, request.idempotency_key, request.parent_task_id, request.story_id,
                     request.story_revision_id,
                     request.requester_role_id, request.requester_persona_id, request.research_profile_id,
                     request.research_profile_version, request_json, content_hash, now, now),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("request_id já registrado.") from error
        return request.request_id

    def save_research_packet(self, packet: ResearchPacket, *, version: int) -> str:
        if not isinstance(packet, ResearchPacket):
            raise RadarStoreError("ResearchPacket precisa usar o contrato versionado E02.")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise RadarStoreError("packet version precisa ser inteiro positivo.")
        packet_id = str(uuid.uuid4())
        data = packet.to_dict()
        packet_json = _json(data, "research_packet")
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    """INSERT INTO radar_research_packets
                       (packet_id, request_id, version, status, packet_json, content_hash, fetched_at, retry_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (packet_id, packet.request_id, version, packet.status, packet_json, packet.content_hash,
                     packet.fetched_at, packet.retry_at),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("ResearchRequest inexistente ou packet version repetida.") from error
        return packet_id

    def create_candidate(
        self, *, candidate_id: str, topic_id: str, queue_lane: str, reason: str,
        depth_available: str, evidence_risk: str, now: str, story_id: str | None = None,
        edition_id: str | None = None, last_material_change: str | None = None,
        priority: float = 0, source_packet_id: str | None = None,
        human_override: Mapping[str, Any] | None = None,
    ) -> None:
        if queue_lane not in _QUEUE_LANES:
            raise RadarStoreError("queue_lane inválido.")
        if isinstance(priority, bool) or not isinstance(priority, (int, float)) or not math.isfinite(float(priority)):
            raise RadarStoreError("priority precisa ser numérica e finita.")
        candidate_id = _text(candidate_id, "candidate_id", maximum=256)  # type: ignore[assignment]
        topic_id = _text(topic_id, "topic_id", maximum=256)  # type: ignore[assignment]
        reason = _text(reason, "reason", maximum=2_000)  # type: ignore[assignment]
        depth_available = _text(depth_available, "depth_available", maximum=256)  # type: ignore[assignment]
        evidence_risk = _text(evidence_risk, "evidence_risk", maximum=256)  # type: ignore[assignment]
        now = _timestamp(now, "now")  # type: ignore[assignment]
        last_material_change = _timestamp(last_material_change, "last_material_change", optional=True)
        story_id = _text(story_id, "story_id", maximum=256, optional=True)
        edition_id = _text(edition_id, "edition_id", maximum=256, optional=True)
        source_packet_id = _text(source_packet_id, "source_packet_id", maximum=256, optional=True)
        override_json = _json(dict(human_override or {}), "human_override")
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    """INSERT INTO radar_candidates
                       (candidate_id, topic_id, story_id, edition_id, queue_lane, reason, depth_available,
                        evidence_risk, last_material_change, priority, source_packet_id, human_override_json,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (candidate_id, topic_id, story_id, edition_id, queue_lane, reason, depth_available,
                     evidence_risk, last_material_change, priority, source_packet_id, override_json, now, now),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("Candidato duplicado ou topic/source packet inexistente.") from error

    def record_candidate_event(
        self, *, event_id: str, candidate_id: str, from_lane: str | None, to_lane: str,
        actor: str, reason: str, occurred_at: str, evidence: Mapping[str, Any] | None = None,
        event_kind: str = "lane_changed", from_evaluation_state: str | None = None,
        to_evaluation_state: str | None = None,
    ) -> None:
        if from_lane is not None and from_lane not in _QUEUE_LANES or to_lane not in _QUEUE_LANES:
            raise RadarStoreError("Lane de CandidateEvent inválida.")
        if event_kind not in _CANDIDATE_EVENT_KINDS:
            raise RadarStoreError("event_kind de CandidateEvent inválido.")
        if from_evaluation_state is not None and from_evaluation_state not in _CANDIDATE_EVALUATION_STATES:
            raise RadarStoreError("from_evaluation_state inválido.")
        if to_evaluation_state is not None and to_evaluation_state not in _CANDIDATE_EVALUATION_STATES:
            raise RadarStoreError("to_evaluation_state inválido.")
        event_id = _text(event_id, "event_id", maximum=256)  # type: ignore[assignment]
        candidate_id = _text(candidate_id, "candidate_id", maximum=256)  # type: ignore[assignment]
        actor = _text(actor, "actor", maximum=256)  # type: ignore[assignment]
        reason = _text(reason, "reason", maximum=2_000)  # type: ignore[assignment]
        occurred_at = _timestamp(occurred_at, "occurred_at")  # type: ignore[assignment]
        evidence_json = _json(dict(evidence or {}), "candidate_event_evidence")
        with closing(self.connect()) as connection:
            try:
                connection.execute(
                    """INSERT INTO radar_candidate_events
                       (event_id, candidate_id, from_lane, to_lane, actor, reason, occurred_at, evidence_json,
                        event_kind, from_evaluation_state, to_evaluation_state)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event_id, candidate_id, from_lane, to_lane, actor, reason, occurred_at, evidence_json,
                     event_kind, from_evaluation_state, to_evaluation_state),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise RadarStoreError("CandidateEvent inválido ou duplicado.") from error

    def get_row(self, table: str, key_column: str, key_value: str) -> dict[str, Any] | None:
        allowed = {
            ("radar_sources", "source_id"), ("radar_documents", "document_id"),
            ("radar_entities", "entity_id"), ("radar_entity_roles", "role_id"),
            ("radar_interviews", "interview_id"),
            ("radar_claims", "claim_id"), ("radar_claim_events", "event_id"),
            ("radar_candidates", "candidate_id"), ("radar_candidate_events", "event_id"),
            ("radar_research_requests", "request_id"), ("radar_research_packets", "packet_id"),
            ("radar_republication_groups", "group_id"),
        }
        if (table, key_column) not in allowed:
            raise RadarStoreError("Tabela/chave de leitura não suportada.")
        with closing(self.connect()) as connection:
            row = connection.execute(f"SELECT * FROM {table} WHERE {key_column}=?", (key_value,)).fetchone()
        return dict(row) if row is not None else None

    def list_rows(self, table: str, *, where_column: str | None = None, where_value: str | None = None) -> list[dict[str, Any]]:
        allowed = {
            "radar_sources", "radar_documents", "radar_observation_events", "radar_entities", "radar_entity_aliases",
            "radar_topics", "radar_topic_entities", "radar_document_entities", "radar_document_topics", "radar_claims",
            "radar_claim_sources", "radar_claim_events", "radar_research_requests", "radar_research_packets",
            "radar_candidates", "radar_candidate_events",
            "radar_fetch_events", "radar_fetch_cache", "radar_republication_groups", "radar_republication_members",
            "radar_entity_roles", "radar_interviews", "radar_interview_variants",
        }
        if table not in allowed:
            raise RadarStoreError("Tabela de leitura não suportada.")
        if where_column is not None and not re.fullmatch(r"[a-z_][a-z0-9_]*", where_column):
            raise RadarStoreError("Filtro de coluna inválido.")
        with closing(self.connect()) as connection:
            if where_column is None:
                rows = connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            else:
                rows = connection.execute(f"SELECT * FROM {table} WHERE {where_column}=? ORDER BY rowid", (where_value,)).fetchall()
        return [dict(row) for row in rows]
