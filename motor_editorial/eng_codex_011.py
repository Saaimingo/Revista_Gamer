"""Single-run live factory proof for ENG-CODEX-011.

The runner joins the existing Radar, AgentQueue/TaskDispatcher, SIWC role
executor, ResearchService/ResearchResultRouter, StoryVersionArchive and layout
renderer. Network access is limited to the exact public GitHub REST endpoints
listed below. Full article, agent and usage artifacts stay under the caller's
private Codex directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import time
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping
from urllib.parse import quote, unquote, urlsplit

from .agent_contracts import (
    AGENT_TASK_ENVELOPE_SCHEMA_VERSION,
    AgentResultEnvelope,
    AgentRoleCatalog,
    AgentRoleProfile,
    AgentTaskEnvelope,
    ResearchPacket,
    canonical_material_claim_id,
    enqueue_contract_task,
    envelope_from_payload,
    load_builtin_role_catalog,
    validate_json_schema,
)
from .agent_siwc import (
    SIWCResponseArtifactStore,
    SIWC_ROLE_EXECUTOR_ID,
    SIWC_ROLE_EXECUTOR_PROFILE,
    _validate_output_references,
    register_siwc_role_executor,
)
from .agent_workflow import (
    RADAR_RESEARCH_EXECUTOR_ID,
    RADAR_RESEARCH_PROFILE,
    RADAR_RESEARCH_TASK_TYPE,
    ResearchResultRouter,
    ResearchTaskExecutor,
)
from .db import Store, json_dumps, stable_hash
from .factory import role_story_draft_to_editorial_output
from .layout.contracts import (
    profile_sha256,
    seal_artifact,
    story_revision_sha256,
    validate_composition_validation,
    validate_story_package,
)
from .layout.engine import (
    DIAGRAMMER_IDENTITY,
    build_visual_needs,
    plan_layout,
    render_preview,
    validate_plan,
    validate_rendered_preview,
)
from .layout.index import LayoutReferenceIndex
from .layout.pipeline import _materialize_references, _read_fixture
from .orchestration import AgentProfile, AgentQueue, TaskDispatcher
from .radar_connectors import RadarConnectorService, SourceProfile
from .radar_incremental import IncrementalRadarService
from .radar_policy import PersistentDomainQuotaGuard
from .radar_store import RadarStore
from .radar_triage import RadarGeneralService, RadarTriagePolicy
from .research_mediation import PUBLIC_SOURCES_SCOPE, RADAR_INDEX_SCOPE, POLICY_SCHEMA_VERSION
from .research_service import ResearchProviderResult, ResearchService
from .siwc import CredentialStore, SIWCClient
from .usage_meter import (
    AgentUsageArtifactStore,
    StoryVersionArchive,
    aggregate_usage_by_persona,
    build_usage_record,
)


REPOSITORY = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = Path.home() / ".codex" / "Revista_Gamer" / "eng-codex-011-live-factory"
GITHUB_DOMAIN = "api.github.com"
DAILY_QUOTA = 8
TOTAL_REQUEST_BUDGET = 4
MAX_CANDIDATES_TO_EDITOR = 12
EDITOR_HANDOFF_LANES = frozenset({"principal", "reserva", "monitoramento"})
MODEL_ID = "gpt-6-luna"
REASONING_EFFORT = "high"
ROBOTS_SNAPSHOT = "User-agent: *\nAllow: /\n"
ROBOTS_PROVENANCE = (
    "https://api.github.com/robots.txt returned HTTP 404 during the authorized preflight; "
    "the allow-all parser snapshot is derived under RFC 9309 section 2.3.1.3, not a fetched robots file."
)
TERMS_PROVENANCE = (
    "GitHub REST API documentation and GitHub Terms of Service reviewed for this mission on 2026-10-26; "
    "public unauthenticated metadata only."
)
SOURCE_CANDIDATES = (
    {"owner": "godotengine", "repo": "godot", "source_id": "github-api-godot-releases", "label": "Godot Engine public releases"},
    {"owner": "ValveSoftware", "repo": "Proton", "source_id": "github-api-proton-releases", "label": "Valve Proton public releases"},
    {"owner": "libsdl-org", "repo": "SDL", "source_id": "github-api-sdl-releases", "label": "SDL public releases"},
)
PERSONA_PACKAGES: dict[str, dict[str, Any]] = {
    "ranzinza": {
        "version": "ranzinza-package-v0.1@3d651fe",
        "ref": "3d651fe1951818767b4a6b935732857f08cb7849",
        "branch": "origin/bloco-02/ranzinza-dna-editorial-v01",
        "files": {
            "docs/personagens/RANZINZA.md": "1488ce058a178eb5d130504112cb1940c3297a1511c014469c7e58242a1e3772",
            "docs/personagens/RANZINZA-DNA-CONCEITUAL-v1.0.md": "a1edde0256082f062904e4b55629d507139e615d103d646a1388471b9cbb1071",
            "docs/personagens/RANZINZA-DNA-OPERACIONAL-v0.2.md": "d4a5f436b6a9859d37a02229f3ee0cbbd0009a50f15f7d6fd3c3d305eca842e7",
            "docs/personagens/RANZINZA-DNA-EDITORIAL-v0.1.md": "2e6bc697026b50d8b758ec25b0b81f97c4205d3a2e5da94788f3a36bed88fe73",
            "docs/personagens/RANZINZA-CONTRATO-CARREGAMENTO-AGENTE-v0.1.md": "bde9405aa277c66ba63639b90a29a78a5a529e52dd2d30ef3135277b67718648",
            "docs/personagens/RANZINZA-AMOSTRAS-APROVADAS-2026-10-19.md": "00ff01d2425177178f4f04c13402ee098fa01be9fdb85d0e1ff8202ee972f79c",
            "docs/personagens/RANZINZA-AUDICOES-APROVADAS-2026-10-24.md": "df13f146cef66b31c5ad581699ee6d3428319fcbcb3040c7e1a7ea75adb8d3a9",
        },
    },
    "beto-cartucho": {
        "version": "beto-cartucho-v0.2@21381c0",
        "ref": "21381c0975bef1da048d7887cbdfbd0dd97bed96",
        "branch": "origin/bloco-02/gamer-dna-v02",
        "files": {
            "docs/personagens/GAMER.md": "3d6e4a24f32748f5b5d1cbfefae11837fb12e8bca8f538c24c383ef50c4ccda3",
            "docs/personagens/GAMER-CONTRATO-COGNITIVO-v0.2.md": "f418527ccb56f782911b9c9c4e86b661eb11fafa54131788a0f8c7215c25ae32",
            "docs/personagens/GAMER-CONTRATO-EXPRESSAO-v0.2.md": "45e89a2de1f0b6b9e133ab3aa11e729fca08383334cce80b5ccf11d5c87b9425",
            "docs/personagens/GAMER-CONTRATO-EDITORIAL-v0.2.md": "62fe52038283bca31d50bb59e96186ee6cc888164dec05f92affd6b64b4d702d",
            "docs/personagens/GAMER-CONTRATO-CARREGAMENTO-E-VALIDACAO-v0.2.md": "13f8fd18e5d1dbb723d1f01eec626f6e69a2730491e4dfd789883ea144e6f7b2",
            "docs/personagens/GAMER-AMOSTRAS-CANDIDATAS-v0.2.md": "ceae5b78520fd61c38314a32a28f7c09a61d5b9ebc2dfaff2bea40f24ac10629",
        },
    },
    "nina-prisma": {
        "version": "nina-prisma-v1.0@21381c0",
        "ref": "21381c0975bef1da048d7887cbdfbd0dd97bed96",
        "branch": "origin/bloco-02/gamer-dna-v02",
        "files": {
            "docs/personagens/NINA-PRISMA.md": "62af383a2dec528a7f38a6e84cd2d30a5706d877ce065f34c0ef0a531078f420",
            "docs/personagens/NINA-PRISMA-CONTRATO-COGNITIVO-v1.0.md": "19446ffe112a3b811b39e13a3a1c66815dd460b4833200f819c2d3224a87d252",
            "docs/personagens/NINA-PRISMA-CONTRATO-EXPRESSAO-v1.0.md": "92d2d68b4e948a3883df0eeb106820c646f81d3669612caf43939fd2a1655dc0",
            "docs/personagens/NINA-PRISMA-CONTRATO-EDITORIAL-v1.0.md": "bc3e6cd90b602a58883b1c2cf4fbe619b12ea0e5e32347dfcbe70e3537aafff3",
            "docs/personagens/NINA-PRISMA-CONTRATO-CARREGAMENTO-E-VALIDACAO-v1.0.md": "686889e7f6a425c8af32a489a7374268bcf77f08c93de51e35b39f482bd139c6",
            "docs/personagens/NINA-PRISMA-AMOSTRAS-APROVADAS-v1.0.md": "3ebf959408a5dd52702f5ec43dd20a17316eea7cb4c7e34f74d9278470361791",
        },
    },
}
PERSONA_LINEAGES = {
    "ranzinza": "hardware e tecnologia; perguntar o que funciona, em quais condições, para quem, com que evidência e custo",
    "beto-cartucho": "jogos e campanha; experiência de jogo descrita sem fingir gameplay próprio",
    "nina-prisma": "mods, criadores e cultura; atribuição, comunidade e licença com distinções claras",
}
INTERNAL_LEAK_MARKERS = (
    "curator_notes_only", "source_body_not_obtained", "rights_not_revalidated",
    "ResearchPacket", "AgentQueue", "TaskDispatcher", "SIWC", "franquia de tokens",
    "como modelo de linguagem", "como uma inteligência artificial", "o sistema não me permitiu",
)


class RunBlocked(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("xb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.rename(temp, path)
    except FileExistsError:
        raise ValueError(f"immutable_artifact_exists:{path.name}") from None
    finally:
        temp.unlink(missing_ok=True)


def _atomic_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("xb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


class Checkpoint:
    def __init__(self, root: Path, run_id: str):
        self.root = root
        self.run_id = run_id
        self.path = root / "checkpoint.json"
        self.state: dict[str, Any] = {
            "mission": "ENG-CODEX-011",
            "run_id": run_id,
            "started_at": _now(),
            "updated_at": _now(),
            "status": "running",
            "stage": "preflight",
            "budget": {"public_domain": GITHUB_DOMAIN, "daily_quota": DAILY_QUOTA, "total_requests_max": TOTAL_REQUEST_BUDGET,
                       "parallel_requests": 1, "siwc_calls_max_per_task": 1, "retries": 0},
            "events": [],
        }
        self.save()

    def save(self) -> None:
        self.state["updated_at"] = _now()
        _atomic_json(self.path, self.state)

    def event(self, stage: str, status: str, **fields: Any) -> None:
        self.state["stage"] = stage
        self.state["events"].append({"at": _now(), "stage": stage, "status": status, **fields})
        self.save()

    @classmethod
    def resume_after_triage(cls, root: Path, run_id: str) -> "Checkpoint":
        checkpoint = cls.__new__(cls)
        checkpoint.root = root
        checkpoint.run_id = run_id
        checkpoint.path = root / "checkpoint.json"
        checkpoint.state = _load_json(checkpoint.path)
        events = checkpoint.state.get("events", [])
        last = events[-1] if isinstance(events, list) and events else {}
        if checkpoint.state.get("run_id") != run_id or checkpoint.state.get("stage") != "triage_agent":
            raise RunBlocked("resume_checkpoint_is_not_at_triage_boundary")
        if last.get("stage") != "triage_agent" or last.get("status") != "succeeded":
            raise RunBlocked("resume_requires_a_durable_successful_triage_result")
        if last.get("task_state") != "succeeded" or last.get("error_code") is not None:
            raise RunBlocked("resume_triage_result_is_not_successful")
        usage_ref = last.get("usage_record_ref")
        if not isinstance(usage_ref, str) or not (root / usage_ref).is_file():
            raise RunBlocked("resume_triage_usage_receipt_missing")
        checkpoint.state["status"] = "running"
        checkpoint.event("resume_after_triage", "started", reused_task_id=last.get("task_id"),
                         repeated_siwc_calls=0, repeated_public_requests=0)
        return checkpoint

    @classmethod
    def resume_after_investigator(cls, root: Path, run_id: str) -> "Checkpoint":
        checkpoint = cls.__new__(cls)
        checkpoint.root = root
        checkpoint.run_id = run_id
        checkpoint.path = root / "checkpoint.json"
        checkpoint.state = _load_json(checkpoint.path)
        events = checkpoint.state.get("events", [])
        last = events[-1] if isinstance(events, list) and events else {}
        if checkpoint.state.get("run_id") != run_id or checkpoint.state.get("stage") != "investigator_agent":
            raise RunBlocked("resume_checkpoint_is_not_at_investigator_boundary")
        if (last.get("stage") != "investigator_agent" or last.get("status") != "blocked"
                or last.get("error_code") != "siwc_result_envelope_invalid"
                or last.get("task_state") != "blocked"):
            raise RunBlocked("resume_requires_the_known_investigator_envelope_blocker")
        usage_ref = last.get("usage_record_ref")
        if not isinstance(usage_ref, str) or not (root / usage_ref).is_file():
            raise RunBlocked("resume_investigator_usage_receipt_missing")
        checkpoint.state["status"] = "running"
        checkpoint.event("resume_after_investigator", "started", reused_task_id=last.get("task_id"),
                         repeated_siwc_calls=0, repeated_public_requests=0,
                         recovery="validate_and_adopt_persisted_response")
        return checkpoint

    @classmethod
    def resume_after_pre_external_writer_block(cls, root: Path, run_id: str) -> "Checkpoint":
        checkpoint = cls.__new__(cls)
        checkpoint.root = root
        checkpoint.run_id = run_id
        checkpoint.path = root / "checkpoint.json"
        checkpoint.state = _load_json(checkpoint.path)
        active = _load_json(root / "active-run.json")
        events = checkpoint.state.get("events", [])
        last = events[-1] if isinstance(events, list) and events else {}
        direct_writer_boundary = (
            checkpoint.state.get("stage") == "journalist_original_agent"
            and last.get("stage") == "journalist_original_agent"
            and last.get("status") == "blocked"
            and last.get("error_code") == "agent_contract_invalid"
            and last.get("task_state") == "blocked"
        )
        recovered_writer_boundary = (
            checkpoint.state.get("stage") == "persona_load"
            and last.get("stage") == "persona_load"
            and last.get("status") == "succeeded"
            and active.get("blocker_code") == "existing_writer_task_is_not_a_safe_pre_external_recovery"
        )
        if (checkpoint.state.get("run_id") != run_id or active.get("run_id") != run_id
                or active.get("status") != "blocked" or not (direct_writer_boundary or recovered_writer_boundary)):
            raise RunBlocked("resume_requires_a_pre_external_writer_contract_block")
        checkpoint.state["status"] = "running"
        checkpoint.event("resume_after_writer_preflight", "started", reused_task_id=last.get("task_id"),
                         repeated_siwc_calls=0, repeated_public_requests=0,
                         recovery="correct_persona_hash_preservation_without_external_retry")
        return checkpoint

    @classmethod
    def resume_after_source_registration_block(cls, root: Path, run_id: str) -> "Checkpoint":
        checkpoint = cls.__new__(cls)
        checkpoint.root = root
        checkpoint.run_id = run_id
        checkpoint.path = root / "checkpoint.json"
        checkpoint.state = _load_json(checkpoint.path)
        active = _load_json(root / "active-run.json")
        events = checkpoint.state.get("events", [])
        last = events[-1] if isinstance(events, list) and events else {}
        if (active.get("run_id") != run_id or active.get("status") != "blocked"
                or active.get("blocker_code") != "RadarStoreError"
                or checkpoint.state.get("run_id") != run_id or checkpoint.state.get("stage") != "persona_load"):
            raise RunBlocked("resume_source_registration_block_not_confirmed")
        if last.get("stage") != "persona_load" or last.get("status") != "succeeded":
            raise RunBlocked("resume_source_registration_boundary_not_persisted")
        checkpoint.state["status"] = "running"
        checkpoint.event("resume_after_source_registration", "started", repeated_siwc_calls=0,
                         repeated_public_requests=0, recovery="reuse_exact_persisted_source_route")
        return checkpoint


def _ensure_git_branch() -> str:
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=REPOSITORY, text=True, encoding="utf-8"
    ).strip()
    if branch != "codex/eng-codex-011-live-factory":
        raise RunBlocked("wrong_eng_011_branch")
    return branch


def _task_id(run_token: str, role_id: str, stage: str) -> str:
    safe_role = re.sub(r"[^a-z0-9-]", "-", role_id.casefold())
    safe_stage = re.sub(r"[^a-z0-9-]", "-", stage.casefold())
    return f"e011-{run_token}-{safe_role}-{safe_stage}"


def _source_profile(source: Mapping[str, str], *, endpoint: str, source_id: str, label: str) -> SourceProfile:
    return SourceProfile.from_mapping({
        "source_id": source_id,
        "connector_kind": "public_api",
        "root_url": endpoint,
        "allowed_hosts": [GITHUB_DOMAIN],
        "allowed_operations": ["api_metadata_read"],
        "access_policy": "allowed",
        "terms_checked_at": "2026-10-26T00:00:00Z",
        "robots_policy": "allowed",
        "robots_checked_at": "2026-10-26T00:00:00Z",
        "min_poll_interval_seconds": 3,
        "max_response_bytes": 131_072 if "releases?" in endpoint else 65_536,
        "timeout_seconds": 20,
        "max_redirects": 0,
        "failure_budget": 1,
        "retry_base_seconds": 60,
        "robots_rules_by_host": {GITHUB_DOMAIN: ROBOTS_SNAPSHOT},
    })


def _register_source(store: RadarStore, profile: SourceProfile, display_name: str, endpoint: str) -> None:
    metadata = {
        "mission": "ENG-CODEX-011",
        "connector_kind": "public_api",
        "host_allowlist": [GITHUB_DOMAIN],
        "access": "public unauthenticated release metadata",
        "terms_provenance": TERMS_PROVENANCE,
        "robots_provenance": ROBOTS_PROVENANCE,
    }
    existing = store.get_row("radar_sources", "source_id", profile.source_id)
    if existing is not None:
        try:
            existing_metadata = json.loads(existing.get("metadata_json") or "{}")
        except json.JSONDecodeError:
            raise RunBlocked("persisted_radar_source_metadata_is_invalid") from None
        if (existing.get("display_name") != display_name or existing.get("canonical_url") != endpoint
                or existing.get("source_type") != "official" or existing.get("access_policy") != "allowed"
                or existing.get("rights_status") != "unknown" or existing.get("language") != "en"
                or existing_metadata != metadata):
            raise RunBlocked("persisted_radar_source_conflicts_with_allowlisted_route")
        return
    store.register_source(
        source_id=profile.source_id,
        display_name=display_name,
        canonical_url=endpoint,
        source_type="official",
        access_policy="allowed",
        rights_status="unknown",
        language="en",
        metadata=metadata,
        now=_now(),
    )


def _release_rows(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def visit(node: Any, depth: int = 0) -> None:
        if depth > 8:
            return
        if isinstance(node, Mapping):
            if isinstance(node.get("tag_name"), str) and (node.get("url") or node.get("html_url")):
                rows.append(dict(node))
                return
            for nested in node.values():
                if isinstance(nested, (Mapping, list, tuple)):
                    visit(nested, depth + 1)
        elif isinstance(node, (list, tuple)):
            for nested in node:
                visit(nested, depth + 1)

    visit(value)
    return rows


def _document_id_from_ref(ref: str) -> str | None:
    match = re.fullmatch(r"radar://document/([a-f0-9]{32})", ref)
    return match.group(1) if match else None


def _source_display_url(document: Mapping[str, Any]) -> str:
    origin = document.get("origin_url")
    canonical = document.get("canonical_url")
    candidate = origin if isinstance(origin, str) else canonical
    return candidate if isinstance(candidate, str) else ""


def _safe_word_excerpt(text: Any, *, maximum_words: int = 25) -> str:
    if not isinstance(text, str):
        return ""
    words = " ".join(text.split()).split(" ")
    return " ".join(words[:maximum_words])


class GitHubReleaseResearchProvider:
    """One safe, source-bound, metadata-only public lookup for one selected tag."""

    def __init__(self, radar_store: RadarStore, incremental: IncrementalRadarService):
        self.radar_store = radar_store
        self.incremental = incremental
        self.routes: dict[str, dict[str, Any]] = {}
        self.last_execution: dict[str, Any] | None = None

    def bind(self, source_id: str, route: Mapping[str, Any]) -> None:
        if source_id in self.routes:
            raise ValueError("research_source_route_already_bound")
        self.routes[source_id] = dict(route)

    def search(self, request: Any, profile: Any, *, cached_document_ids: tuple[str, ...], budget: Any) -> ResearchProviderResult:
        started = time.monotonic()
        if len(request.preferred_source_ids) != 1 or request.preferred_source_ids[0] not in self.routes:
            return ResearchProviderResult(status="blocked", missing_evidence=request.required_evidence_kinds,
                                          constraints=("trusted selected-release source route missing",))
        source_id = request.preferred_source_ids[0]
        route = self.routes[source_id]
        if (tuple(request.allowed_scope) != (RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE)
                or tuple(request.preferred_domains) != (GITHUB_DOMAIN,)
                or budget.max_requests != 1 or budget.max_bytes > 65_536
                or budget.max_sources > 5):
            return ResearchProviderResult(status="blocked", missing_evidence=request.required_evidence_kinds,
                                          constraints=("ResearchRequest exceeds the ENG-011 public lookup budget",))
        tag = route["tag_name"]
        if not isinstance(tag, str) or not tag.strip() or len(tag) > 200 or any(ord(char) < 32 for char in tag):
            return ResearchProviderResult(status="blocked", missing_evidence=request.required_evidence_kinds,
                                          constraints=("selected tag is invalid for a source-bound lookup",))
        tag_path = quote(tag, safe="")
        endpoint = f"https://{GITHUB_DOMAIN}/repos/{route['owner']}/{route['repo']}/releases/tags/{tag_path}"
        parts = urlsplit(endpoint)
        if parts.hostname != GITHUB_DOMAIN or parts.scheme != "https" or parts.username or parts.password:
            return ResearchProviderResult(status="blocked", missing_evidence=request.required_evidence_kinds,
                                          constraints=("source route escaped exact host policy",))
        profile_for_source: SourceProfile = route["profile"]
        result = self.incremental.fetch(profile_for_source, url=endpoint)
        fetch = result.fetch
        execution = {
            "request_id": request.request_id,
            "source_id": source_id,
            "endpoint": endpoint,
            "fetch_status": fetch.status,
            "http_status": fetch.http_status,
            "fetched_at": fetch.fetched_at,
            "payload_bytes": fetch.payload_bytes,
            "payload_sha256": fetch.payload_sha256,
            "redirect_count": fetch.redirect_count,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        self.last_execution = execution
        if fetch.status != "observed" or fetch.http_status != 200 or not result.documents:
            status = "rate_limited" if fetch.http_status == 429 or fetch.status == "rate_limited" else "partial"
            return ResearchProviderResult(
                status=status,
                missing_evidence=request.required_evidence_kinds,
                constraints=(f"selected public release lookup returned {fetch.status}",),
                retry_at=fetch.retry_at,
                requests_used=1,
                bytes_read=fetch.payload_bytes,
                sources_considered=1,
                elapsed_seconds=time.monotonic() - started,
            )
        rows = _release_rows(fetch.metadata)
        exact = next((row for row in rows if row.get("tag_name") == tag), None)
        if exact is None:
            return ResearchProviderResult(
                status="partial", missing_evidence=request.required_evidence_kinds,
                constraints=("release response did not match the requested tag",), requests_used=1,
                bytes_read=fetch.payload_bytes, sources_considered=1, elapsed_seconds=time.monotonic() - started,
            )
        document_id = result.documents[0].document_id
        document = self.radar_store.get_row("radar_documents", "document_id", document_id)
        if document is None:
            return ResearchProviderResult(status="blocked", missing_evidence=request.required_evidence_kinds,
                                          constraints=("fetched public release document was not persisted",), requests_used=1,
                                          bytes_read=fetch.payload_bytes, sources_considered=1,
                                          elapsed_seconds=time.monotonic() - started)

        now = _now()
        owner_id = "github-owner-" + stable_hash(route["owner"])[:20]
        entity = self.radar_store.get_row("radar_entities", "entity_id", owner_id)
        if entity is None:
            self.radar_store.register_entity(
                entity_id=owner_id,
                entity_kind="organization",
                canonical_name=route["owner"],
                language="en",
                metadata={"public_identity": "GitHub repository owner account", "repository": f"{route['owner']}/{route['repo']}"},
                source_document_id=document_id,
                now=now,
            )
        self.radar_store.link_document_entity(document_id=document_id, entity_id=owner_id, relation_type="statement_by")
        topic_id = "topic-" + stable_hash(f"{route['owner']}/{route['repo']}@{tag}")[:24]
        if self.radar_store.get_row("radar_topics", "topic_id", topic_id) is None:
            self.radar_store.register_topic(
                topic_id=topic_id,
                canonical_key=f"{route['owner']}/{route['repo']}@{tag}",
                title=str(exact.get("name") or tag)[:1_000],
                now=now,
            )
        claim_id = "claim-" + stable_hash(request.request_id)[:24]
        excerpt = _safe_word_excerpt(exact.get("body_excerpt"), maximum_words=25)
        statement = excerpt or (
            f"Release {tag} was listed for {route['owner']}/{route['repo']} at "
            f"{exact.get('published_at') or exact.get('created_at') or 'an unreported publication time'}."
        )
        self.radar_store.register_claim(
            claim_id=claim_id,
            topic_id=topic_id,
            statement=statement,
            epistemic_status="official_statement",
            asserted_by_entity_id=owner_id,
            reported_by_source_id=source_id,
            earliest_traceable_source_id=source_id,
            source_document_id=document_id,
            first_seen_at=now,
            statement_date=exact.get("published_at") or exact.get("created_at"),
            published_at=exact.get("published_at") or exact.get("created_at"),
            url=exact.get("html_url") if isinstance(exact.get("html_url"), str) else endpoint,
            confidence_in_attribution=1.0,
            confidence_in_content=1.0,
            evidence_refs=[f"radar://document/{document_id}"],
            editorial_review_status="unreviewed",
        )
        self.radar_store.link_claim_source(
            claim_id=claim_id,
            source_id=source_id,
            relation_type="statement",
            origin_group_id="origin-" + stable_hash(request.request_id)[:20],
            linked_at=now,
            document_id=document_id,
        )
        self.last_execution["document_id"] = document_id
        self.last_execution["claim_id"] = claim_id
        self.last_execution["excerpt_words"] = len(excerpt.split())
        return ResearchProviderResult(
            status="found",
            document_ids=(document_id,),
            claim_ids=(claim_id,),
            requests_used=1,
            bytes_read=fetch.payload_bytes,
            sources_considered=1,
            elapsed_seconds=time.monotonic() - started,
        )


def _build_initial_packet(
    *,
    request_id: str,
    radar_store: RadarStore,
    eligible_candidates: list[dict[str, Any]],
) -> tuple[ResearchPacket, list[dict[str, Any]]]:
    refs: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []
    excerpts: list[str] = []
    evidence_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in eligible_candidates:
        for raw_id in candidate["document_ids"]:
            if raw_id in seen:
                continue
            seen.add(raw_id)
            document = radar_store.get_row("radar_documents", "document_id", raw_id)
            if document is None:
                continue
            evidence_id = f"radar://document/{raw_id}"
            digest = str(document.get("content_sha256") or "")
            refs.append({"ref": evidence_id, "sha256": digest})
            lineage.append({
                "evidence_id": evidence_id,
                "document_id": raw_id,
                "source_id": document.get("source_id"),
                "title": document.get("title"),
                "publisher": document.get("publisher"),
                "author": document.get("byline"),
                "published_at": document.get("published_at"),
                "observed_at": document.get("fetched_at"),
                "url": _source_display_url(document),
                "canonical_source_url": document.get("canonical_url"),
            })
            excerpt = candidate.get("body_excerpt")
            if isinstance(excerpt, str) and excerpt.strip():
                excerpts.append(_safe_word_excerpt(excerpt, maximum_words=25))
            evidence_rows.append({
                "evidence_id": evidence_id,
                "source_id": candidate["source_id"],
                "source_document_id": raw_id,
                "source_url": _source_display_url(document),
                "canonical_source_url": document.get("canonical_url"),
                "title": document.get("title"),
                "publisher": document.get("publisher"),
                "author": document.get("byline"),
                "published_at": document.get("published_at"),
                "observed_at": document.get("fetched_at"),
                "epistemic_status": "official_statement",
                "excerpt": _safe_word_excerpt(excerpt, maximum_words=25) if excerpt else None,
            })
    packet = ResearchPacket.create(
        request_id=request_id,
        status="partial",
        document_refs=refs,
        claim_refs=[],
        source_lineage=lineage,
        new_material_since=_now(),
        relevant_excerpts_short=excerpts,
        missing_evidence=["full_release_details"],
        constraints=[],
        fetched_at=_now(),
    )
    return packet, evidence_rows


def _load_persona(persona_id: str, root: Path) -> tuple[str, dict[str, Any]]:
    package = PERSONA_PACKAGES.get(persona_id)
    if package is None:
        raise RunBlocked("selected_persona_package_missing")
    head = subprocess.check_output(
        ["git", "rev-parse", package["branch"]], cwd=REPOSITORY, text=True, encoding="utf-8"
    ).strip()
    if head != package["ref"]:
        raise RunBlocked("approved_persona_branch_moved_since_preflight")
    persona_dir = root / "approved-persona-sources" / persona_id
    persona_dir.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    files: list[dict[str, str]] = []
    for relative, expected in package["files"].items():
        raw = subprocess.check_output(
            ["git", "show", f"{package['ref']}:{relative}"], cwd=REPOSITORY
        )
        digest = _sha(raw)
        if digest != expected:
            raise RunBlocked("approved_persona_source_sha256_mismatch")
        target = persona_dir / Path(relative).name
        if not target.exists():
            _write_new(target, raw)
        elif _sha(target.read_bytes()) != digest:
            raise RunBlocked("private_persona_archive_conflicts_with_source")
        parts.append(raw.decode("utf-8"))
        files.append({"path": relative, "sha256": digest, "bytes": str(len(raw))})
    composite = "\n".join(parts)
    manifest = {
        "persona_id": persona_id,
        "persona_version": package["version"],
        "source_branch": package["branch"],
        "source_commit": package["ref"],
        "files": files,
        "composite_instruction_sha256": stable_hash(composite),
        "composite_characters": len(composite),
        "modified": False,
        "published": False,
    }
    _atomic_json(persona_dir / "manifest.json", manifest)
    return composite, manifest


def _role_profiles(catalog: AgentRoleCatalog) -> dict[str, AgentRoleProfile]:
    return {
        row["role_id"]: AgentRoleProfile.from_mapping(row)
        for row in catalog.to_mapping()["profiles"]
        if row["role_id"] not in catalog.disabled_role_ids
    }


def _new_role_task(
    *,
    queue: AgentQueue,
    catalog: AgentRoleCatalog,
    profiles: Mapping[str, AgentRoleProfile],
    run_id: str,
    run_token: str,
    story_id: str,
    role_id: str,
    stage: str,
    input_payload: Mapping[str, Any],
    source_snapshot_ids: list[str],
    root: Path,
    research_policy: Mapping[str, Any] | None = None,
    persona_id: str | None = None,
    persona_version: str | None = None,
    persona_text: str | None = None,
    research_packet: ResearchPacket | None = None,
    dependencies: tuple[str, ...] = (),
) -> tuple[str, AgentTaskEnvelope]:
    profile = profiles[role_id]
    task_id = _task_id(run_token, role_id, stage)
    input_bytes = (json.dumps(input_payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    input_ref = root / "task-inputs" / f"{task_id}.json"
    if input_ref.exists():
        if input_ref.read_bytes() != input_bytes:
            raise RunBlocked("persisted_task_input_conflicts_with_idempotent_task")
    else:
        _write_new(input_ref, input_bytes)
    persona_hash = stable_hash(persona_text) if persona_text is not None else None
    envelope_data: dict[str, Any] = {
        "schema_version": AGENT_TASK_ENVELOPE_SCHEMA_VERSION,
        "task_id": task_id,
        "run_id": run_id,
        "story_id": story_id,
        "edition_id": "eng-codex-011-internal-preview",
        "role_id": role_id,
        "role_version": profile.role_version,
        "role_hash": profile.content_hash,
        "input_payload_hash": stable_hash(json_dumps(dict(input_payload))),
        "persona_id": persona_id,
        "persona_version": persona_version,
        "persona_hash": persona_hash,
        "input_artifact_refs": [{"ref": f"private://task-inputs/{task_id}.json", "sha256": _sha(input_bytes)}],
        "source_snapshot_ids": sorted(set(source_snapshot_ids)),
        "authorized_tools": [grant.to_dict() for grant in profile.allowed_tools],
        "deadline": None,
        "context_schema_version": "1.0",
        "usage_guardrails": {"max_calls": 1, "max_iterations": 1},
        "idempotency_key": f"eng-codex-011:{run_id}:{role_id}:{stage}",
        "correlation_id": f"eng-codex-011:{story_id}",
        "requires_human_gate": True,
        "research_mediation_policy": dict(research_policy) if research_policy is not None else None,
    }
    envelope = AgentTaskEnvelope.from_mapping(envelope_data)
    task_id = enqueue_contract_task(
        queue,
        envelope,
        input_payload,
        catalog=catalog,
        executor_profile=SIWC_ROLE_EXECUTOR_PROFILE,
        executor_id=SIWC_ROLE_EXECUTOR_ID,
        max_attempts=1,
        dependencies=dependencies,
        research_packet=research_packet,
    )
    return task_id, envelope


def _task_output(
    *, task_id: str, queue: AgentQueue, response_store: SIWCResponseArtifactStore,
    root: Path, envelope: AgentTaskEnvelope, usage_store: AgentUsageArtifactStore,
    research_suggestion_count: int | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    task = queue.get(task_id)
    metadata_path = root / "siwc-role-responses" / f"{task_id}.metadata.json"
    if task is None or not metadata_path.exists():
        return None, None, None
    metadata = _load_json(metadata_path)
    response_ref = task.result.get("artifact_ref") if isinstance(task.result, Mapping) else None
    if not isinstance(response_ref, Mapping):
        response_path = root / "siwc-role-responses" / f"{task_id}.response.json"
        if not response_path.exists():
            return None, metadata, None
        response_bytes = response_path.read_bytes()
        digest = _sha(response_bytes)
    else:
        response_bytes = response_store.read_response(str(response_ref.get("ref")), str(response_ref.get("sha256")))
        digest = str(response_ref.get("sha256"))
    try:
        structured = json.loads(response_bytes.decode("utf-8"))
        if not isinstance(structured, dict):
            structured = None
    except (UnicodeDecodeError, json.JSONDecodeError):
        structured = None
    usage_metadata = {
        **metadata,
        "provider_call_outcome": "success" if task.state == "succeeded" else ("uncertain" if task.state == "uncertain" else "failed"),
        "research_suggestion_count": research_suggestion_count,
    }
    usage_ref = usage_store.write(build_usage_record(
        task=task,
        envelope=envelope,
        metadata=usage_metadata,
        raw_response=response_bytes,
        research_request_count=research_suggestion_count,
        schema_status=str(metadata.get("output_validation") or task.state),
        story_revision_id=(envelope.research_mediation_policy or {}).get("story_revision_id"),
    ))
    _atomic_json(root / "structured-outputs" / f"{task_id}.json", {
        "task_id": task_id,
        "raw_response_sha256": digest,
        "structured_output": structured,
        "response_metadata": metadata,
    })
    return structured, metadata, usage_ref


def _load_succeeded_role_output(
    *, task_id: str, queue: AgentQueue, role_catalog: AgentRoleCatalog,
    response_store: SIWCResponseArtifactStore, root: Path,
) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    task = queue.get(task_id)
    if task is None or task.state != "succeeded" or task.attempts < 1 or not isinstance(task.result, Mapping):
        raise RunBlocked("persisted_role_task_is_not_succeeded")
    envelope = envelope_from_payload(task.payload)
    role_catalog.validate_task(envelope, input_payload=task.payload.get("input"))
    role_catalog.validate_result(envelope, task.result)
    metadata_path = root / "siwc-role-responses" / f"{task_id}.metadata.json"
    request_path = root / "siwc-role-responses" / f"{task_id}.request.json"
    output_path = root / "structured-outputs" / f"{task_id}.json"
    if not metadata_path.is_file() or not request_path.is_file() or not output_path.is_file():
        raise RunBlocked("persisted_role_output_artifacts_are_incomplete")
    metadata = _load_json(metadata_path)
    output_container = _load_json(output_path)
    response_ref = task.result.get("artifact_ref")
    if not isinstance(response_ref, Mapping):
        raise RunBlocked("persisted_role_result_has_no_response_reference")
    response_bytes = response_store.read_response(str(response_ref.get("ref")), str(response_ref.get("sha256")))
    response_digest = _sha(response_bytes)
    if (response_digest != metadata.get("response_sha256")
            or response_digest != output_container.get("raw_response_sha256")
            or metadata.get("response_completed") is not True
            or metadata.get("store") is not False or metadata.get("stream") is not True
            or metadata.get("model") != MODEL_ID or metadata.get("reasoning_effort") != REASONING_EFFORT):
        raise RunBlocked("persisted_role_response_integrity_check_failed")
    recovered = any(event.get("action") == "external_output_recovered" for event in queue.events(task_id))
    if metadata.get("output_validation") != "role_schema_valid" and not (
        recovered and metadata.get("output_validation") == "result_envelope_rejected"
    ):
        raise RunBlocked("persisted_role_output_validation_state_not_accepted")
    structured_output = json.loads(response_bytes.decode("utf-8"))
    if not isinstance(structured_output, dict) or output_container.get("structured_output") != structured_output:
        raise RunBlocked("persisted_role_structured_output_differs_from_raw_response")
    request_ref = metadata.get("request_artifact_ref")
    request_digest = metadata.get("request_artifact_sha256")
    if not isinstance(request_ref, str) or not isinstance(request_digest, str):
        raise RunBlocked("persisted_role_request_reference_missing")
    request_record = json.loads(response_store.read_response(request_ref, request_digest).decode("utf-8"))
    prompt_input = request_record.get("prompt_input")
    if not isinstance(prompt_input, Mapping):
        raise RunBlocked("persisted_role_request_input_missing")
    task_input_data = prompt_input.get("task_input_data", {}).get("data")
    if not isinstance(task_input_data, Mapping) or dict(task_input_data) != task.payload.get("input"):
        raise RunBlocked("persisted_role_request_does_not_match_task_input")
    profile = role_catalog.resolve(envelope.role_id, envelope.role_version, envelope.role_hash)
    validate_json_schema(structured_output, profile.output_schema, "$output")
    _validate_output_references(envelope.role_id, prompt_input, structured_output)
    usage_path = root / "agent-usage" / f"{task_id}.attempt-{task.attempts:03d}.json"
    usage_ref = usage_path.relative_to(root).as_posix() if usage_path.is_file() else None
    return structured_output, dict(metadata), usage_ref


def _dispatch_role(
    *, dispatcher: TaskDispatcher, queue: AgentQueue, task_id: str, envelope: AgentTaskEnvelope,
    root: Path, response_store: SIWCResponseArtifactStore, usage_store: AgentUsageArtifactStore,
    checkpoint: Checkpoint, stage: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    checkpoint.event(stage, "call_started", task_id=task_id, role_id=envelope.role_id, provider="SIWC", retries=0)
    outcome = dispatcher.dispatch_one(task_id)
    task = queue.get(task_id)
    if task is None:
        checkpoint.event(stage, "blocked", task_id=task_id, error_code="task_missing_after_dispatch")
        raise RunBlocked("task_missing_after_dispatch")
    raw_file = root / "siwc-role-responses" / f"{task_id}.response.json"
    suggestion_count: int | None = None
    if raw_file.exists():
        try:
            raw_output = json.loads(raw_file.read_text(encoding="utf-8"))
            suggestions = raw_output.get("requested_research") if isinstance(raw_output, Mapping) else None
            suggestion_count = len(suggestions) if isinstance(suggestions, list) else 0
        except (OSError, json.JSONDecodeError):
            suggestion_count = None
    structured, metadata, usage_ref = _task_output(
        task_id=task_id, queue=queue, response_store=response_store, root=root,
        envelope=envelope, usage_store=usage_store, research_suggestion_count=suggestion_count,
    )
    checkpoint.event(
        stage,
        "succeeded" if outcome.state == "succeeded" else "blocked",
        task_id=task_id,
        role_id=envelope.role_id,
        task_state=outcome.state,
        error_code=outcome.error_code,
        external_request_started=task.external_request_started,
        response_sha256=metadata.get("response_artifact_sha256") if metadata else None,
        usage_record_ref=usage_ref.get("ref") if usage_ref else None,
        input_tokens=(metadata.get("usage") or {}).get("input_tokens") if metadata else None,
        output_tokens=(metadata.get("usage") or {}).get("output_tokens") if metadata else None,
        total_tokens=(metadata.get("usage") or {}).get("total_tokens") if metadata else None,
        latency_ms=metadata.get("duration_ms") if metadata else None,
    )
    if outcome.state != "succeeded" or structured is None:
        raise RunBlocked(f"{envelope.role_id}_call_{outcome.state}")
    return structured, metadata, usage_ref


def _make_radar_profile(source: Mapping[str, str], source_id: str, *, details: bool = False, tag: str | None = None) -> tuple[SourceProfile, str]:
    if details:
        if tag is None:
            raise ValueError("detail_profile_requires_tag")
        endpoint = f"https://{GITHUB_DOMAIN}/repos/{source['owner']}/{source['repo']}/releases/tags/{quote(tag, safe='')}"
        label = f"{source['owner']}/{source['repo']} release detail"
    else:
        endpoint = f"https://{GITHUB_DOMAIN}/repos/{source['owner']}/{source['repo']}/releases?per_page=5"
        label = source["label"]
    profile = _source_profile(source, endpoint=endpoint, source_id=source_id, label=label)
    return profile, endpoint


def _register_candidate_sources(radar_store: RadarStore) -> tuple[list[SourceProfile], dict[str, dict[str, str]]]:
    profiles: list[SourceProfile] = []
    source_by_id: dict[str, dict[str, str]] = {}
    for source in SOURCE_CANDIDATES:
        profile, endpoint = _make_radar_profile(source, source["source_id"])
        _register_source(radar_store, profile, source["label"], endpoint)
        profiles.append(profile)
        source_by_id[profile.source_id] = dict(source)
    return profiles, source_by_id


def _map_live_items(scan: Any, source_by_id: Mapping[str, Mapping[str, str]], radar_store: RadarStore) -> dict[str, dict[str, Any]]:
    release_rows_by_source: dict[str, list[dict[str, Any]]] = {}
    for fetch in scan.fetches:
        release_rows_by_source[fetch.fetch.source_id] = _release_rows(fetch.fetch.metadata)
    mapped: dict[str, dict[str, Any]] = {}
    for item in scan.batch.items:
        document_refs = [ref for ref in item.get("evidence_refs", []) if isinstance(ref, str) and ref.startswith("radar://document/")]
        docs: list[dict[str, Any]] = []
        for ref in document_refs:
            document_id = _document_id_from_ref(ref)
            document = radar_store.get_row("radar_documents", "document_id", document_id) if document_id else None
            if document:
                docs.append(document)
        if not docs:
            continue
        source_id = str(docs[0].get("source_id"))
        source = source_by_id.get(source_id)
        if source is None:
            continue
        row = next((candidate for candidate in release_rows_by_source.get(source_id, [])
                    if candidate.get("url") == item.get("url") or candidate.get("html_url") == item.get("url")), None)
        if row is None:
            row = next((candidate for candidate in release_rows_by_source.get(source_id, [])
                        if candidate.get("tag_name") == docs[0].get("title")), None)
        if row is None:
            continue
        mapped[item["item_id"]] = {
            "item_id": item["item_id"],
            "url": item["url"],
            "publisher": item["publisher"],
            "published_at": item.get("published_at"),
            "diff": item.get("diff", ""),
            "triage_evidence_refs": list(item.get("evidence_refs", [])),
            "document_ids": [doc["document_id"] for doc in docs],
            "evidence_ids": [f"radar://document/{doc['document_id']}" for doc in docs],
            "source_id": source_id,
            "source": dict(source),
            "release": row,
            "title": str(row.get("name") or row.get("tag_name") or docs[0].get("title") or ""),
            "tag_name": row.get("tag_name"),
            "author": row.get("author") or docs[0].get("byline"),
            "body_excerpt": row.get("body_excerpt"),
            "fetched_at": docs[0].get("fetched_at"),
            "source_snapshot_ids": [
                ref for ref in item.get("evidence_refs", []) if isinstance(ref, str) and ref.startswith("snapshot-")
            ],
        }
    return mapped


def _map_persisted_live_items(
    batch_items: list[Mapping[str, Any]],
    source_by_id: Mapping[str, Mapping[str, str]],
    radar_store: RadarStore,
) -> dict[str, dict[str, Any]]:
    """Rebuild live release candidates from the already persisted Radar batch."""
    mapped: dict[str, dict[str, Any]] = {}
    for item in batch_items:
        document_refs = [ref for ref in item.get("evidence_refs", [])
                         if isinstance(ref, str) and ref.startswith("radar://document/")]
        docs = [radar_store.get_row("radar_documents", "document_id", document_id)
                for ref in document_refs
                if (document_id := _document_id_from_ref(ref))]
        docs = [doc for doc in docs if doc is not None]
        if not docs:
            continue
        document = docs[0]
        source_id = str(document.get("source_id"))
        source = source_by_id.get(source_id)
        origin_url = document.get("origin_url")
        if source is None or not isinstance(origin_url, str):
            continue
        parsed = urlsplit(origin_url)
        marker = "/releases/tag/"
        if (parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.username
                or parsed.password or marker not in parsed.path):
            continue
        tag_name = unquote(parsed.path.split(marker, 1)[1])
        if not tag_name or len(tag_name) > 200 or any(ord(char) < 32 for char in tag_name):
            continue
        release = {
            "name": document.get("title"),
            "tag_name": tag_name,
            "url": document.get("canonical_url"),
            "html_url": origin_url,
            "author": document.get("byline"),
            "published_at": document.get("published_at"),
            "body_excerpt": document.get("summary_snippet"),
        }
        mapped[str(item["item_id"])] = {
            "item_id": str(item["item_id"]),
            "url": str(item.get("url") or origin_url),
            "publisher": str(item.get("publisher") or document.get("publisher") or source["label"]),
            "published_at": item.get("published_at") or document.get("published_at"),
            "diff": item.get("diff", ""),
            "triage_evidence_refs": list(item.get("evidence_refs", [])),
            "document_ids": [str(row["document_id"]) for row in docs],
            "evidence_ids": [f"radar://document/{row['document_id']}" for row in docs],
            "source_id": source_id,
            "source": dict(source),
            "release": release,
            "title": str(release.get("name") or tag_name),
            "tag_name": tag_name,
            "author": release.get("author"),
            "body_excerpt": release.get("body_excerpt"),
            "fetched_at": document.get("fetched_at"),
            "source_snapshot_ids": [],
        }
    return mapped


def _candidate_matches_triage_refs(candidate: Mapping[str, Any], refs: set[str]) -> bool:
    if candidate.get("item_id") in refs:
        return True
    candidate_refs = candidate.get("triage_evidence_refs", [])
    return isinstance(candidate_refs, list) and bool(refs.intersection(
        ref for ref in candidate_refs if isinstance(ref, str)
    ))


def _claim_records_for_candidate(investigator_output: Mapping[str, Any], candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    evidence = set(candidate["evidence_ids"])
    rows: list[dict[str, Any]] = []
    for claim in investigator_output.get("claims", []):
        if not isinstance(claim, Mapping):
            continue
        refs = [item for item in claim.get("evidence_ids", []) if isinstance(item, str)]
        if evidence.intersection(refs):
            rows.append(dict(claim))
    return rows


def _canonicalize_investigator_claim_ids(output: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    normalized = dict(output)
    claims = output.get("claims")
    if not isinstance(claims, list):
        raise RunBlocked("investigator_claims_are_not_a_list")
    mapping: list[dict[str, str]] = []
    normalized_claims: list[dict[str, Any]] = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            raise RunBlocked("investigator_claim_is_not_an_object")
        source_label = claim.get("claim_id")
        evidence_ids = claim.get("evidence_ids")
        epistemic_status = claim.get("epistemic_status")
        canonical_id = canonical_material_claim_id(source_label, evidence_ids, epistemic_status)
        normalized_claim = dict(claim)
        normalized_claim["claim_id"] = canonical_id
        if canonical_id != source_label:
            normalized_claim["source_claim_label"] = source_label
        normalized_claims.append(normalized_claim)
        mapping.append({"claim_index": str(index), "source_claim_label": str(source_label),
                        "canonical_claim_id": canonical_id})
    normalized["claims"] = normalized_claims
    return normalized, mapping


def _recover_completed_investigator_output(
    *, task_id: str, queue: AgentQueue, role_catalog: AgentRoleCatalog,
    response_store: SIWCResponseArtifactStore, root: Path, checkpoint: Checkpoint,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    task = queue.get(task_id)
    task_events = queue.events(task_id) if task is not None else []
    last_task_event = task_events[-1] if task_events else {}
    last_task_detail = last_task_event.get("detail", {})
    if (task is None or task.state != "blocked" or last_task_event.get("action") != "blocked"
            or last_task_detail.get("error_code") != "siwc_result_envelope_invalid"
            or not task.external_request_started or task.attempts != 1 or task.max_attempts != 1):
        raise RunBlocked("persisted_investigator_task_is_not_recoverable")
    envelope = envelope_from_payload(task.payload)
    if envelope.role_id != "evidence_investigator":
        raise RunBlocked("persisted_recovery_task_is_not_the_investigator")
    metadata_path = root / "siwc-role-responses" / f"{task_id}.metadata.json"
    request_path = root / "siwc-role-responses" / f"{task_id}.request.json"
    structured_path = root / "structured-outputs" / f"{task_id}.json"
    if not metadata_path.is_file() or not request_path.is_file() or not structured_path.is_file():
        raise RunBlocked("persisted_investigator_artifacts_are_incomplete")
    metadata = _load_json(metadata_path)
    output_container = _load_json(structured_path)
    request_ref = metadata.get("request_artifact_ref")
    request_digest = metadata.get("request_artifact_sha256")
    response_ref = metadata.get("response_artifact_ref")
    response_digest_expected = metadata.get("response_artifact_sha256")
    if (metadata.get("output_validation") != "result_envelope_rejected"
            or metadata.get("response_completed") is not True or metadata.get("store") is not False
            or metadata.get("stream") is not True or metadata.get("model") != MODEL_ID
            or metadata.get("reasoning_effort") != REASONING_EFFORT
            or not isinstance(request_ref, str) or not isinstance(request_digest, str)
            or not isinstance(response_ref, str) or not isinstance(response_digest_expected, str)):
        raise RunBlocked("investigator_provider_completion_metadata_not_recoverable")
    request_bytes = response_store.read_response(request_ref, request_digest)
    response_bytes = response_store.read_response(response_ref, response_digest_expected)
    request_record = json.loads(request_bytes.decode("utf-8"))
    response_digest = _sha(response_bytes)
    if (response_digest != output_container.get("raw_response_sha256")
            or response_digest != metadata.get("response_sha256")
            or not isinstance(metadata.get("usage"), Mapping)):
        raise RunBlocked("investigator_response_integrity_check_failed")
    raw_output = json.loads(response_bytes.decode("utf-8"))
    if not isinstance(raw_output, Mapping):
        raise RunBlocked("investigator_persisted_response_is_not_an_object")
    prompt_input = request_record.get("prompt_input")
    if not isinstance(prompt_input, Mapping):
        raise RunBlocked("investigator_persisted_request_has_no_controlled_input")
    task_input = prompt_input.get("task_input_data")
    task_input_data = task_input.get("data") if isinstance(task_input, Mapping) else None
    if not isinstance(task_input_data, Mapping) or dict(task_input_data) != task.payload.get("input"):
        raise RunBlocked("investigator_persisted_request_does_not_match_queue_input")
    role_catalog.validate_task(envelope, input_payload=task.payload.get("input"))
    profile = role_catalog.resolve(envelope.role_id, envelope.role_version, envelope.role_hash)
    validate_json_schema(raw_output, profile.output_schema, "$output")
    _validate_output_references(envelope.role_id, prompt_input, raw_output)
    structured_in_request = output_container.get("structured_output")
    if not isinstance(structured_in_request, Mapping) or dict(structured_in_request) != dict(raw_output):
        raise RunBlocked("investigator_structured_output_differs_from_raw_response")

    normalized_output, claim_id_mapping = _canonicalize_investigator_claim_ids(raw_output)
    material_claims = [{
        "claim_id": claim["claim_id"],
        "evidence_ids": list(claim["evidence_ids"]),
        "epistemic_status": claim["epistemic_status"],
    } for claim in normalized_output["claims"]]
    result_mapping = AgentResultEnvelope.from_mapping({
        "schema_version": "1.0",
        "task_id": task_id,
        "status": "completed",
        "output_schema_version": str(profile.output_schema.get("version", profile.output_schema.get("schema_version", "1.0"))),
        "artifact_ref": {"ref": response_ref, "sha256": response_digest},
        "material_claims": material_claims,
        "requested_research": None,
        "open_questions": list(raw_output.get("blockers", [])),
        "observed_constraints": [
            "human_review_required", "publication_state=not_published",
            "siwc_store=false", "siwc_stream=true", "response_completed=true",
        ],
        "input_hash": envelope.input_hash,
        "output_hash": response_digest,
        "created_at": metadata.get("completed_at") or metadata.get("request_started_at"),
        "model_used": metadata.get("model"),
        "model_effort": metadata.get("reasoning_effort"),
        "usage_reported": metadata.get("usage"),
        "next_action_suggestion": "human_review_required",
    }).to_dict()
    role_catalog.validate_result(envelope, result_mapping)
    if not queue.recover_completed_external_output(task_id, result_mapping, response_sha256=response_digest):
        raise RunBlocked("investigator_queue_recovery_transition_rejected")
    normalized_hash = stable_hash(json_dumps(normalized_output))
    _atomic_json(root / "dossier" / "investigator-output-recovery.json", {
        "schema_version": "ENG-CODEX-011-InvestigatorRecovery.v1",
        "task_id": task_id,
        "response_sha256": response_digest,
        "normalized_output_sha256": normalized_hash,
        "claim_id_mapping": claim_id_mapping,
        "normalized_output": normalized_output,
        "transformation": "invalid natural-language claim_id values receive deterministic contract-safe IDs; source labels and raw response remain preserved",
        "provider_calls_repeated": 0,
    })
    checkpoint.event("investigator_output_recovered", "succeeded", task_id=task_id,
                     original_error_code="siwc_result_envelope_invalid", response_sha256=response_digest,
                     normalized_output_sha256=normalized_hash, normalized_claim_count=len(material_claims),
                     provider_calls_repeated=0)
    return normalized_output, dict(metadata), response_digest


def _make_med_policy(source_id: str, source: Mapping[str, str], tag: str, story_revision_id: str, known_evidence_ids: list[str]) -> dict[str, Any]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "story_revision_id": story_revision_id,
        "authorization_ref": "github-issue-41",
        "authorized_domains": [GITHUB_DOMAIN],
        "routes": [{
            "route_id": "selected-github-release-details",
            "question": "What changed in the official release notes for the selected version and tag?",
            "purpose": "Verify the published release details and its official changelog before completing the story.",
            "research_profile_id": "radar.general.v1",
            "research_profile_version": "1.0.0",
            "required_evidence_kinds": ["official_statement"],
            "reason": "Complete the selected public release evidence and verify its stated changes.",
            "intent_terms": ["release", "version", "tag", "official", "changelog", "change log", "changes", "release notes", "published"],
            "allowed_scope": [RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE],
            "preferred_source_ids": [source_id],
            "preferred_domains": [GITHUB_DOMAIN],
            "known_evidence_ids": list(known_evidence_ids),
            "versions_configurations": {"repository": f"{source['owner']}/{source['repo']}", "tag": tag},
        }],
    }


def _create_png(path: Path, title: str, subtitle: str) -> dict[str, Any]:
    """Use a private original ImageGen image when supplied, or draw locally."""
    image_source = os.environ.get("ENGCODEX011_IMAGE_PATH")
    if image_source:
        source_path = Path(image_source).expanduser().resolve(strict=True)
        image_bytes = source_path.read_bytes()
        if len(image_bytes) < 33 or len(image_bytes) > 20_000_000:
            raise RunBlocked("generated_image_size_out_of_bounds")
        if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n") or image_bytes[12:16] != b"IHDR":
            raise RunBlocked("generated_image_is_not_a_png")
        if not image_bytes.endswith(b"\x00\x00\x00\x00IEND\xaeB`\x82"):
            raise RunBlocked("generated_image_png_is_incomplete")
        width, height = struct.unpack(">II", image_bytes[16:24])
        if not (256 <= width <= 8192 and 256 <= height <= 8192):
            raise RunBlocked("generated_image_dimensions_out_of_bounds")
        _write_new(path, image_bytes)
        return {
            "sha256": _sha(image_bytes),
            "bytes": len(image_bytes),
            "width": width,
            "height": height,
            "title_context": title,
            "subtitle_context": subtitle,
            "origin": "openai_imagegen_builtin_original_internal_preview",
            "source_filename": source_path.name,
        }

    width, height = 1200, 680
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            t = x / max(1, width - 1)
            u = y / max(1, height - 1)
            r = int(15 + 24 * t + 10 * (1 - u))
            g = int(27 + 75 * u + 26 * t)
            b = int(54 + 92 * (1 - t) + 50 * u)
            grid = (x % 64 == 0 or y % 64 == 0) and 160 < y < 610
            if grid:
                r, g, b = min(255, r + 12), min(255, g + 20), min(255, b + 25)
            cx, cy = 600, 350
            dx, dy = x - cx, y - cy
            radius = (dx * dx + dy * dy) ** 0.5
            if 135 < radius < 141 or 210 < radius < 216:
                r, g, b = 65, 223, 221
            if 250 < x < 950 and 292 < y < 300 and (x // 40) % 2 == 0:
                r, g, b = 93, 166, 247
            if 250 < x < 950 and 380 < y < 386 and (x // 28) % 2 == 1:
                r, g, b = 183, 137, 252
            if 500 < x < 700 and 285 < y < 395:
                if x in range(500, 507) or x in range(693, 700) or y in range(285, 292) or y in range(388, 395):
                    r, g, b = 218, 240, 255
            rows.extend((r, g, b))
    raw = bytes(rows)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, level=7)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_new(path, png)
    return {
        "sha256": _sha(png),
        "bytes": len(png),
        "width": width,
        "height": height,
        "title_context": title,
        "subtitle_context": subtitle,
        "origin": "original_local_raster_no_third_party_assets",
    }


def _write_usage_summary(root: Path) -> dict[str, Any]:
    usage_dir = root / "agent-usage"
    records = [_load_json(path) for path in sorted(usage_dir.glob("*.json"))]
    summary = aggregate_usage_by_persona(records)
    totals: dict[str, Any] = {}
    for metric in ("input_tokens", "output_tokens", "reasoning_tokens", "total_tokens", "latency_ms"):
        values = [row.get(metric) for row in records if isinstance(row.get(metric), int) and not isinstance(row.get(metric), bool)]
        totals[metric] = {"reported_count": len(values), "sum_reported": sum(values) if values else None}
    value = {
        "schema_version": "ENG-CODEX-011-Usage.v1",
        "source": "SIWC response metadata usage and duration_ms; no token or franchise conversion",
        "calls": records,
        "totals": totals,
        "by_persona": summary,
        "franchise_observation": {"percent": 76, "source": "direction report", "measured_by_provider": False},
        "paid_api_calls": 0,
    }
    _atomic_json(root / "usage-report.json", value)
    return value


def _create_story_package(
    *,
    story_id: str,
    writer_output: Mapping[str, Any],
    evidence_rows: list[dict[str, Any]],
    source_ids: list[str],
    persona_id: str,
    persona_version: str,
    persona_hash: str,
    assignment_profile: AgentRoleProfile,
    reviewer_profile: AgentRoleProfile,
    reviewer_task_id: str,
    reviewer_raw_sha256: str,
    image: Mapping[str, Any],
    title_context: str,
    observed_at: str,
    review_verdict: str,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    editorial_output = role_story_draft_to_editorial_output(
        writer_output,
        evidence_rows=evidence_rows,
        valid_source_ids=set(source_ids),
    )
    # The factory adapter is the boundary between the real StoryDraft and the
    # existing layout contracts. It validates every evidence-to-source link.
    sections: list[dict[str, Any]] = []
    block_index = 0
    for section in writer_output["sections"]:
        evidence_ids = list(section["evidence_ids"])
        mapped_source_ids = []
        for row in evidence_rows:
            if row["evidence_id"] in evidence_ids and row["source_id"] not in mapped_source_ids:
                mapped_source_ids.append(row["source_id"])
        block_index += 1
        sections.append({
            "block_id": f"article-heading-{block_index:02d}",
            "kind": "heading",
            "text": str(section["heading"]),
            "source_ids": mapped_source_ids,
        })
        sections.append({
            "block_id": f"article-paragraph-{block_index:02d}",
            "kind": "paragraph",
            "text": str(section["body"]),
            "source_ids": mapped_source_ids,
        })
        if block_index == 1:
            sections.append({
                "block_id": "article-original-illustration",
                "kind": "figure_request",
                "text": "Ilustração conceitual original para acompanhar a reportagem.",
                "source_ids": [],
                "figures": [{
                    "asset_id": f"asset-{image['sha256'][:24]}",
                    "caption": "Ilustração conceitual original gerada para esta prévia; não retrata um produto ou evento específico.",
                    "alt_text": "Mundo de jogo surgindo de uma malha digital azul e âmbar, ligada a uma placa luminosa.",
                }],
            })
    source_text = "Fontes consultadas: " + "; ".join(
        f"[{item['source_id']}] {item['title']} — {item['url']} (consultado em {item['observed_at']})"
        for item in sources
    )
    sections.append({
        "block_id": "article-source-notes",
        "kind": "paragraph",
        "text": source_text,
        "source_ids": list(dict.fromkeys(source_ids)),
    })
    identity_values = {
        "editor": {
            "role": "editor",
            "profile_id": f"assignment_editor:{assignment_profile.content_hash}",
            "version": assignment_profile.role_version,
            "description": "Editor de pauta executado por agente SIWC real; recomendação sujeita à direção.",
        },
        "writer_persona": {
            "role": "writer_persona",
            "profile_id": f"persona:{persona_id}",
            "version": persona_version,
            "description": f"DNA aprovado de {persona_id}; SHA-256 integral registrado no pacote privado.",
            "persona_hash": persona_hash,
        },
        "reviewer": {
            "role": "reviewer",
            "profile_id": f"editorial_reviewer:{reviewer_profile.content_hash}",
            "version": reviewer_profile.role_version,
            "description": "Revisor editorial executado por agente SIWC real; aprovação humana pendente.",
        },
    }
    payload = {
        "story_id": story_id,
        "edition_id": "eng-codex-011-internal-preview",
        "story_revision": 1,
        "title": str(writer_output["title"]),
        "dek": str(writer_output["dek"]),
        "preview_label": "PRÉVIA INTERNA · REVISÃO HUMANA PENDENTE",
        "preview_note": "Prévia privada para avaliação da direção. Não publicada.",
        "source_ids": list(dict.fromkeys(source_ids)),
        "identities": identity_values,
        "review": {
            "verdict": review_verdict,
            "synthetic_fixture": False,
            "reviewer_profile_id": f"editorial_reviewer@{reviewer_profile.role_version}",
            "reviewer_task_id": reviewer_task_id,
            "review_artifact_sha256": reviewer_raw_sha256,
            "human_approval": "pending",
            "reviewed_story_sha256": "0" * 64,
        },
        "sections": sections,
        "source_manifest": sources,
        "created_at": observed_at,
        "published": False,
        "factory_adapter_output": editorial_output,
    }
    payload["review"]["reviewed_story_sha256"] = story_revision_sha256(payload)
    story = validate_story_package(seal_artifact(story_id, "StoryPackage.v0", 1, payload))
    return story


def _make_media_inventory(story_id: str, image: Mapping[str, Any], image_path: Path) -> dict[str, Any]:
    asset_id = f"asset-{image['sha256'][:24]}"
    payload = {
        "inventory_id": f"media-{story_id}",
        "revision": 1,
        "assets": [{
            "asset_id": asset_id,
            "media_kind": "synthetic_generated",
            "rights_status": "synthetic_fixture",
            "synthetic": True,
            "permitted_modes": ["internal_preview"],
            "description": "Ilustração original gerada para a prévia interna; não representa produto, jogo ou evento específico.",
            "rights_holder": "Geração interna; nenhum ativo de terceiro identificado",
            "origin": image["origin"],
            "asset_sha256": image["sha256"],
            "dimensions": {"width": image["width"], "height": image["height"]},
            "license": {"status": "not_applicable_synthetic_generated", "evidence": None},
            "credit": "Ilustração original gerada para a prévia interna; reutilização em publicação não autorizada.",
            "permitted_transformations": ["resize_for_internal_preview"],
            "linked_block_ids": ["article-original-illustration"],
            "local_path": str(image_path),
        }],
    }
    from .layout.contracts import validate_media_inventory
    return validate_media_inventory(seal_artifact(payload["inventory_id"], "MediaInventory.v0", 1, payload))


def _start_private_preview_server(root: Path, run_id: str) -> dict[str, Any]:
    port_file = root / "preview" / "server-port.json"
    log_file = root / "preview" / "server.log"
    port_file.unlink(missing_ok=True)
    command = [sys.executable, "-m", "motor_editorial.eng_codex_011", "serve", str(root / "preview"), str(port_file)]
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with log_file.open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=REPOSITORY,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if port_file.exists():
            value = _load_json(port_file)
            return {"pid": process.pid, "host": "127.0.0.1", "port": value["port"], "url": f"http://127.0.0.1:{value['port']}/index.html"}
        if process.poll() is not None:
            break
        time.sleep(0.1)
    raise RunBlocked("loopback_preview_server_failed_to_start")


def _serve(preview_root: Path, port_file: Path) -> int:
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    root = preview_root.resolve()
    if not root.is_dir() or not root.is_relative_to(PRIVATE_ROOT.resolve()):
        raise SystemExit("preview_root_outside_private_eng011_root")
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    _atomic_json(port_file, {"host": "127.0.0.1", "port": server.server_address[1], "pid": os.getpid()})
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
    return 0


def run_live_factory(root: Path = PRIVATE_ROOT, *, resume_existing_run: bool = False) -> dict[str, Any]:
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    active_path = root / "active-run.json"
    branch = _ensure_git_branch()
    resume_after_investigator = False
    resume_after_pre_external_writer = False
    if resume_existing_run:
        if not active_path.exists():
            raise RunBlocked("resume_requires_an_existing_blocked_run")
        active = _load_json(active_path)
        if active.get("status") != "blocked" or active.get("branch") != branch:
            raise RunBlocked("resume_run_state_or_branch_mismatch")
        run_id = active.get("run_id")
        if not isinstance(run_id, str) or not run_id.startswith("eng-codex-011-"):
            raise RunBlocked("resume_run_id_invalid")
        run_token = run_id.rsplit("-", 1)[-1]
        checkpoint_state = _load_json(root / "checkpoint.json")
        checkpoint_events = checkpoint_state.get("events", [])
        last_checkpoint_event = checkpoint_events[-1] if isinstance(checkpoint_events, list) and checkpoint_events else {}
        resume_after_investigator = (
            checkpoint_state.get("stage") == "investigator_agent"
            and last_checkpoint_event.get("stage") == "investigator_agent"
            and last_checkpoint_event.get("status") == "blocked"
            and last_checkpoint_event.get("error_code") == "siwc_result_envelope_invalid"
        )
        resume_after_source_registration = (
            active.get("blocker_code") == "RadarStoreError"
            and checkpoint_state.get("stage") == "persona_load"
            and last_checkpoint_event.get("stage") == "persona_load"
            and last_checkpoint_event.get("status") == "succeeded"
        )
        resume_after_writer_guard = (
            active.get("blocker_code") == "existing_writer_task_is_not_a_safe_pre_external_recovery"
            and checkpoint_state.get("stage") == "persona_load"
            and last_checkpoint_event.get("stage") == "persona_load"
            and last_checkpoint_event.get("status") == "succeeded"
        )
        resume_after_pre_external_writer = (
            checkpoint_state.get("stage") == "journalist_original_agent"
            and last_checkpoint_event.get("stage") == "journalist_original_agent"
            and last_checkpoint_event.get("status") == "blocked"
            and last_checkpoint_event.get("error_code") == "agent_contract_invalid"
        ) or resume_after_source_registration or resume_after_writer_guard
        if resume_after_investigator:
            checkpoint = Checkpoint.resume_after_investigator(root, run_id)
        elif resume_after_source_registration:
            checkpoint = Checkpoint.resume_after_source_registration_block(root, run_id)
        elif resume_after_pre_external_writer:
            checkpoint = Checkpoint.resume_after_pre_external_writer_block(root, run_id)
        else:
            checkpoint = Checkpoint.resume_after_triage(root, run_id)
        _atomic_json(active_path, {**active, "status": "running", "updated_at": _now(), "branch": branch})
    else:
        if active_path.exists():
            raise RunBlocked("existing_eng_011_run_prevents_redundant_execution")
        run_token = uuid.uuid4().hex[:12]
        run_id = f"eng-codex-011-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{run_token}"
        checkpoint = Checkpoint(root, run_id)
        _atomic_json(active_path, {"run_id": run_id, "status": "running", "started_at": _now(), "branch": branch})
    usage_store = AgentUsageArtifactStore(root)
    version_archive = StoryVersionArchive(root)
    response_store = SIWCResponseArtifactStore(root)
    role_catalog = load_builtin_role_catalog()
    profiles = _role_profiles(role_catalog)
    client = SIWCClient(CredentialStore())
    if resume_existing_run:
        visible_models = {MODEL_ID}
        if not any(event.get("stage") == "model_preflight" and event.get("status") == "succeeded"
                   and event.get("model") == MODEL_ID for event in checkpoint.state.get("events", [])):
            raise RunBlocked("resume_model_preflight_not_proven_in_prior_run")
    else:
        model_rows = client.models()
        visible_models = {
            str(row.get("slug")) for row in model_rows
            if isinstance(row, Mapping) and row.get("visibility") == "list" and isinstance(row.get("slug"), str)
        }
        checkpoint.event("model_preflight", "succeeded" if MODEL_ID in visible_models else "blocked",
                         model=MODEL_ID if MODEL_ID in visible_models else None, visible_model_count=len(visible_models),
                         api_calls=1, paid_api_calls=0)
    if MODEL_ID not in visible_models:
        raise RunBlocked("gpt_6_luna_not_visible_in_existing_siwc_catalog")

    db_root = root / "ledger"
    db_root.mkdir(parents=True, exist_ok=True)
    app_store = Store(db_root / "motor.sqlite3", db_root / "motor-artifacts")
    queue = AgentQueue(app_store)
    radar_store = RadarStore(db_root / "radar.sqlite3")
    quota_guard = PersistentDomainQuotaGuard(radar_store, quotas={GITHUB_DOMAIN: DAILY_QUOTA}, timezone_name="America/Sao_Paulo")
    connector = RadarConnectorService(domain_quota_guard=quota_guard)
    incremental = IncrementalRadarService(store=radar_store, connector=connector)
    if resume_existing_run:
        source_profiles = []
        source_by_id = {source["source_id"]: dict(source) for source in SOURCE_CANDIDATES}
    else:
        source_profiles, source_by_id = _register_candidate_sources(radar_store)
    provider = GitHubReleaseResearchProvider(radar_store, incremental)
    research_service = ResearchService(store=radar_store, provider=provider)
    router = ResearchResultRouter(
        queue=queue,
        catalog=role_catalog,
        executor_profiles={(SIWC_ROLE_EXECUTOR_PROFILE.profile_id, SIWC_ROLE_EXECUTOR_PROFILE.version): SIWC_ROLE_EXECUTOR_PROFILE},
    )
    dispatcher = TaskDispatcher(
        queue,
        executors={},
        profiles={},
        role_catalog=role_catalog,
        persona_instruction_resolver=lambda envelope: persona_text_cache.get(envelope.persona_id) if envelope.persona_id else None,
        deterministic_task_routes={RADAR_RESEARCH_TASK_TYPE: RADAR_RESEARCH_EXECUTOR_ID},
        result_router=router,
    )
    persona_text_cache: dict[str, str] = {}
    register_siwc_role_executor(
        dispatcher,
        client,
        artifact_root=root,
        model=MODEL_ID,
        reasoning_effort=REASONING_EFFORT,
        catalog_models=visible_models,
    )
    dispatcher.executors[RADAR_RESEARCH_EXECUTOR_ID] = ResearchTaskExecutor(research_service, role_catalog)
    dispatcher.profiles[(RADAR_RESEARCH_PROFILE.profile_id, RADAR_RESEARCH_PROFILE.version)] = RADAR_RESEARCH_PROFILE
    if resume_existing_run:
        public_log = _load_json(root / "public-research-log.json")
        request_rows = public_log.get("requests", [])
        if (public_log.get("mission") != "ENG-CODEX-011" or public_log.get("run_id") != run_id
                or not isinstance(request_rows, list) or len(request_rows) >= TOTAL_REQUEST_BUDGET):
            raise RunBlocked("resume_public_request_budget_or_run_identity_mismatch")
        batch_id = public_log.get("batch_id")
        triage_task_id = f"radar-triage-{batch_id}"
        triage_task = queue.get(triage_task_id)
        if triage_task is None or triage_task.state != "succeeded" or triage_task.attempts != 1:
            raise RunBlocked("resume_requires_one_durable_successful_triage_task")
        request_path = root / "siwc-role-responses" / f"{triage_task_id}.request.json"
        request_payload = _load_json(request_path)
        batch_data = request_payload.get("prompt_input", {}).get("task_input_data", {}).get("data", {})
        if batch_data.get("batch_id") != batch_id or not isinstance(batch_data.get("items"), list):
            raise RunBlocked("resume_triage_input_artifact_mismatch")
        scan = SimpleNamespace(
            batch=SimpleNamespace(
                batch_id=batch_id,
                source_snapshot_ids=public_log.get("batch_source_snapshot_ids", []),
                items=batch_data["items"],
            ),
            triage_task_id=triage_task_id,
            fetches=[],
        )
        observed = [row for row in request_rows if row.get("status") == "observed" and row.get("http_status") == 200]
        if not observed:
            raise RunBlocked("resume_requires_a_successful_live_source_fetch")
        triage_envelope = envelope_from_payload(triage_task.payload)
        role_catalog.validate_result(triage_envelope, triage_task.result)
        output_container = _load_json(root / "structured-outputs" / f"{triage_task_id}.json")
        triage_meta = _load_json(root / "siwc-role-responses" / f"{triage_task_id}.metadata.json")
        response_ref = triage_task.result.get("artifact_ref") if isinstance(triage_task.result, Mapping) else None
        if not isinstance(response_ref, Mapping):
            raise RunBlocked("resume_triage_response_reference_missing")
        response_bytes = response_store.read_response(str(response_ref.get("ref")), str(response_ref.get("sha256")))
        response_digest = _sha(response_bytes)
        if (response_digest != output_container.get("raw_response_sha256")
                or response_digest != triage_meta.get("response_sha256")
                or triage_meta.get("response_completed") is not True
                or triage_meta.get("output_validation") != "role_schema_valid"):
            raise RunBlocked("resume_triage_artifact_integrity_check_failed")
        triage_output = output_container.get("structured_output")
        if not isinstance(triage_output, Mapping):
            raise RunBlocked("resume_triage_output_not_structured")
        checkpoint.event("triage_reused", "succeeded", task_id=triage_task_id,
                         network_requests_reused=len(request_rows), prior_triage_calls=1,
                         repeated_public_requests=0, repeated_siwc_calls=0)
        live_items = _map_persisted_live_items(scan.batch.items, source_by_id, radar_store)
    else:
        checkpoint.event("preflight", "succeeded", model=MODEL_ID, reasoning_effort=REASONING_EFFORT,
                         source_allowlist=[GITHUB_DOMAIN], daily_quota=DAILY_QUOTA, total_requests_max=TOTAL_REQUEST_BUDGET,
                         branch=branch, research_provider="bounded GitHub releases metadata", retries=0)
        radar_service = RadarGeneralService(
            store=radar_store,
            incremental=incremental,
            queue=queue,
            catalog=role_catalog,
            executor_id=SIWC_ROLE_EXECUTOR_ID,
            executor_profile=SIWC_ROLE_EXECUTOR_PROFILE,
        )
        checkpoint.event("radar_scan", "started", sources=[profile.source_id for profile in source_profiles], parallel_requests=1)
        scan = radar_service.scan(
            source_profiles,
            policy=RadarTriagePolicy(relevance_threshold=0.50),
            portfolio=(),
            wait_for_origin_slot=True,
        )
        request_rows = []
        for item in scan.fetches:
            request_rows.append({
                "source_id": item.fetch.source_id,
                "requested_url": item.fetch.requested_url,
                "status": item.fetch.status,
                "http_status": item.fetch.http_status,
                "fetched_at": item.fetch.fetched_at,
                "bytes": item.fetch.payload_bytes,
                "sha256": item.fetch.payload_sha256,
                "documents": len(item.documents),
            })
        _atomic_json(root / "public-research-log.json", {
            "mission": "ENG-CODEX-011",
            "run_id": run_id,
            "authorization_ref": "github-issue-41",
            "robots_provenance": ROBOTS_PROVENANCE,
            "terms_provenance": TERMS_PROVENANCE,
            "requests": request_rows,
            "candidate_count": len(scan.batch.items),
            "batch_id": scan.batch.batch_id,
            "batch_source_snapshot_ids": list(scan.batch.source_snapshot_ids),
        })
        observed = [row for row in request_rows if row["status"] == "observed" and row["http_status"] == 200]
        if not observed or scan.triage_task_id is None:
            raise RunBlocked("radar_found_no_successful_live_candidate_batch")
        checkpoint.event("radar_scan", "succeeded", triage_task_id=scan.triage_task_id,
                         batch_id=scan.batch.batch_id, candidate_count=len(scan.batch.items),
                         network_requests=len(request_rows), successful_sources=len(observed),
                         fetched_at=max((row["fetched_at"] for row in request_rows), default=None))

        triage_output, triage_meta, _ = _dispatch_role(
            dispatcher=dispatcher, queue=queue, task_id=scan.triage_task_id,
            envelope=envelope_from_payload(queue.get(scan.triage_task_id).payload),
            root=root, response_store=response_store, usage_store=usage_store,
            checkpoint=checkpoint, stage="triage_agent",
        )
        live_items = _map_live_items(scan, source_by_id, radar_store)
    decisions = triage_output.get("decisions", []) if isinstance(triage_output, Mapping) else []
    eligible: list[dict[str, Any]] = []
    for decision in decisions:
        if not isinstance(decision, Mapping) or decision.get("suggested_lane") not in EDITOR_HANDOFF_LANES:
            continue
        refs = decision.get("evidence_refs", [])
        if not isinstance(refs, list):
            continue
        decision_refs = {ref for ref in refs if isinstance(ref, str)}
        candidates = [item for item in live_items.values()
                      if _candidate_matches_triage_refs(item, decision_refs)]
        for candidate in candidates:
            eligible.append({**candidate, "triage_decision": dict(decision)})
    unique_eligible = {item["item_id"]: item for item in eligible}
    eligible = list(unique_eligible.values())[:MAX_CANDIDATES_TO_EDITOR]
    if not eligible:
        raise RunBlocked("live_triage_produced_no_editorial_candidate_with_traceable_evidence")
    initial_request_id = "initial-radar-" + stable_hash(run_id)[:24]
    initial_packet, initial_evidence = _build_initial_packet(
        request_id=initial_request_id,
        radar_store=radar_store,
        eligible_candidates=eligible,
    )
    evidence_refs = sorted({
        *[ref for candidate in eligible for ref in candidate["evidence_ids"]],
        *[candidate["item_id"] for candidate in eligible],
    })
    snapshot_ids = sorted({
        str(snapshot_id)
        for candidate in eligible for snapshot_id in candidate.get("source_snapshot_ids", [])
        if snapshot_id
    } | set(scan.batch.source_snapshot_ids))
    investigator_input = {
        "question": "Prepare a concise, traceable dossier for the live Radar candidates. Identify what the public release metadata actually says, distinguish official statements from interpretation, and preserve unresolved factual questions.",
        "evidence_refs": evidence_refs,
        "claim_history": [],
        "search_limits": {
            "allowed_domain": GITHUB_DOMAIN,
            "candidate_count": len(eligible),
            "initial_public_requests": len(request_rows),
            "additional_public_request_limit_per_selected_story": 1,
            "candidate_records": [
                {key: candidate.get(key) for key in ("item_id", "title", "tag_name", "publisher", "author", "published_at", "url", "source_id", "evidence_ids", "triage_decision")}
                for candidate in eligible
            ],
        },
    }
    if resume_after_investigator:
        previous_investigator_event = next((event for event in reversed(checkpoint.state.get("events", []))
                                            if event.get("stage") == "investigator_agent"
                                            and event.get("status") == "blocked"), None)
        investigator_task = previous_investigator_event.get("task_id") if previous_investigator_event else None
        if not isinstance(investigator_task, str):
            raise RunBlocked("resume_investigator_task_id_missing_from_checkpoint")
        existing_investigator_task = queue.get(investigator_task)
        if existing_investigator_task is None or existing_investigator_task.payload.get("input") != investigator_input:
            raise RunBlocked("resume_investigator_input_differs_from_persisted_task")
        investigator_envelope = envelope_from_payload(existing_investigator_task.payload)
        investigator_output, investigator_meta, investigator_response_sha = _recover_completed_investigator_output(
            task_id=investigator_task, queue=queue, role_catalog=role_catalog,
            response_store=response_store, root=root, checkpoint=checkpoint,
        )
        checkpoint.event("investigator_reused", "succeeded", task_id=investigator_task,
                         response_sha256=investigator_response_sha, repeated_siwc_calls=0)
    elif resume_after_pre_external_writer:
        investigator_task = _task_id(run_token, "evidence_investigator", "live-dossier")
        investigator_task_result = queue.get(investigator_task)
        if investigator_task_result is None:
            raise RunBlocked("resume_succeeded_investigator_task_missing")
        investigator_envelope = envelope_from_payload(investigator_task_result.payload)
        raw_investigator_output, investigator_meta, investigator_usage_ref = _load_succeeded_role_output(
            task_id=investigator_task, queue=queue, role_catalog=role_catalog,
            response_store=response_store, root=root,
        )
        recovery_path = root / "dossier" / "investigator-output-recovery.json"
        if not recovery_path.is_file():
            raise RunBlocked("resume_investigator_normalization_artifact_missing")
        recovery = _load_json(recovery_path)
        investigator_response_sha = investigator_meta.get("response_sha256")
        normalized_investigator_output = recovery.get("normalized_output")
        if (recovery.get("response_sha256") != investigator_response_sha
                or not isinstance(normalized_investigator_output, Mapping)
                or stable_hash(json_dumps(dict(normalized_investigator_output))) != recovery.get("normalized_output_sha256")
                or raw_investigator_output.get("claims") is None):
            raise RunBlocked("resume_investigator_normalization_artifact_integrity_failed")
        investigator_output = dict(normalized_investigator_output)
        checkpoint.event("investigator_reused", "succeeded", task_id=investigator_task,
                         response_sha256=investigator_response_sha, usage_receipt_ref=investigator_usage_ref,
                         repeated_siwc_calls=0)
    else:
        investigator_task, investigator_envelope = _new_role_task(
            queue=queue, catalog=role_catalog, profiles=profiles, run_id=run_id,
            run_token=run_token, story_id=f"discovery-{scan.batch.batch_id}",
            role_id="evidence_investigator", stage="live-dossier", input_payload=investigator_input,
            source_snapshot_ids=snapshot_ids, root=root, research_packet=initial_packet,
            dependencies=(scan.triage_task_id,),
        )
        investigator_output, investigator_meta, investigator_usage = _dispatch_role(
            dispatcher=dispatcher, queue=queue, task_id=investigator_task, envelope=investigator_envelope,
            root=root, response_store=response_store, usage_store=usage_store,
            checkpoint=checkpoint, stage="investigator_agent",
        )
        investigator_output, claim_id_mapping = _canonicalize_investigator_claim_ids(investigator_output)
        investigator_task_result = queue.get(investigator_task)
        if investigator_task_result is None or not isinstance(investigator_task_result.result, Mapping):
            raise RunBlocked("investigator_result_not_persisted_after_dispatch")
        investigator_response_ref = investigator_task_result.result.get("artifact_ref")
        if not isinstance(investigator_response_ref, Mapping):
            raise RunBlocked("investigator_response_reference_missing_after_dispatch")
        _atomic_json(root / "dossier" / "investigator-output-normalized.json", {
            "schema_version": "ENG-CODEX-011-InvestigatorNormalization.v1",
            "task_id": investigator_task,
            "response_sha256": investigator_response_ref.get("sha256"),
            "normalized_output_sha256": stable_hash(json_dumps(investigator_output)),
            "claim_id_mapping": claim_id_mapping,
            "normalized_output": investigator_output,
            "provider_calls_repeated": 0,
        })
    _atomic_json(root / "dossier" / "initial-investigation.json", {
        "packet": initial_packet.to_dict(),
        "evidence_records": initial_evidence,
        "investigator_output": investigator_output,
        "candidate_count": len(eligible),
    })
    candidate_dossier: list[dict[str, Any]] = []
    for candidate in eligible:
        candidate_dossier.append({
            "candidate_item_id": candidate["item_id"],
            "title": candidate["title"],
            "tag_name": candidate["tag_name"],
            "publisher": candidate["publisher"],
            "author": candidate["author"],
            "published_at": candidate["published_at"],
            "url": candidate["url"],
            "source_id": candidate["source_id"],
            "evidence_ids": candidate["evidence_ids"],
            "triage": candidate["triage_decision"],
            "claims": _claim_records_for_candidate(investigator_output, candidate),
            "excerpt": candidate.get("body_excerpt"),
        })
    assignment_input = {
        "evidence_dossier": {
            "schema_version": "LiveRadarDossier.v1",
            "candidates": candidate_dossier,
            "evidence": initial_evidence,
            "investigation": investigator_output,
            "research_packet": initial_packet.to_dict(),
        },
        "edition_state": {"edition_id": "eng-codex-011", "current_date": "2026-10-26",
                          "active_story_ids": [], "decision_owner": "direction"},
        "editorial_constraints": {
            "eligible_candidate_ids": [candidate["item_id"] for candidate in eligible],
            "eligible_journalists": PERSONA_LINEAGES,
            "publication_state": "not_published",
            "technical_testing_claims": "prohibited unless evidenced by this dossier",
            "character_rules": "recommend one approved persona; no DNA may be edited",
            "triage_lane_policy": "monitoramento is a real triage outcome, not an automatic rejection or approval; select only if the specific release has a timely reader-relevant angle supported by evidence, and preserve any remaining research need",
        },
        "required_coverage": [
            "Select exactly one candidate_item_id from evidence_dossier.candidates.",
            "Return journalist_persona_id as one of ranzinza, beto-cartucho, nina-prisma, aligned to the supplied editorial lines.",
            "Use claims and questions supported by candidate evidence; do not turn release metadata into independent performance claims.",
            "The journalist writes for readers; internal process metadata stays out of the story.",
        ],
    }
    if resume_after_pre_external_writer:
        assignment_task = _task_id(run_token, "assignment_editor", "live-assignment")
        persisted_assignment = queue.get(assignment_task)
        if persisted_assignment is None:
            raise RunBlocked("resume_assignment_task_missing")
        assignment_envelope = envelope_from_payload(persisted_assignment.payload)
        assignment_output, assignment_meta, assignment_usage_ref = _load_succeeded_role_output(
            task_id=assignment_task, queue=queue, role_catalog=role_catalog,
            response_store=response_store, root=root,
        )
        checkpoint.event("assignment_result_reused", "succeeded", task_id=assignment_task,
                         response_sha256=assignment_meta.get("response_sha256"),
                         usage_receipt_ref=assignment_usage_ref, repeated_siwc_calls=0)
    else:
        assignment_task, assignment_envelope = _new_role_task(
            queue=queue, catalog=role_catalog, profiles=profiles, run_id=run_id,
            run_token=run_token, story_id=f"discovery-{scan.batch.batch_id}",
            role_id="assignment_editor", stage="live-assignment", input_payload=assignment_input,
            source_snapshot_ids=snapshot_ids, root=root,
            dependencies=(investigator_task,),
        )
        assignment_output, _, _ = _dispatch_role(
            dispatcher=dispatcher, queue=queue, task_id=assignment_task, envelope=assignment_envelope,
            root=root, response_store=response_store, usage_store=usage_store,
            checkpoint=checkpoint, stage="assignment_editor_agent",
        )
    candidate_id = assignment_output.get("candidate_item_id")
    persona_id = assignment_output.get("journalist_persona_id")
    selected = next((candidate for candidate in eligible if candidate["item_id"] == candidate_id), None)
    if selected is None or persona_id not in PERSONA_PACKAGES:
        raise RunBlocked("assignment_editor_selected_unknown_live_candidate_or_persona")
    if not selected.get("tag_name"):
        raise RunBlocked("selected_candidate_has_no_release_tag_for_safe_followup")
    story_id = "story-" + stable_hash(f"{run_id}:{candidate_id}")[:24]
    checkpoint.event("editorial_assignment", "succeeded", task_id=assignment_task,
                     selected_candidate_id=candidate_id, selected_title=selected["title"],
                     selected_publisher=selected["publisher"], journalist_persona_id=persona_id,
                     story_id=story_id)

    persona_text, persona_manifest = _load_persona(persona_id, root)
    persona_text_cache[persona_id] = persona_text
    package = PERSONA_PACKAGES[persona_id]
    checkpoint.event("persona_load", "succeeded", persona_id=persona_id,
                     persona_version=package["version"], composite_sha256=persona_manifest["composite_instruction_sha256"],
                     file_count=len(persona_manifest["files"]), character_count=len(persona_text), modified=False)

    detail_source_id = f"github-api-{selected['source']['repo'].casefold()}-detail"
    detail_profile, detail_endpoint = _make_radar_profile(
        selected["source"], detail_source_id, details=True, tag=str(selected["tag_name"])
    )
    _register_source(radar_store, detail_profile, f"{selected['source']['owner']}/{selected['source']['repo']} release detail", detail_endpoint)
    provider.bind(detail_source_id, {
        "owner": selected["source"]["owner"],
        "repo": selected["source"]["repo"],
        "tag_name": selected["tag_name"],
        "profile": detail_profile,
        "selected_candidate_id": candidate_id,
    })
    policy = _make_med_policy(detail_source_id, selected["source"], str(selected["tag_name"]), "story-revision-01", selected["evidence_ids"])
    selected_evidence_rows = [row for row in initial_evidence if row["evidence_id"] in selected["evidence_ids"]]
    writer_evidence_rows = [{key: value for key, value in row.items() if key != "excerpt"}
                            for row in selected_evidence_rows]
    selected_evidence_ids = set(selected["evidence_ids"])
    writer_packet_fields = initial_packet.to_dict()
    writer_packet_fields.pop("content_hash", None)
    writer_packet_fields.update({
        "status": "partial",
        "document_refs": [row for row in writer_packet_fields["document_refs"]
                          if row.get("ref") in selected_evidence_ids],
        "claim_refs": [],
        "source_lineage": [row for row in writer_packet_fields["source_lineage"]
                           if row.get("evidence_id") in selected_evidence_ids],
        "relevant_excerpts_short": [],
        "missing_evidence": ["official_release_details"],
        "constraints": [],
        "fetched_at": _now(),
    })
    writer_initial_packet = ResearchPacket.create(**writer_packet_fields)
    writer_dossier = {
        "schema_version": "EvidenceDossier.v1",
        "candidate": {
            key: selected.get(key)
            for key in ("item_id", "title", "tag_name", "publisher", "author", "published_at", "url", "source_id", "triage_decision")
        },
        "claims": [],
        "evidence": writer_evidence_rows,
        "known_evidence_ids": selected["evidence_ids"],
        "open_questions": list(assignment_output.get("questions", [])),
    }
    editorial_brief = {
        "angle": assignment_output["angle"],
        "genre": assignment_output["genre"],
        "questions": assignment_output["questions"],
        "modules": assignment_output["modules"],
        "gaps": assignment_output["gaps"],
        "needs_more_research": assignment_output["needs_more_research"],
        "selected_candidate_id": candidate_id,
        "selected_journalist_id": persona_id,
    }
    writing_constraints = {
        "voice": "Load and embody the complete approved persona package as supplied in trusted instructions. Do not rewrite or describe the DNA.",
        "reader_facing": True,
        "internal_audit_is_not_article_copy": True,
        "no_system_or_model_limitations_in_prose": True,
        "do_not_claim_unperformed_tests_or_experience": True,
        "source_ids": {row["evidence_id"]: row["source_id"] for row in selected_evidence_rows},
        "citation_style": "cite each factual section with its evidence_ids; source markers are supplied by the Motor during factory adaptation",
        "research_capability": "This dossier has no verified changelog detail yet. Before completing the story, formulate in your own natural language one specific request for the official release details through requested_research.question and requested_research.purpose. The Motor will resolve only the selected repository and tag.",
        "article_scope": "Explain only what this release and its traceable evidence support. Keep factual uncertainty natural and relevant to readers.",
    }
    writer_input = {"editorial_brief": editorial_brief, "evidence_dossier": writer_dossier, "writing_constraints": writing_constraints}
    writer_stage = "original-draft"
    existing_writer_task_id = _task_id(run_token, "persona_writer", writer_stage)
    existing_writer_task = queue.get(existing_writer_task_id)
    if existing_writer_task is not None:
        writer_task = existing_writer_task_id
        writer_envelope = envelope_from_payload(existing_writer_task.payload)
        writer_events = queue.events(existing_writer_task_id)
        last_writer_event = writer_events[-1] if writer_events else {}
        last_writer_detail = last_writer_event.get("detail", {})
        if (existing_writer_task.state != "blocked" or existing_writer_task.external_request_started
                or existing_writer_task.attempts != 1 or existing_writer_task.max_attempts != 1
                or last_writer_event.get("action") != "blocked"
                or last_writer_detail.get("error_code") != "agent_contract_invalid"
                or existing_writer_task.payload.get("input") != writer_input
                or writer_envelope.story_id != story_id
                or writer_envelope.persona_id != persona_id
                or writer_envelope.persona_version != package["version"]
                or writer_envelope.persona_hash != stable_hash(persona_text)
                or writer_envelope.to_dict().get("research_mediation_policy") != policy):
            raise RunBlocked("existing_writer_task_is_not_a_safe_pre_external_recovery")
        persisted_packet = ResearchPacket.from_mapping(existing_writer_task.payload.get("research_packet"))
        role_catalog.prepare_invocation(
            writer_envelope, input_payload=existing_writer_task.payload.get("input"),
            research_packet=persisted_packet, persona_instructions=persona_text,
        )
        if not queue.reopen_pre_external_contract_failure(existing_writer_task_id):
            raise RunBlocked("writer_pre_external_recovery_transition_rejected")
        checkpoint.event("writer_preflight_reopened", "succeeded", task_id=existing_writer_task_id,
                         previous_external_requests=0, next_queue_attempt=2,
                         corrected_contract="preserve_approved_persona_bytes_exactly")
    else:
        writer_task, writer_envelope = _new_role_task(
            queue=queue, catalog=role_catalog, profiles=profiles, run_id=run_id,
            run_token=run_token, story_id=story_id, role_id="persona_writer", stage=writer_stage,
            input_payload=writer_input, source_snapshot_ids=snapshot_ids, root=root,
            research_policy=policy, persona_id=persona_id, persona_version=package["version"], persona_text=persona_text,
            research_packet=writer_initial_packet, dependencies=(assignment_task,),
        )
    writer_original, writer_original_meta, writer_original_usage = _dispatch_role(
        dispatcher=dispatcher, queue=queue, task_id=writer_task, envelope=writer_envelope,
        root=root, response_store=response_store, usage_store=usage_store,
        checkpoint=checkpoint, stage="journalist_original_agent",
    )
    original_task = queue.get(writer_task)
    original_raw_ref = original_task.result["artifact_ref"]
    original_raw = response_store.read_response(original_raw_ref["ref"], original_raw_ref["sha256"])
    original_archive = version_archive.write(
        task=original_task,
        envelope=writer_envelope,
        raw_response=original_raw,
        structured_story=writer_original,
        response_ref=original_raw_ref,
        usage_ref=writer_original_usage,
    )
    checkpoint.event("story_original_archive", "succeeded", task_id=writer_task,
                     version_kind=original_archive["version_kind"], manifest_ref=original_archive["manifest_ref"],
                     full_text_sha256=original_archive["full_text_sha256"])

    parent_result = role_catalog.validate_result(writer_envelope, original_task.result)
    research_request = parent_result.requested_research
    working_output = writer_original
    working_envelope = writer_envelope
    working_task = original_task
    working_meta = writer_original_meta or {}
    working_usage = writer_original_usage
    research_packet: ResearchPacket | None = None
    research_task_id: str | None = None
    research_completed = False
    if research_request is not None:
        request_value = research_request.to_dict()
        _atomic_json(root / "research-flow.json", {
            "request": request_value,
            "origin_task_id": writer_task,
            "origin_role_id": "persona_writer",
            "same_story_id": research_request.story_id == story_id,
            "natural_language_question": research_request.question,
            "converted_by_motor": True,
            "one_request_limit": research_request.max_requests,
            "one_domain_allowlist": list(research_request.preferred_domains),
        })
        research_task = next((task for task in queue.list_tasks(limit=1000) if task.task_type == RADAR_RESEARCH_TASK_TYPE
                              and task.payload.get("research_request", {}).get("request_id") == research_request.request_id), None)
        if research_task is None:
            raise RunBlocked("research_request_was_not_enqueued_by_shared_result_router")
        research_task_id = research_task.task_id
        checkpoint.event("research_request", "enqueued", task_id=research_task_id,
                         request_id=research_request.request_id, parent_task_id=writer_task,
                         story_id=research_request.story_id, story_revision_id=research_request.story_revision_id,
                         natural_language_question=research_request.question,
                         allowed_domains=list(research_request.preferred_domains), max_requests=research_request.max_requests)
        radar_outcome = dispatcher.dispatch_one(research_task_id)
        radar_task_done = queue.get(research_task_id)
        if radar_task_done is None or radar_outcome.state != "succeeded":
            raise RunBlocked("bounded_radar_research_task_did_not_complete")
        radar_result = radar_task_done.result or {}
        research_packet = ResearchPacket.from_mapping(radar_result.get("packet"))
        packet_docs = [item.to_dict() for item in research_packet.document_refs]
        research_completed = research_packet.status == "found" and bool(packet_docs) and not research_packet.missing_evidence
        research_exec = provider.last_execution or {}
        _atomic_json(root / "research-flow.json", {
            "request": request_value,
            "research_task_id": research_task_id,
            "request_id": research_request.request_id,
            "origin_task_id": writer_task,
            "continuation_same_story": research_packet.request_id == research_request.request_id and research_request.story_id == story_id,
            "question": research_request.question,
            "packet": research_packet.to_dict(),
            "provider_execution": research_exec,
            "research_service_result": radar_result,
            "status": "completed" if research_completed else "partial_or_blocked",
        })
        checkpoint.event("research_provider", "succeeded" if research_completed else "blocked",
                         task_id=research_task_id, request_id=research_request.request_id,
                         packet_id=radar_result.get("packet_id"), packet_status=research_packet.status,
                         returned_documents=len(packet_docs), returned_claims=len(research_packet.claim_refs),
                         provider_called=radar_result.get("provider_called"),
                         public_request=research_exec.get("endpoint"), http_status=research_exec.get("http_status"),
                         response_bytes=research_exec.get("payload_bytes"), response_sha256=research_exec.get("payload_sha256"))
        if research_completed:
            continuation = next((task for task in queue.list_tasks(limit=1000)
                                 if task.task_type == "agent.role.persona_writer"
                                 and task.payload.get("research_packet", {}).get("request_id") == research_request.request_id), None)
            if continuation is None:
                raise RunBlocked("research_packet_was_not_returned_to_same_journalist")
            working_task = continuation
            working_envelope = envelope_from_payload(continuation.payload)
            working_output, working_meta, working_usage = _dispatch_role(
                dispatcher=dispatcher, queue=queue, task_id=continuation.task_id, envelope=working_envelope,
                root=root, response_store=response_store, usage_store=usage_store,
                checkpoint=checkpoint, stage="journalist_research_continuation_agent",
            )
            continuation_raw_ref = working_task.result["artifact_ref"]
            continuation_raw = response_store.read_response(continuation_raw_ref["ref"], continuation_raw_ref["sha256"])
            continuation_archive = version_archive.write(
                task=working_task, envelope=working_envelope, raw_response=continuation_raw,
                structured_story=working_output, response_ref=continuation_raw_ref, usage_ref=working_usage,
            )
            checkpoint.event("story_research_revision_archive", "succeeded", task_id=working_task.task_id,
                             version_kind=continuation_archive["version_kind"],
                             manifest_ref=continuation_archive["manifest_ref"],
                             full_text_sha256=continuation_archive["full_text_sha256"])
    else:
        checkpoint.event("research_request", "blocked", task_id=writer_task,
                         reason="journalist_did_not_request_complementary_research")

    final_dossier = dict(writer_dossier)
    final_evidence_rows = list(selected_evidence_rows)
    final_source_ids = list(dict.fromkeys(row["source_id"] for row in final_evidence_rows))
    final_sources = [
        {"source_id": row["source_id"], "title": row["title"], "url": row["source_url"],
         "observed_at": row["observed_at"], "published_at": row["published_at"], "author": row["author"]}
        for row in final_evidence_rows
    ]
    if research_packet is not None and research_completed:
        for document_ref in research_packet.document_refs:
            document_id = _document_id_from_ref(document_ref.ref)
            document = radar_store.get_row("radar_documents", "document_id", document_id) if document_id else None
            if not document:
                continue
            source_id = str(document.get("source_id"))
            source_label = f"S{len(final_source_ids) + 1}"
            if source_id not in final_source_ids:
                final_source_ids.append(source_id)
            final_evidence_rows.append({
                "evidence_id": document_ref.ref,
                "source_id": source_id,
                "source_document_id": document_id,
                "source_url": _source_display_url(document),
                "canonical_source_url": document.get("canonical_url"),
                "title": document.get("title"),
                "publisher": document.get("publisher"),
                "author": document.get("byline"),
                "published_at": document.get("published_at"),
                "observed_at": document.get("fetched_at"),
                "epistemic_status": "official_statement",
                "excerpt": research_packet.relevant_excerpts_short[0] if research_packet.relevant_excerpts_short else None,
            })
            final_sources.append({
                "source_id": source_label,
                "radar_source_id": source_id,
                "title": document.get("title"),
                "url": _source_display_url(document),
                "canonical_url": document.get("canonical_url"),
                "observed_at": document.get("fetched_at"),
                "published_at": document.get("published_at"),
                "author": document.get("byline"),
            })
        final_dossier["research_return"] = research_packet.to_dict()
        final_dossier["evidence"] = final_evidence_rows
        final_dossier["claims"] = list(final_dossier.get("claims", [])) + [
            {"claim_id": claim_id, "evidence_ids": [item.ref for item in research_packet.document_refs],
             "epistemic_status": "official_statement", "statement": excerpt}
            for claim_id, excerpt in zip(research_packet.claim_refs, research_packet.relevant_excerpts_short)
        ]
    valid_source_ids = list(dict.fromkeys(final_source_ids))
    if not valid_source_ids:
        raise RunBlocked("final_story_has_no_source_evidence")

    body_for_checks = "\n".join(
        [str(working_output.get("title", "")), str(working_output.get("dek", ""))]
        + [str(section.get("body", "")) for section in working_output.get("sections", []) if isinstance(section, Mapping)]
    )
    leaked_markers = [marker for marker in INTERNAL_LEAK_MARKERS if marker.casefold() in body_for_checks.casefold()]
    story_text = StoryVersionArchive._render(working_output)
    draft_hash = stable_hash(story_text)
    fact_checker_input = {
        "draft": story_text,
        "draft_hash": draft_hash,
        "evidence_dossier": final_dossier,
        "editorial_policy": {
            "require_claim_evidence": True,
            "distinguish_official_statement_from_independent_measurement": True,
            "no_unperformed_testing": True,
            "no_internal_audit_language_in_reader_copy": True,
            "publication_state": "not_published",
        },
    }
    fact_task, fact_envelope = _new_role_task(
        queue=queue, catalog=role_catalog, profiles=profiles, run_id=run_id,
        run_token=run_token, story_id=story_id, role_id="fact_checker", stage="fact-check-original",
        input_payload=fact_checker_input, source_snapshot_ids=snapshot_ids, root=root,
        dependencies=(working_task.task_id,),
    )
    fact_output, _, fact_usage = _dispatch_role(
        dispatcher=dispatcher, queue=queue, task_id=fact_task, envelope=fact_envelope,
        root=root, response_store=response_store, usage_store=usage_store,
        checkpoint=checkpoint, stage="fact_checker_agent",
    )

    current_writer_output = working_output
    current_writer_task = working_task
    current_writer_envelope = working_envelope
    current_writer_meta = working_meta
    current_writer_usage = working_usage
    current_fact_output = fact_output
    current_fact_task_id = fact_task
    correction_needed = fact_output.get("status") in {"revise", "hold"} or bool(leaked_markers)
    if correction_needed:
        revision_id = "story-revision-02"
        revised_policy = _make_med_policy(detail_source_id, selected["source"], str(selected["tag_name"]), revision_id, selected["evidence_ids"])
        revision_input = {
            "editorial_brief": editorial_brief,
            "evidence_dossier": final_dossier,
            "writing_constraints": {
                **writing_constraints,
                "revision_request": "Correct the attached fact-check and remove any internal process language while preserving supported facts, full article structure and the approved character voice.",
                "fact_check_findings": fact_output.get("findings", []),
                "internal_language_findings": leaked_markers,
                "prior_draft": story_text,
                "research_cycle_already_used": research_completed,
            },
        }
        revision_task, revision_envelope = _new_role_task(
            queue=queue, catalog=role_catalog, profiles=profiles, run_id=run_id,
            run_token=run_token, story_id=story_id, role_id="persona_writer", stage="editorial-revision-02",
            input_payload=revision_input, source_snapshot_ids=snapshot_ids, root=root,
            research_policy=revised_policy, persona_id=persona_id, persona_version=package["version"], persona_text=persona_text,
            research_packet=research_packet or initial_packet,
            dependencies=(fact_task,),
        )
        revised_output, revised_meta, revised_usage = _dispatch_role(
            dispatcher=dispatcher, queue=queue, task_id=revision_task, envelope=revision_envelope,
            root=root, response_store=response_store, usage_store=usage_store,
            checkpoint=checkpoint, stage="journalist_correction_agent",
        )
        revised_task = queue.get(revision_task)
        revised_ref = revised_task.result["artifact_ref"]
        revised_raw = response_store.read_response(revised_ref["ref"], revised_ref["sha256"])
        revised_archive = version_archive.write(
            task=revised_task, envelope=revision_envelope, raw_response=revised_raw,
            structured_story=revised_output, response_ref=revised_ref, usage_ref=revised_usage,
        )
        checkpoint.event("story_correction_archive", "succeeded", task_id=revision_task,
                         version_kind=revised_archive["version_kind"], manifest_ref=revised_archive["manifest_ref"],
                         full_text_sha256=revised_archive["full_text_sha256"])
        revised_text = StoryVersionArchive._render(revised_output)
        revised_fact_input = {**fact_checker_input, "draft": revised_text, "draft_hash": stable_hash(revised_text),
                              "evidence_dossier": final_dossier}
        revised_fact_task, revised_fact_envelope = _new_role_task(
            queue=queue, catalog=role_catalog, profiles=profiles, run_id=run_id,
            run_token=run_token, story_id=story_id, role_id="fact_checker", stage="fact-check-revision-02",
            input_payload=revised_fact_input, source_snapshot_ids=snapshot_ids, root=root,
            dependencies=(revision_task,),
        )
        revised_fact, _, _ = _dispatch_role(
            dispatcher=dispatcher, queue=queue, task_id=revised_fact_task, envelope=revised_fact_envelope,
            root=root, response_store=response_store, usage_store=usage_store,
            checkpoint=checkpoint, stage="fact_checker_revision_agent",
        )
        current_writer_output = revised_output
        current_writer_task = revised_task
        current_writer_envelope = revision_envelope
        current_writer_meta = revised_meta
        current_writer_usage = revised_usage
        current_fact_output = revised_fact
        current_fact_task_id = revised_fact_task
        story_text = revised_text
        draft_hash = stable_hash(story_text)
        body_for_checks = "\n".join([str(current_writer_output.get("title", "")), str(current_writer_output.get("dek", ""))]
                                     + [str(s.get("body", "")) for s in current_writer_output.get("sections", []) if isinstance(s, Mapping)])
        leaked_markers = [marker for marker in INTERNAL_LEAK_MARKERS if marker.casefold() in body_for_checks.casefold()]

    reviewer_input = {
        "draft": story_text,
        "draft_hash": draft_hash,
        "fact_check_verdict": current_fact_output,
        "editorial_brief": editorial_brief,
        "persona_ref": {
            "id": persona_id,
            "version": package["version"],
            "sha256": persona_manifest["composite_instruction_sha256"],
            "source_commit": package["ref"],
            "identity_line": PERSONA_LINEAGES[persona_id],
        },
    }
    reviewer_task, reviewer_envelope = _new_role_task(
        queue=queue, catalog=role_catalog, profiles=profiles, run_id=run_id,
        run_token=run_token, story_id=story_id, role_id="editorial_reviewer", stage="editorial-review",
        input_payload=reviewer_input, source_snapshot_ids=snapshot_ids, root=root,
        dependencies=(current_fact_task_id,),
    )
    reviewer_output, _, _ = _dispatch_role(
        dispatcher=dispatcher, queue=queue, task_id=reviewer_task, envelope=reviewer_envelope,
        root=root, response_store=response_store, usage_store=usage_store,
        checkpoint=checkpoint, stage="editorial_reviewer_agent",
    )
    reviewer_task_row = queue.get(reviewer_task)
    reviewer_ref = reviewer_task_row.result["artifact_ref"]
    reviewer_raw = response_store.read_response(reviewer_ref["ref"], reviewer_ref["sha256"])
    human_editorial_approval = "pending"
    final_integrity_ok = (
        research_completed
        and current_fact_output.get("status") == "pass"
        and reviewer_output.get("verdict") == "pass"
        and reviewer_output.get("human_review_required") is True
        and not leaked_markers
    )

    # Render the final real StoryDraft through the factory adapter and the
    # existing layout contract; references are metadata-only design aids.
    image_path = root / "preview" / "assets" / "illustration.png"
    image = _create_png(image_path, str(current_writer_output["title"]), str(selected["title"]))
    image_path.rename(image_path.with_name(f"{image['sha256']}.png"))
    image_path = image_path.with_name(f"{image['sha256']}.png")
    story_package = _create_story_package(
        story_id=story_id,
        writer_output=current_writer_output,
        evidence_rows=final_evidence_rows,
        source_ids=valid_source_ids,
        persona_id=persona_id,
        persona_version=package["version"],
        persona_hash=persona_manifest["composite_instruction_sha256"],
        assignment_profile=profiles["assignment_editor"],
        reviewer_profile=profiles["editorial_reviewer"],
        reviewer_task_id=reviewer_task,
        reviewer_raw_sha256=_sha(reviewer_raw),
        image=image,
        title_context=str(current_writer_output["title"]),
        observed_at=_now(),
        review_verdict=str(reviewer_output.get("verdict")),
        sources=final_sources,
    )
    media_inventory = _make_media_inventory(story_id, image, image_path)
    layout_fixture = _read_fixture()
    reference_index = LayoutReferenceIndex(db_root / "layout-reference-index.sqlite3")
    reference_index.add_references(_materialize_references(layout_fixture["references"]))
    reference_sha = reference_index.fingerprint()
    needs = build_visual_needs(story_package)
    references = reference_index.search(
        [tag for need in needs["needs"] for tag in need["tags"]], limit=3,
    )
    if len(references) != 3:
        raise RunBlocked("layout_reference_index_did_not_return_three_metadata_records")
    layout_plan = plan_layout(story_package, media_inventory, needs, references, reference_sha)
    validation = validate_composition_validation(validate_plan(
        story_package, media_inventory, layout_plan, reference_sha, reference_index.references(),
    ))
    if validation["payload"]["status"] != "PASS":
        raise RunBlocked("real_story_layout_validation_failed")
    asset_id = media_inventory["payload"]["assets"][0]["asset_id"]
    asset_url = f"assets/{image['sha256']}.png"
    preview_html = render_preview(story_package, layout_plan, validation, {asset_id: asset_url})
    preview_check = validate_rendered_preview(story_package, layout_plan, validation, preview_html, {asset_id: asset_url})
    preview_path = root / "preview" / "index.html"
    _write_new(preview_path, preview_html.encode("utf-8"))
    _atomic_json(root / "render-evidence.json", {
        "story_id": story_id,
        "story_revision_sha256": story_revision_sha256(story_package["payload"]),
        "layout_plan_sha256": layout_plan["content_sha256"],
        "layout_validation_sha256": validation["content_sha256"],
        "rendered_preview_validation": preview_check,
        "image": {**image, "path": str(image_path), "asset_id": asset_id, "asset_url": asset_url},
        "published": False,
        "human_approval": human_editorial_approval,
    })
    server = _start_private_preview_server(root, run_id)
    checkpoint.event("preview_server", "started", **server, bind_address="127.0.0.1", public_network_exposure=False)

    usage_report = _write_usage_summary(root)
    archive_index = version_archive.directory / hashlib.sha256(story_id.encode("utf-8")).hexdigest()[:32] / "INDEX.json"
    report = {
        "mission": "ENG-CODEX-011",
        "run_id": run_id,
        "status": "awaiting_browser_visual_verification" if final_integrity_ok else "blocked_or_partial",
        "branch": branch,
        "source_batch_id": scan.batch.batch_id,
        "selected_candidate_id": candidate_id,
        "selected_candidate_title": selected["title"],
        "selected_journalist": persona_id,
        "story_id": story_id,
        "story_versions_index": str(archive_index),
        "research_request_id": research_request.request_id if research_request else None,
        "research_task_id": research_task_id,
        "research_completed": research_completed,
        "fact_check_status": current_fact_output.get("status"),
        "editorial_review_verdict": reviewer_output.get("verdict"),
        "human_approval": human_editorial_approval,
        "internal_language_markers_remaining": leaked_markers,
        "preview_url": server["url"],
        "preview_validation": preview_check,
        "usage_report": str(root / "usage-report.json"),
        "usage_total_tokens": usage_report["totals"]["total_tokens"],
        "franchise_observation_percent": 76,
        "paid_api_calls": 0,
        "published": False,
        "deployed": False,
        "merged": False,
        "browser_visual_verification": "pending",
    }
    _atomic_json(root / "run-report.json", report)
    checkpoint.state["status"] = report["status"]
    checkpoint.event("deterministic_preview", "succeeded", preview_url=server["url"],
                     preview_path=str(preview_path), image_sha256=image["sha256"],
                     story_revision_sha256=story_revision_sha256(story_package["payload"]),
                     layout_validation_status=validation["payload"]["status"],
                     human_approval="pending", published=False)
    _atomic_json(active_path, {"run_id": run_id, "status": report["status"], "started_at": checkpoint.state["started_at"], "updated_at": _now(), "branch": branch})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m motor_editorial.eng_codex_011")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="execute one authorized ENG-011 live newsroom proof")
    run_parser.add_argument("--image-path", type=Path, help="private original PNG for the internal preview")
    resume_parser = subparsers.add_parser("resume", help="resume after the persisted successful Radar triage without repeating it")
    resume_parser.add_argument("--image-path", type=Path, help="private original PNG for the internal preview")
    serve = subparsers.add_parser("serve", help=argparse.SUPPRESS)
    serve.add_argument("preview_root", type=Path)
    serve.add_argument("port_file", type=Path)
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args.preview_root, args.port_file)
    try:
        if args.image_path is not None:
            os.environ["ENGCODEX011_IMAGE_PATH"] = str(args.image_path.expanduser().resolve())
        report = run_live_factory(resume_existing_run=args.command == "resume")
    except RunBlocked as error:
        root = PRIVATE_ROOT.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        active_path = root / "active-run.json"
        active = _load_json(active_path) if active_path.exists() else {"run_id": None, "started_at": _now()}
        active.update({"status": "blocked", "blocker_code": error.code, "updated_at": _now()})
        _atomic_json(active_path, active)
        print(json.dumps({"status": "BLOQUEADO", "code": error.code, "evidence_root": str(root)}, ensure_ascii=False))
        return 2
    except Exception as error:
        root = PRIVATE_ROOT.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        active_path = root / "active-run.json"
        active = _load_json(active_path) if active_path.exists() else {"run_id": None, "started_at": _now()}
        active.update({"status": "blocked", "blocker_code": type(error).__name__, "updated_at": _now()})
        _atomic_json(active_path, active)
        print(json.dumps({"status": "BLOQUEADO", "code": type(error).__name__, "evidence_root": str(root)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
