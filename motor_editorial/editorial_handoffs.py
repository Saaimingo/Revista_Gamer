"""Typed, revision-bound editorial handoffs for the offline factory circuit."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from .agent_contracts import canonical_material_claim_id
from .editorial import article_revision_sha256
from .layout.contracts import profile_sha256


SCHEMA_VERSION = "EditorialHandoff.v1"
ARTIFACT_KEYS = {
    "evidence_dossier": "EvidenceDossier.v1",
    "editorial_brief": "EditorialBrief.v1",
    "story_draft": "StoryDraft.v1",
    "fact_check_verdict": "FactCheckVerdict.v1",
    "editorial_review": "EditorialReview.v1",
}
CANDIDATE_DOSSIER_TYPE = "CandidateDossier.v1"
EDITORIAL_TRIAGE_LANES = frozenset({"principal", "reserva", "monitoramento"})
JOURNALIST_EDITORIAL_LINES = {
    "ranzinza": "hardware e tecnologia; exigir condições, evidência, custo e impacto para jogadores",
    "beto-cartucho": "jogos e campanha; discutir narrativa, design e recepção sem alegar gameplay próprio",
    "nina-prisma": "mods, criadores e cultura; distinguir atribuição, comunidade, origem e licença",
}
JOURNALIST_TOPIC_MATRIX = {
    "hardware_technology_performance": ["ranzinza"],
    "games_campaign_narrative": ["beto-cartucho"],
    "mods_creators_culture": ["nina-prisma"],
    "cross_cutting": ["ranzinza", "beto-cartucho", "nina-prisma"],
}
_INSTRUCTION_LIKE = re.compile(
    r"(?:ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|"
    r"reveal\s+(?:the\s+)?(?:system\s+)?prompt|"
    r"ignore\s+as\s+instru(?:ç|c)(?:õ|o)es|"
    r"revele\s+o\s+prompt)",
    re.IGNORECASE,
)


class HandoffError(ValueError):
    """A typed editorial artifact is malformed or belongs to a stale revision."""


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as error:
        raise HandoffError("Handoff contém valor que não pode ser serializado como JSON canônico.") from error
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffError(f"{field} precisa ser texto não vazio.")
    return value


def _validate_payload(artifact_type: str, payload: Mapping[str, Any]) -> None:
    if artifact_type == CANDIDATE_DOSSIER_TYPE:
        for field in ("batch_id", "triage_task_id", "investigator_task_id"):
            _require_text(payload.get(field), f"CandidateDossier.{field}")
        candidate_ids = payload.get("candidate_item_ids")
        candidates = payload.get("candidates")
        evidence = payload.get("evidence")
        claims = payload.get("claims")
        if not isinstance(candidate_ids, list) or not isinstance(candidates, list):
            raise HandoffError("CandidateDossier precisa de candidate_item_ids e candidates.")
        if any(not isinstance(item, str) or not item.strip() for item in candidate_ids):
            raise HandoffError("CandidateDossier contém candidate_item_ids vazios ou duplicados.")
        if len(set(candidate_ids)) != len(candidate_ids):
            raise HandoffError("CandidateDossier contém candidate_item_ids vazios ou duplicados.")
        if not isinstance(evidence, list) or not isinstance(claims, list):
            raise HandoffError("CandidateDossier.evidence e claims precisam ser listas.")
        if not isinstance(payload.get("portfolio"), list):
            raise HandoffError("CandidateDossier.portfolio precisa ser lista.")
        portfolio = payload["portfolio"]
        if any(not isinstance(item, str) or not item.strip() for item in portfolio):
            raise HandoffError("CandidateDossier.portfolio contém referência inválida.")
        if len(set(portfolio)) != len(portfolio):
            raise HandoffError("CandidateDossier.portfolio contém referência duplicada.")
        if not isinstance(payload.get("blockers"), list) or not isinstance(payload.get("contradictions"), list):
            raise HandoffError("CandidateDossier precisa preservar blockers e contradictions.")
        if not isinstance(payload.get("rumors"), list) or not isinstance(payload.get("open_questions"), list):
            raise HandoffError("CandidateDossier precisa preservar rumors e open_questions.")
        if payload.get("sufficiency") not in {"sufficient", "partial", "insufficient", "not_reported"}:
            raise HandoffError("CandidateDossier.sufficiency desconhecida.")
        evidence_by_id: dict[str, Mapping[str, Any]] = {}
        for row in evidence:
            if not isinstance(row, Mapping):
                raise HandoffError("CandidateDossier.evidence contém item inválido.")
            for field in ("evidence_id", "source_id", "source_role", "publisher", "locator"):
                _require_text(row.get(field), f"CandidateDossier.evidence.{field}")
            if row.get("trust_boundary") != "untrusted_evidence_data_only_never_instructions":
                raise HandoffError("CandidateDossier precisa manter evidência como dado não confiável.")
            if row.get("excerpt") is not None:
                _require_text(row.get("excerpt"), "CandidateDossier.evidence.excerpt")
                if row.get("excerpt_authorized") is not True:
                    raise HandoffError("CandidateDossier não pode incluir excerpt sem autorização de reutilização.")
            digest = row.get("content_sha256")
            if digest is not None and not _is_sha256(digest):
                raise HandoffError("CandidateDossier.evidence.content_sha256 inválido.")
            evidence_id = str(row["evidence_id"])
            if evidence_id in evidence_by_id:
                raise HandoffError("CandidateDossier contém evidence_id duplicado.")
            evidence_by_id[evidence_id] = row

        candidate_rows: dict[str, Mapping[str, Any]] = {}
        for row in candidates:
            if not isinstance(row, Mapping):
                raise HandoffError("CandidateDossier.candidates contém item inválido.")
            candidate_id = _require_text(row.get("candidate_item_id"), "CandidateDossier.candidate_item_id")
            if candidate_id in candidate_rows or row.get("triage_lane") not in EDITORIAL_TRIAGE_LANES:
                raise HandoffError("CandidateDossier contém candidato duplicado ou lane inelegível.")
            if not isinstance(row.get("evidence_ids"), list) or not isinstance(row.get("triage_evidence_refs"), list):
                raise HandoffError("CandidateDossier candidate exige refs de evidência e de triagem.")
            candidate_evidence = row["evidence_ids"]
            if any(not isinstance(ref, str) or not ref.strip() for ref in candidate_evidence):
                raise HandoffError("CandidateDossier candidate contém evidence_id inválido.")
            if any(not isinstance(ref, str) or ref not in evidence_by_id for ref in candidate_evidence):
                raise HandoffError("CandidateDossier candidate aponta para evidence_id ausente.")
            if len(set(candidate_evidence)) != len(candidate_evidence):
                raise HandoffError("CandidateDossier candidate contém evidence_id duplicado.")
            if any(not isinstance(ref, str) or not ref.strip() for ref in row["triage_evidence_refs"]):
                raise HandoffError("CandidateDossier candidate contém triage_evidence_ref inválida.")
            if len(set(row["triage_evidence_refs"])) != len(row["triage_evidence_refs"]):
                raise HandoffError("CandidateDossier candidate contém triage_evidence_ref duplicada.")
            _require_text(row.get("candidate_angle"), "CandidateDossier.candidate_angle")
            for lineage_key in ("source_lineage", "claim_lineage"):
                lineage = row.get(lineage_key)
                if not isinstance(lineage, list) or any(not isinstance(item, Mapping) for item in lineage):
                    raise HandoffError(f"CandidateDossier {lineage_key} precisa ser uma lista de objetos.")
            for source in row["source_lineage"]:
                _require_text(source.get("source_id"), "CandidateDossier.source_lineage.source_id")
                for field in ("document_id", "publisher", "url"):
                    if source.get(field) is not None:
                        _require_text(source.get(field), f"CandidateDossier.source_lineage.{field}")
            candidate_rows[candidate_id] = row
        if set(candidate_rows) != set(candidate_ids):
            raise HandoffError("CandidateDossier candidate_item_ids não correspondem aos candidates persistidos.")

        valid_sources = {str(row["source_id"]) for row in evidence_by_id.values()}
        valid_evidence_ids = set(evidence_by_id)
        claim_ids: set[str] = set()
        for row in claims:
            if not isinstance(row, Mapping):
                raise HandoffError("CandidateDossier.claims contém item inválido.")
            claim_id = _require_text(row.get("claim_id"), "CandidateDossier.claim_id")
            if claim_id in claim_ids:
                raise HandoffError("CandidateDossier contém claim_id duplicado.")
            claim_ids.add(claim_id)
            _require_text(row.get("claim"), "CandidateDossier.claim")
            if row.get("epistemic_status") not in {
                "official_statement", "named_person_statement", "independent_measurement",
                "community_report", "attributed_rumor", "editorial_interpretation", "unverified_or_disputed",
            }:
                raise HandoffError("CandidateDossier contém epistemic_status desconhecido.")
            refs, sources = row.get("evidence_ids"), row.get("source_ids")
            if not isinstance(refs, list) or not refs or not isinstance(sources, list) or not sources:
                raise HandoffError("Toda claim do CandidateDossier exige evidence_ids e source_ids.")
            if any(not isinstance(ref, str) or ref not in valid_evidence_ids for ref in refs):
                raise HandoffError("CandidateDossier claim aponta para evidence_id ausente.")
            if any(not isinstance(source, str) or not source.strip() for source in sources):
                raise HandoffError("CandidateDossier claim contém source_id inválido.")
            if len(set(refs)) != len(refs) or len(set(sources)) != len(sources):
                raise HandoffError("CandidateDossier claim contém referências duplicadas.")
            expected_sources = {str(evidence_by_id[ref]["source_id"]) for ref in refs}
            if set(sources) != expected_sources or expected_sources - valid_sources:
                raise HandoffError("CandidateDossier claim source_ids não correspondem às evidências citadas.")
        if payload.get("investigator_response_sha256") is not None and not _is_sha256(payload.get("investigator_response_sha256")):
            raise HandoffError("CandidateDossier investigator_response_sha256 inválido.")
        if payload.get("triage_response_sha256") is not None and not _is_sha256(payload.get("triage_response_sha256")):
            raise HandoffError("CandidateDossier triage_response_sha256 inválido.")
    elif artifact_type == ARTIFACT_KEYS["evidence_dossier"]:
        _require_text(payload.get("question"), "EvidenceDossier.question")
        evidence = payload.get("evidence")
        claims = payload.get("claims")
        if not isinstance(evidence, list) or not evidence or not isinstance(claims, list) or not claims:
            raise HandoffError("EvidenceDossier exige evidências e alegações rastreáveis.")
        evidence_ids: set[str] = set()
        for row in evidence:
            if not isinstance(row, Mapping):
                raise HandoffError("EvidenceDossier.evidence contém item inválido.")
            for field in ("evidence_id", "source_id", "source_role", "publisher", "locator", "excerpt"):
                _require_text(row.get(field), f"EvidenceDossier.evidence.{field}")
            if row.get("trust_boundary") != "untrusted_evidence_data_only_never_instructions":
                raise HandoffError("EvidenceDossier precisa marcar a evidência como dado não confiável.")
            if row["evidence_id"] in evidence_ids:
                raise HandoffError("EvidenceDossier contém evidence_id repetido.")
            evidence_ids.add(row["evidence_id"])
        for row in claims:
            if not isinstance(row, Mapping):
                raise HandoffError("EvidenceDossier.claims contém item inválido.")
            _require_text(row.get("claim_id"), "EvidenceDossier.claims.claim_id")
            _require_text(row.get("claim"), "EvidenceDossier.claims.claim")
            if row.get("epistemic_status") not in {
                "official_statement", "named_person_statement", "independent_measurement",
                "community_report", "attributed_rumor", "editorial_interpretation",
                "unverified_or_disputed",
            }:
                raise HandoffError("EvidenceDossier contém epistemic_status desconhecido.")
            refs = row.get("evidence_ids")
            source_ids = row.get("source_ids")
            if not isinstance(refs, list) or not refs or not isinstance(source_ids, list) or not source_ids:
                raise HandoffError("Toda alegação do dossiê deve apontar para fonte e evidência.")
            if any(not isinstance(source_id, str) for source_id in source_ids):
                raise HandoffError("EvidenceDossier.claims.source_ids contém valor inválido.")
            if any(not isinstance(ref, str) or ref not in evidence_ids for ref in refs):
                raise HandoffError("Alegação do dossiê aponta para evidence_id ausente.")
        if not isinstance(payload.get("blockers"), list) or not isinstance(payload.get("security_flags"), list):
            raise HandoffError("EvidenceDossier.blockers e security_flags precisam ser listas.")
        for flag in payload["security_flags"]:
            if not isinstance(flag, Mapping) or flag.get("evidence_id") not in evidence_ids:
                raise HandoffError("Security flag não aponta para evidência do dossiê.")
            if flag.get("handling") != "retained_as_untrusted_data_not_executed":
                raise HandoffError("Conteúdo instrucional de fonte precisa permanecer inerte.")
    elif artifact_type == ARTIFACT_KEYS["editorial_brief"]:
        dossier_hash = payload.get("evidence_dossier_sha256", payload.get("candidate_dossier_sha256"))
        if not _is_sha256(dossier_hash):
            raise HandoffError("EditorialBrief exige hash válido do dossiê que a originou.")
        _require_text(payload.get("angle"), "EditorialBrief.angle")
        if payload.get("genre") not in {"news", "rumor", "investigation", "analysis", "review", "guide"}:
            raise HandoffError("EditorialBrief.genre fora do contrato.")
        for field in ("questions", "modules", "gaps"):
            if not isinstance(payload.get(field), list):
                raise HandoffError(f"EditorialBrief.{field} precisa ser lista.")
        if any(not isinstance(item, str) or not item.strip() for item in payload["questions"]):
            raise HandoffError("EditorialBrief.questions contém item inválido.")
        if any(not isinstance(item, str) or not item.strip() for item in payload["gaps"]):
            raise HandoffError("EditorialBrief.gaps contém item inválido.")
        if any(not isinstance(item, Mapping) for item in payload["modules"]):
            raise HandoffError("EditorialBrief.modules contém módulo inválido.")
        if not isinstance(payload.get("needs_more_research"), bool):
            raise HandoffError("EditorialBrief.needs_more_research precisa ser booleano.")
        _require_text(payload.get("visual_policy"), "EditorialBrief.visual_policy")
        if payload.get("candidate_item_id") is not None:
            _require_text(payload.get("candidate_item_id"), "EditorialBrief.candidate_item_id")
        persona_ref = payload.get("journalist_persona_ref")
        if persona_ref is not None:
            if not isinstance(persona_ref, Mapping) or persona_ref.get("immutable_reference_only") is not True:
                raise HandoffError("EditorialBrief precisa referenciar a persona sem recriar seu DNA.")
            _require_text(persona_ref.get("persona_id"), "EditorialBrief.journalist_persona_ref.persona_id")
            if not _is_sha256(persona_ref.get("profile_sha256")):
                raise HandoffError("EditorialBrief exige hash da identidade de jornalista.")
    elif artifact_type == ARTIFACT_KEYS["story_draft"]:
        revision = payload.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise HandoffError("StoryDraft.revision precisa ser inteiro positivo.")
        parent_hash = payload.get("parent_draft_sha256")
        if (revision == 1 and parent_hash is not None) or (revision > 1 and not _is_sha256(parent_hash)):
            raise HandoffError("StoryDraft precisa preservar a linhagem da revisão anterior.")
        if not _is_sha256(payload.get("draft_sha256")):
            raise HandoffError("StoryDraft exige hash de texto válido.")
        _require_text(payload.get("headline"), "StoryDraft.headline")
        _require_text(payload.get("dek"), "StoryDraft.dek")
        sections = payload.get("sections")
        if not isinstance(sections, list) or not sections:
            raise HandoffError("StoryDraft precisa conter seções.")
        available_evidence: set[str] | None = None
        refs = payload.get("evidence_ids")
        if refs is not None:
            available_evidence = set(refs) if isinstance(refs, list) else set()
        for row in sections:
            if not isinstance(row, Mapping):
                raise HandoffError("StoryDraft.sections contém seção inválida.")
            _require_text(row.get("heading"), "StoryDraft.sections.heading")
            _require_text(row.get("body"), "StoryDraft.sections.body")
            if not isinstance(row.get("source_ids"), list) or not isinstance(row.get("evidence_ids"), list):
                raise HandoffError("StoryDraft precisa preservar IDs de fonte e evidência.")
            if any(not isinstance(ref, str) for ref in row["source_ids"] + row["evidence_ids"]):
                raise HandoffError("StoryDraft contém referência de fonte ou evidência inválida.")
            if available_evidence is not None and not set(row["evidence_ids"]).issubset(available_evidence):
                raise HandoffError("StoryDraft cita evidência fora do conjunto disponível.")
        if not _is_sha256(payload.get("evidence_dossier_sha256")) or not _is_sha256(payload.get("editorial_brief_sha256")):
            raise HandoffError("StoryDraft exige hashes do dossiê e do brief.")
        persona = payload.get("persona_ref")
        if not isinstance(persona, Mapping) or persona.get("immutable_reference_only") is not True:
            raise HandoffError("StoryDraft precisa referenciar a persona sem recriar seu DNA.")
        for field in ("role", "profile_id", "version"):
            _require_text(persona.get(field), f"StoryDraft.persona_ref.{field}")
        if not _is_sha256(persona.get("profile_sha256")):
            raise HandoffError("StoryDraft exige hash da identidade referenciada.")
        if not isinstance(payload.get("requested_research"), list):
            raise HandoffError("StoryDraft.requested_research precisa ser lista.")
    elif artifact_type == ARTIFACT_KEYS["fact_check_verdict"]:
        if not _is_sha256(payload.get("draft_sha256")) or not _is_sha256(payload.get("evidence_dossier_sha256")):
            raise HandoffError("FactCheckVerdict exige hashes válidos do draft e do dossiê.")
        if payload.get("status") not in {"pass", "revise", "hold"}:
            raise HandoffError("FactCheckVerdict.status fora do contrato.")
        findings = payload.get("findings")
        if not isinstance(findings, list) or not findings:
            raise HandoffError("FactCheckVerdict precisa conter achados.")
        for row in findings:
            if not isinstance(row, Mapping):
                raise HandoffError("FactCheckVerdict.findings contém item inválido.")
            _require_text(row.get("claim"), "FactCheckVerdict.findings.claim")
            if not isinstance(row.get("evidence_ids"), list) or not row["evidence_ids"]:
                raise HandoffError("Achado factual precisa apontar para evidências.")
            if any(not isinstance(ref, str) for ref in row["evidence_ids"]):
                raise HandoffError("Achado factual contém evidence_id inválido.")
            if row.get("status") not in {"supported", "contradicted", "unsupported", "uncertain"}:
                raise HandoffError("Achado factual contém status desconhecido.")
        if not isinstance(payload.get("rumor_attribution_preserved"), bool):
            raise HandoffError("FactCheckVerdict precisa declarar o estado de atribuição de rumor.")
    elif artifact_type == ARTIFACT_KEYS["editorial_review"]:
        if not _is_sha256(payload.get("draft_sha256")) or not _is_sha256(payload.get("fact_check_sha256")):
            raise HandoffError("EditorialReview exige hashes válidos do draft e da checagem.")
        if payload.get("verdict") not in {"pass", "revise", "hold"}:
            raise HandoffError("EditorialReview.verdict fora do contrato.")
        if not isinstance(payload.get("findings"), list):
            raise HandoffError("EditorialReview.findings precisa ser lista.")
        if payload.get("human_review_required") is not True or payload.get("human_approval") is not False:
            raise HandoffError("EditorialReview precisa manter decisão humana pendente.")
        if payload.get("published") is not False:
            raise HandoffError("EditorialReview não pode marcar a matéria como publicada.")


def _seal(artifact_type: str, story_id: str, revision_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if artifact_type not in {*ARTIFACT_KEYS.values(), CANDIDATE_DOSSIER_TYPE}:
        raise HandoffError("Tipo de handoff editorial desconhecido.")
    if not isinstance(story_id, str) or not story_id.strip() or not isinstance(revision_id, str) or not revision_id.strip():
        raise HandoffError("Handoff editorial exige story_id e revision_id.")
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "artifact_id": f"{artifact_type}:{story_id}:{revision_id}",
        "story_id": story_id,
        "revision_id": revision_id,
        "payload": dict(payload),
    }
    return {**core, "content_sha256": _canonical_sha256(core)}


def validate_artifact(value: Any, expected_type: str | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HandoffError("Handoff precisa ser objeto.")
    artifact = dict(value)
    if set(artifact) != {
        "schema_version", "artifact_type", "artifact_id", "story_id", "revision_id", "payload", "content_sha256",
    }:
        raise HandoffError("Envelope de handoff contém campos ausentes ou extras.")
    if artifact.get("schema_version") != SCHEMA_VERSION or artifact.get("artifact_type") not in {
        *ARTIFACT_KEYS.values(), CANDIDATE_DOSSIER_TYPE,
    }:
        raise HandoffError("Versão ou tipo de handoff não suportado.")
    if expected_type is not None and artifact["artifact_type"] != expected_type:
        raise HandoffError("Tipo de handoff não corresponde à etapa.")
    if not isinstance(artifact.get("story_id"), str) or not artifact["story_id"].strip():
        raise HandoffError("story_id inválido no handoff.")
    if not isinstance(artifact.get("revision_id"), str) or not artifact["revision_id"].strip():
        raise HandoffError("revision_id inválido no handoff.")
    if artifact.get("artifact_id") != f"{artifact['artifact_type']}:{artifact['story_id']}:{artifact['revision_id']}":
        raise HandoffError("artifact_id diverge da linhagem do handoff.")
    if not isinstance(artifact.get("payload"), Mapping):
        raise HandoffError("payload do handoff precisa ser objeto.")
    _validate_payload(artifact["artifact_type"], artifact["payload"])
    if artifact["artifact_type"] == ARTIFACT_KEYS["story_draft"]:
        expected_revision = f"-r{artifact['payload']['revision']}"
        if not artifact["revision_id"].endswith(expected_revision):
            raise HandoffError("StoryDraft.revision_id diverge da revisão declarada.")
    core = {key: artifact[key] for key in artifact if key != "content_sha256"}
    if artifact.get("content_sha256") != _canonical_sha256(core):
        raise HandoffError("Hash do handoff diverge do conteúdo.")
    return artifact


def _input(inputs: Mapping[str, Any], key: str, expected_type: str) -> dict[str, Any]:
    try:
        return validate_artifact(inputs[key], expected_type)
    except KeyError as error:
        raise HandoffError(f"Handoff anterior ausente: {key}.") from error


def _evidence_id(source_id: str) -> str:
    return f"evidence-{source_id.casefold()}"


def build_candidate_dossier(
    *,
    story_id: str,
    batch_id: str,
    triage_task_id: str,
    investigator_task_id: str,
    candidates: list[Mapping[str, Any]],
    evidence: list[Mapping[str, Any]],
    investigator_output: Mapping[str, Any],
    portfolio: list[str] | None = None,
    research_packet: Mapping[str, Any] | None = None,
    triage_response_sha256: str | None = None,
    investigator_response_sha256: str | None = None,
) -> dict[str, Any]:
    """Seal the Radar candidate pool and investigation in one typed handoff.

    Natural-language legacy ``claim_id`` labels are retained verbatim in the
    dossier while the Motor generates a deterministic, machine-safe claim ID.
    Raw role responses remain immutable and are identified by their SHA-256.
    Source excerpts are copied only when the upstream evidence record carries
    an explicit ``excerpt_authorized`` decision.
    """

    _require_text(story_id, "CandidateDossier.story_id")
    _require_text(batch_id, "CandidateDossier.batch_id")
    _require_text(triage_task_id, "CandidateDossier.triage_task_id")
    _require_text(investigator_task_id, "CandidateDossier.investigator_task_id")
    if not isinstance(investigator_output, Mapping):
        raise HandoffError("Investigator output precisa ser objeto.")
    if not isinstance(candidates, list) or not isinstance(evidence, list):
        raise HandoffError("CandidateDossier exige listas de candidates e evidence.")
    if not isinstance(investigator_output.get("claims", []), (list, tuple)):
        raise HandoffError("Investigator claims precisa ser lista.")
    for field in ("blockers", "contradictions", "rumors", "open_questions"):
        if field in investigator_output and not isinstance(investigator_output[field], (list, tuple)):
            raise HandoffError(f"Investigator.{field} precisa ser lista.")
    portfolio_items = portfolio if portfolio is not None else []
    if not isinstance(portfolio_items, (list, tuple)):
        raise HandoffError("CandidateDossier.portfolio precisa ser lista de IDs.")
    if any(not isinstance(item, str) or not item.strip() for item in portfolio_items):
        raise HandoffError("CandidateDossier.portfolio contém referência inválida.")
    if len(set(portfolio_items)) != len(portfolio_items):
        raise HandoffError("CandidateDossier.portfolio contém referência duplicada.")
    if not _is_sha256(triage_response_sha256) or not _is_sha256(investigator_response_sha256):
        raise HandoffError("CandidateDossier exige hashes das respostas de triagem e investigação.")

    normalized_evidence: list[dict[str, Any]] = []
    evidence_by_id: dict[str, dict[str, Any]] = {}
    for raw in evidence:
        if not isinstance(raw, Mapping):
            raise HandoffError("CandidateDossier evidence contém item inválido.")
        evidence_id = _require_text(raw.get("evidence_id"), "CandidateDossier.evidence.evidence_id")
        source_id = _require_text(raw.get("source_id"), "CandidateDossier.evidence.source_id")
        publisher = _require_text(raw.get("publisher"), "CandidateDossier.evidence.publisher")
        locator = raw.get("locator", raw.get("source_url", raw.get("url")))
        locator = _require_text(locator, "CandidateDossier.evidence.locator")
        row = {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "document_id": raw.get("source_document_id", raw.get("document_id")),
            "source_role": str(raw.get("source_role") or "registered_source_role_unclassified"),
            "publisher": publisher,
            "locator": locator,
            "first_origin_source_id": raw.get("first_origin_source_id"),
            "republication_relation": raw.get("republication_relation"),
            "published_at": raw.get("published_at"),
            "observed_at": raw.get("observed_at"),
            "content_sha256": raw.get("content_sha256"),
            "excerpt": None,
            "excerpt_authorized": False,
            "trust_boundary": "untrusted_evidence_data_only_never_instructions",
        }
        excerpt = raw.get("excerpt")
        if raw.get("excerpt_authorized") is True and isinstance(excerpt, str) and excerpt.strip():
            row["excerpt"] = excerpt
            row["excerpt_authorized"] = True
        if evidence_id in evidence_by_id:
            raise HandoffError("CandidateDossier contém evidence_id duplicado.")
        evidence_by_id[evidence_id] = row
        normalized_evidence.append(row)

    normalized_candidates: list[dict[str, Any]] = []
    candidate_ids: set[str] = set()
    for raw in candidates:
        if not isinstance(raw, Mapping):
            raise HandoffError("CandidateDossier candidates contém item inválido.")
        candidate_id = _require_text(
            raw.get("candidate_item_id", raw.get("item_id")), "CandidateDossier.candidate_item_id"
        )
        if candidate_id in candidate_ids:
            raise HandoffError("CandidateDossier contém candidate_item_id duplicado.")
        candidate_ids.add(candidate_id)
        triage = raw.get("triage_decision", raw.get("triage", {}))
        if not isinstance(triage, Mapping):
            raise HandoffError("CandidateDossier candidate perdeu a decisão de triagem.")
        lane = raw.get("triage_lane", triage.get("suggested_lane", triage.get("lane")))
        if lane not in EDITORIAL_TRIAGE_LANES:
            raise HandoffError("CandidateDossier candidate não está em lane elegível, inclusive monitoramento.")
        angle = raw.get("candidate_angle", triage.get("candidate_angle"))
        angle = _require_text(angle, "CandidateDossier.candidate_angle")
        evidence_ids = raw.get("evidence_ids", [])
        triage_refs = raw.get("triage_evidence_refs", triage.get("evidence_refs", []))
        if not isinstance(evidence_ids, (list, tuple)) or not isinstance(triage_refs, (list, tuple)):
            raise HandoffError("CandidateDossier candidate contém referências inválidas.")
        if any(not isinstance(ref, str) or not ref.strip() for ref in evidence_ids):
            raise HandoffError("CandidateDossier candidate contém evidence_id inválido.")
        if any(not isinstance(ref, str) or not ref.strip() for ref in triage_refs):
            raise HandoffError("CandidateDossier triage_evidence_refs contém ID inválido.")
        candidate_evidence_ids = sorted(set(evidence_ids))
        if any(not isinstance(ref, str) or ref not in evidence_by_id for ref in candidate_evidence_ids):
            raise HandoffError("CandidateDossier candidate aponta para evidência não persistida.")
        detail: Mapping[str, Any] = {}
        raw_diff = raw.get("diff")
        if isinstance(raw_diff, str) and raw_diff.strip():
            try:
                parsed_detail = json.loads(raw_diff)
            except json.JSONDecodeError:
                raise HandoffError("CandidateDossier discovery diff não é JSON válido.") from None
            if not isinstance(parsed_detail, Mapping):
                raise HandoffError("CandidateDossier discovery diff precisa ser objeto.")
            detail = parsed_detail
        source_lineage = raw.get("source_lineage", detail.get("source_lineage", []))
        claim_lineage = raw.get("claim_lineage", detail.get("claim_lineage", []))
        if not isinstance(source_lineage, (list, tuple)) or any(not isinstance(item, Mapping) for item in source_lineage):
            raise HandoffError("CandidateDossier source_lineage precisa ser lista de objetos.")
        if not isinstance(claim_lineage, (list, tuple)) or any(not isinstance(item, Mapping) for item in claim_lineage):
            raise HandoffError("CandidateDossier claim_lineage precisa ser lista de objetos.")
        for source in source_lineage:
            _require_text(source.get("source_id"), "CandidateDossier.source_lineage.source_id")
            for field in ("document_id", "publisher", "url"):
                if source.get(field) is not None:
                    _require_text(source.get(field), f"CandidateDossier.source_lineage.{field}")
        normalized_candidates.append({
            "candidate_item_id": candidate_id,
            "triage_lane": lane,
            "candidate_angle": angle,
            "triage_evidence_refs": sorted(set(triage_refs)),
            "evidence_ids": candidate_evidence_ids,
            "title": raw.get("title"),
            "publisher": raw.get("publisher"),
            "url": raw.get("url"),
            "published_at": raw.get("published_at"),
            "source_lineage": list(source_lineage) if isinstance(source_lineage, (list, tuple)) else [],
            "claim_lineage": list(claim_lineage) if isinstance(claim_lineage, (list, tuple)) else [],
        })
    normalized_candidates.sort(key=lambda row: row["candidate_item_id"])

    normalized_claims: list[dict[str, Any]] = []
    claim_id_mappings: list[dict[str, str]] = []
    for index, raw_claim in enumerate(investigator_output.get("claims", [])):
        if not isinstance(raw_claim, Mapping):
            raise HandoffError(f"Investigator claim {index} não é objeto.")
        label = raw_claim.get(
            "claim_label",
            raw_claim.get("claim", raw_claim.get("source_claim_label", raw_claim.get("claim_id"))),
        )
        label = _require_text(label, f"Investigator.claims[{index}].claim_label")
        epistemic = raw_claim.get("epistemic_status")
        refs = raw_claim.get("evidence_ids")
        if not isinstance(refs, (list, tuple)) or not refs or any(not isinstance(ref, str) for ref in refs):
            raise HandoffError(f"Investigator claim {index} não possui evidence_ids válidos.")
        refs_list = list(dict.fromkeys(refs))
        if any(ref not in evidence_by_id for ref in refs_list):
            raise HandoffError(f"Investigator claim {index} aponta para evidência ausente.")
        if epistemic not in {
            "official_statement", "named_person_statement", "independent_measurement",
            "community_report", "attributed_rumor", "editorial_interpretation", "unverified_or_disputed",
        }:
            raise HandoffError(f"Investigator claim {index} possui epistemic_status inválido.")
        sources = sorted({evidence_by_id[ref]["source_id"] for ref in refs_list})
        supplied_sources = raw_claim.get("source_ids")
        if supplied_sources is not None and (
            not isinstance(supplied_sources, (list, tuple))
            or any(not isinstance(source, str) or not source.strip() for source in supplied_sources)
            or set(supplied_sources) != set(sources)
        ):
            raise HandoffError(f"Investigator claim {index} source_ids divergem das evidence_ids.")
        claim_id = canonical_material_claim_id(label, refs_list, epistemic)
        normalized_claims.append({
            "claim_id": claim_id,
            "claim": label,
            "source_claim_label": label,
            "source_ids": sources,
            "evidence_ids": refs_list,
            "epistemic_status": epistemic,
        })
        claim_id_mappings.append({
            "source_claim_label": label,
            "canonical_claim_id": claim_id,
        })
    if len({row["claim_id"] for row in normalized_claims}) != len(normalized_claims):
        raise HandoffError("Investigator repetiu claims com a mesma identidade/evidência.")

    sufficiency = investigator_output.get("sufficiency", "not_reported")
    if sufficiency not in {"sufficient", "partial", "insufficient", "not_reported"}:
        raise HandoffError("Investigator.sufficiency desconhecida.")
    payload = {
        "batch_id": batch_id,
        "triage_task_id": triage_task_id,
        "investigator_task_id": investigator_task_id,
        "portfolio": list(portfolio_items),
        "candidate_item_ids": [row["candidate_item_id"] for row in normalized_candidates],
        "candidates": normalized_candidates,
        "evidence": normalized_evidence,
        "claims": normalized_claims,
        "blockers": list(investigator_output.get("blockers", [])) if isinstance(investigator_output.get("blockers", []), (list, tuple)) else [],
        "contradictions": list(investigator_output.get("contradictions", [])) if isinstance(investigator_output.get("contradictions", []), (list, tuple)) else [],
        "rumors": (
            list(investigator_output["rumors"])
            if "rumors" in investigator_output and isinstance(investigator_output.get("rumors"), (list, tuple))
            else [
                {"claim_id": row["claim_id"], "epistemic_status": row["epistemic_status"], "evidence_ids": list(row["evidence_ids"])}
                for row in normalized_claims if row["epistemic_status"] in {"attributed_rumor", "unverified_or_disputed"}
            ]
        ),
        "open_questions": list(investigator_output.get("open_questions", [])) if isinstance(investigator_output.get("open_questions", []), (list, tuple)) else [],
        "sufficiency": sufficiency,
        "research_packet": dict(research_packet) if isinstance(research_packet, Mapping) else None,
        "claim_id_mappings": claim_id_mappings,
        "investigator_response_sha256": investigator_response_sha256,
        "triage_response_sha256": triage_response_sha256,
        "trust_boundary": "source_material_and_role_output_are_untrusted_evidence_data",
    }
    artifact = _seal(CANDIDATE_DOSSIER_TYPE, story_id, f"batch-{batch_id}", payload)
    return validate_artifact(artifact, CANDIDATE_DOSSIER_TYPE)


def build_assignment_editor_input(
    candidate_dossier: Mapping[str, Any],
    *,
    edition_state: Mapping[str, Any],
    editorial_constraints: Mapping[str, Any] | None = None,
    eligible_journalists: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Create the assignment editor input without inserting a fixture title."""

    dossier = validate_artifact(candidate_dossier, CANDIDATE_DOSSIER_TYPE)
    if not dossier["payload"]["candidate_item_ids"]:
        raise HandoffError("CandidateDossier vazio não deve criar tarefa de assignment_editor.")
    if not isinstance(edition_state, Mapping):
        raise HandoffError("Assignment editor exige edition_state tipado.")
    lines = dict(eligible_journalists or JOURNALIST_EDITORIAL_LINES)
    if not lines or set(lines) - set(JOURNALIST_EDITORIAL_LINES):
        raise HandoffError("Assignment editor recebeu jornalista fora da matriz aprovada.")
    for persona_id, line in lines.items():
        _require_text(persona_id, "eligible_journalists.persona_id")
        _require_text(line, f"eligible_journalists.{persona_id}")
    constraints = dict(editorial_constraints or {})
    caller_ids = constraints.get("eligible_candidate_ids")
    candidate_ids = list(dossier["payload"]["candidate_item_ids"])
    if caller_ids is not None and (not isinstance(caller_ids, (list, tuple)) or set(caller_ids) != set(candidate_ids)):
        raise HandoffError("Assignment editor eligible_candidate_ids diverge do CandidateDossier.")
    constraints.update({
        "eligible_candidate_ids": candidate_ids,
        "eligible_journalists": lines,
        "journalist_topic_matrix": {key: [persona for persona in value if persona in lines]
                                     for key, value in JOURNALIST_TOPIC_MATRIX.items()},
        "publication_state": "not_published",
        "character_rules": "Atribua uma persona aprovada por tema; preserve integralmente seu DNA.",
        "visual_rights_gate": "image_needs are requests only; rights approval is separate and required.",
    })
    return {
        "evidence_dossier": dossier["payload"],
        "edition_state": dict(edition_state),
        "editorial_constraints": constraints,
        "required_coverage": [
            "Escolha somente candidate_item_id existente no CandidateDossier.",
            "Considere candidatos em monitoramento se houver ângulo sustentado; não os promova automaticamente.",
            "Escolha uma única persona elegível conforme a matriz de temas e a linha editorial fornecida.",
            "Se nenhuma pauta justificar matéria, não invente título ou candidato; encaminhe monitoramento ou investigação adicional.",
            "Separe lacunas e metadados internos da linguagem que será escrita para leitores.",
            "Declare necessidades visuais sem presumir autorização ou licença.",
        ],
    }


def validate_assignment_editor_output(
    output: Mapping[str, Any],
    candidate_dossier: Mapping[str, Any],
    *,
    approved_persona_hashes: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Validate the editor's actual candidate and persona choice against the dossier."""

    dossier = validate_artifact(candidate_dossier, CANDIDATE_DOSSIER_TYPE)
    if not isinstance(output, Mapping):
        raise HandoffError("Assignment editor output precisa ser objeto.")
    candidate_id = output.get("candidate_item_id")
    if not isinstance(candidate_id, str) or candidate_id not in set(dossier["payload"]["candidate_item_ids"]):
        raise HandoffError("Assignment editor selecionou candidate_item_id ausente do CandidateDossier.")
    persona_id = output.get("journalist_persona_id")
    if not isinstance(persona_id, str) or persona_id not in JOURNALIST_EDITORIAL_LINES:
        raise HandoffError("Assignment editor selecionou persona ausente da matriz aprovada.")
    if output.get("genre") not in {"news", "rumor", "investigation", "analysis", "review", "guide"}:
        raise HandoffError("Assignment editor genre fora do contrato.")
    if not isinstance(output.get("angle"), str) or not output["angle"].strip():
        raise HandoffError("Assignment editor não propôs ângulo editorial.")
    if not isinstance(output.get("questions"), (list, tuple)) or not isinstance(output.get("modules"), (list, tuple)):
        raise HandoffError("Assignment editor não entregou perguntas e módulos tipados.")
    if not isinstance(output.get("gaps"), (list, tuple)) or not isinstance(output.get("needs_more_research"), bool):
        raise HandoffError("Assignment editor não preservou gaps e needs_more_research.")
    hashes = dict(approved_persona_hashes or {})
    if hashes:
        digest = hashes.get(persona_id)
        if not _is_sha256(digest):
            raise HandoffError("Persona escolhida não possui hash aprovado disponível.")
    candidate = next(row for row in dossier["payload"]["candidates"] if row["candidate_item_id"] == candidate_id)
    if not candidate["evidence_ids"] and output.get("needs_more_research") is not True:
        raise HandoffError("Assignment editor não pode propor matéria sem evidência nem pesquisa pendente.")
    theme = output.get("editorial_theme") or candidate.get("editorial_theme")
    if theme is not None:
        permitted = JOURNALIST_TOPIC_MATRIX.get(str(theme))
        if permitted is None or persona_id not in permitted:
            raise HandoffError("Persona escolhida não corresponde ao tema declarado.")
    return {
        **dict(output),
        "candidate_item_id": candidate_id,
        "journalist_persona_id": persona_id,
        "journalist_persona_ref": {
            "persona_id": persona_id,
            "profile_sha256": hashes.get(persona_id) if hashes else None,
            "immutable_reference_only": True,
        },
    }


def build_editorial_brief_from_assignment(
    *,
    story_id: str,
    revision_id: str,
    candidate_dossier: Mapping[str, Any],
    assignment_output: Mapping[str, Any],
    approved_persona_hash: str,
    assignment_task_id: str,
    assignment_response_sha256: str | None = None,
) -> dict[str, Any]:
    """Persist the editor's real assignment as a hash-bound EditorialBrief."""

    dossier = validate_artifact(candidate_dossier, CANDIDATE_DOSSIER_TYPE)
    persona_id = assignment_output.get("journalist_persona_id") if isinstance(assignment_output, Mapping) else None
    validated = validate_assignment_editor_output(
        assignment_output,
        dossier,
        approved_persona_hashes={str(persona_id): approved_persona_hash},
    )
    _require_text(assignment_task_id, "EditorialBrief.assignment_task_id")
    if not _is_sha256(approved_persona_hash):
        raise HandoffError("EditorialBrief exige SHA-256 da persona aprovada.")
    if assignment_response_sha256 is not None and not _is_sha256(assignment_response_sha256):
        raise HandoffError("EditorialBrief.assignment_response_sha256 inválido.")
    candidate = next(
        row for row in dossier["payload"]["candidates"]
        if row["candidate_item_id"] == validated["candidate_item_id"]
    )
    image_needs = validated.get("image_needs", [])
    if not isinstance(image_needs, (list, tuple)):
        raise HandoffError("EditorialBrief.image_needs precisa ser lista.")
    if any(not isinstance(item, Mapping) for item in validated["modules"]):
        raise HandoffError("EditorialBrief.modules contém item não estruturado.")
    payload = {
        "candidate_dossier_sha256": dossier["content_sha256"],
        "candidate_item_id": validated["candidate_item_id"],
        "triage_lane": candidate["triage_lane"],
        "assignment_task_id": assignment_task_id,
        "assignment_response_sha256": assignment_response_sha256,
        "angle": validated["angle"],
        "genre": validated["genre"],
        "questions": list(validated["questions"]),
        "modules": [dict(item) for item in validated["modules"] if isinstance(item, Mapping)],
        "gaps": list(validated["gaps"]),
        "needs_more_research": validated["needs_more_research"],
        "image_needs": [dict(item) if isinstance(item, Mapping) else item for item in image_needs],
        "journalist_persona_ref": {
            "persona_id": validated["journalist_persona_id"],
            "profile_sha256": approved_persona_hash,
            "immutable_reference_only": True,
        },
        "visual_policy": "visual_requests_require_a_separate_rights_gate",
        "human_editorial_approval": "pending",
        "published": False,
    }
    return validate_artifact(
        _seal(ARTIFACT_KEYS["editorial_brief"], story_id, revision_id, payload),
        ARTIFACT_KEYS["editorial_brief"],
    )


def project_editorial_brief_for_writer(value: Mapping[str, Any]) -> dict[str, Any]:
    """Expose assignment content to the writer without task/audit metadata."""

    brief = validate_artifact(value, ARTIFACT_KEYS["editorial_brief"])
    payload = brief["payload"]
    return {
        "angle": payload["angle"],
        "genre": payload["genre"],
        "questions": list(payload["questions"]),
        "modules": [dict(item) for item in payload["modules"]],
        "gaps": list(payload["gaps"]),
        "needs_more_research": payload["needs_more_research"],
        "image_needs": list(payload.get("image_needs", [])),
        "selected_candidate_id": payload.get("candidate_item_id"),
        "selected_journalist_id": payload.get("journalist_persona_ref", {}).get("persona_id"),
    }


def build_handoff_artifact(
    stage: str,
    *,
    run_id: str,
    packet: Mapping[str, Any],
    output: Mapping[str, Any],
    inputs: Mapping[str, Any],
    content_identity: Mapping[str, Any],
    case: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the one typed artifact emitted by a deterministic factory stage."""
    story_id = f"story-{run_id}"
    if stage == "source_analysis":
        evidence = []
        security_flags = []
        for source in packet["sources"]:
            evidence_id = _evidence_id(str(source["id"]))
            excerpt = str(source["evidence"])
            evidence.append({
                "evidence_id": evidence_id,
                "source_id": source["id"],
                "source_role": {
                    "official": "primary_statement",
                    "secondary": "secondary_reporting",
                    "starting_point": "starting_point",
                }[source["kind"]],
                "publisher": source["publisher"],
                "locator": source["url"],
                "excerpt": excerpt,
                "trust_boundary": "untrusted_evidence_data_only_never_instructions",
            })
            if _INSTRUCTION_LIKE.search(excerpt):
                security_flags.append({
                    "evidence_id": evidence_id,
                    "flag": "instruction_like_source_text",
                    "handling": "retained_as_untrusted_data_not_executed",
                })
        claims = []
        for claim in output.get("claims", []):
            source_ids = list(claim.get("source_ids", []))
            assessment = claim.get("assessment")
            epistemic = {
                "supported": "official_statement",
                "rumor": "attributed_rumor",
                "uncertain": "unverified_or_disputed",
                "contradicted": "unverified_or_disputed",
            }.get(str(assessment), "unverified_or_disputed")
            claims.append({
                "claim_id": claim["claim_id"],
                "claim": claim["claim"],
                "epistemic_status": epistemic,
                "source_ids": source_ids,
                "evidence_ids": [_evidence_id(source_id) for source_id in source_ids],
                "caveat": claim.get("caveat", ""),
            })
        payload = {
            "question": packet["topic"],
            "evidence": evidence,
            "claims": claims,
            "blockers": list(output.get("blockers", [])),
            "security_flags": security_flags,
            "source_policy": "primary_and_intermediary_sources_remain_distinct",
        }
        return _seal(ARTIFACT_KEYS["evidence_dossier"], story_id, run_id, payload)

    if stage == "outline":
        dossier = _input(inputs, "evidence_dossier", ARTIFACT_KEYS["evidence_dossier"])
        case = case or {}
        payload = {
            "evidence_dossier_sha256": dossier["content_sha256"],
            "angle": str(case.get("angle") or output["dek"]),
            "genre": str(case.get("genre") or "analysis"),
            "questions": list(case.get("questions") or [section["focus"] for section in output["sections"]]),
            "modules": [dict(section) for section in output["sections"]],
            "gaps": list(case.get("gaps") or []),
            "needs_more_research": bool(case.get("needs_more_research", False)),
            "visual_policy": "visual_requests_require_a_separate_rights_gate",
        }
        return _seal(ARTIFACT_KEYS["editorial_brief"], story_id, run_id, payload)

    if stage in {"draft", "correction"}:
        dossier = _input(inputs, "evidence_dossier", ARTIFACT_KEYS["evidence_dossier"])
        brief = _input(inputs, "editorial_brief", ARTIFACT_KEYS["editorial_brief"])
        previous_draft = inputs.get("story_draft")
        revision = 1
        parent_hash = None
        if stage == "correction":
            previous_draft = validate_artifact(previous_draft, ARTIFACT_KEYS["story_draft"])
            revision = int(previous_draft["payload"]["revision"]) + 1
            parent_hash = previous_draft["payload"]["draft_sha256"]
        article_hash = article_revision_sha256(output)
        body = str(output["body_markdown"])
        cited_source_ids = list(output["source_ids"])
        payload = {
            "revision": revision,
            "parent_draft_sha256": parent_hash,
            "draft_sha256": article_hash,
            "headline": output["headline"],
            "dek": output["dek"],
            "sections": [{
                "heading": "Matéria",
                "body": body,
                "source_ids": cited_source_ids,
                "evidence_ids": [_evidence_id(source_id) for source_id in cited_source_ids],
            }],
            "evidence_dossier_sha256": dossier["content_sha256"],
            "editorial_brief_sha256": brief["content_sha256"],
            "persona_ref": {
                "role": content_identity.get("role"),
                "profile_id": content_identity.get("profile_id"),
                "version": content_identity.get("version"),
                "profile_sha256": profile_sha256(content_identity),
                "immutable_reference_only": True,
            },
            "requested_research": [],
        }
        return _seal(ARTIFACT_KEYS["story_draft"], story_id, f"{run_id}-r{revision}", payload)

    if stage in {"fact_check", "final_fact_check"}:
        dossier = _input(inputs, "evidence_dossier", ARTIFACT_KEYS["evidence_dossier"])
        draft = _input(inputs, "story_draft", ARTIFACT_KEYS["story_draft"])
        article_for_check = output.get("article_for_check")
        if not isinstance(article_for_check, Mapping) or draft["payload"]["draft_sha256"] != article_revision_sha256(
            article_for_check
        ):
            raise HandoffError("FactCheckVerdict recebeu uma revisão divergente.")
        findings = []
        for finding in output.get("findings", []):
            source_ids = list(finding.get("source_ids", []))
            findings.append({
                "claim": finding["claim"],
                "evidence_ids": [_evidence_id(source_id) for source_id in source_ids],
                "status": finding["status"],
                "confidence": finding["confidence"],
                "correction": finding.get("correction", ""),
            })
        dossier_claims = dossier["payload"]["claims"]
        draft_body = " ".join(section["body"] for section in draft["payload"]["sections"])
        body_preserves_attribution = bool(re.search(r"\b(?:rumor|boato)\b", draft_body, re.IGNORECASE))
        uncertain_findings = [item for item in findings if item["status"] == "uncertain"]
        rumor_attributed = bool(uncertain_findings) and body_preserves_attribution and all(
            any(
                claim["epistemic_status"] == "attributed_rumor"
                and set(claim["evidence_ids"]) == set(finding["evidence_ids"])
                for claim in dossier_claims
            )
            for finding in uncertain_findings
        )
        statuses = {item["status"] for item in findings}
        if statuses & {"contradicted", "unsupported"}:
            verdict = "hold"
        elif "uncertain" in statuses and not rumor_attributed:
            verdict = "hold"
        else:
            verdict = "pass"
        payload = {
            "draft_sha256": draft["payload"]["draft_sha256"],
            "evidence_dossier_sha256": dossier["content_sha256"],
            "status": verdict,
            "findings": findings,
            "rumor_attribution_preserved": rumor_attributed,
        }
        return _seal(
            ARTIFACT_KEYS["fact_check_verdict"], story_id, draft["revision_id"], payload
        )

    if stage in {"review", "final_review"}:
        draft = _input(inputs, "story_draft", ARTIFACT_KEYS["story_draft"])
        fact_check = _input(inputs, "fact_check_verdict", ARTIFACT_KEYS["fact_check_verdict"])
        article_for_review = output.get("article_for_review")
        if not isinstance(article_for_review, Mapping) or draft["payload"]["draft_sha256"] != article_revision_sha256(
            article_for_review
        ):
            raise HandoffError("EditorialReview recebeu uma revisão divergente.")
        verdict = str(output.get("verdict", "hold"))
        if fact_check["payload"]["status"] == "hold":
            verdict = "hold"
        payload = {
            "draft_sha256": draft["payload"]["draft_sha256"],
            "fact_check_sha256": fact_check["content_sha256"],
            "verdict": verdict,
            "findings": list(output.get("findings", [])),
            "human_review_required": True,
            "human_approval": False,
            "published": False,
        }
        return _seal(
            ARTIFACT_KEYS["editorial_review"], story_id, draft["revision_id"], payload
        )

    raise HandoffError(f"Etapa sem handoff tipado: {stage}.")


def validate_handoff_chain(
    value: Mapping[str, Any],
    *,
    expected_story_id: str | None = None,
    expected_article: Mapping[str, Any] | None = None,
    require_pass: bool = False,
) -> dict[str, dict[str, Any]]:
    """Validate type, hash, lineage, and revision across all five handoffs."""
    if not isinstance(value, Mapping):
        raise HandoffError("Cadeia de handoffs precisa ser objeto.")
    chain = {
        key: validate_artifact(value.get(key), artifact_type)
        for key, artifact_type in ARTIFACT_KEYS.items()
    }
    story_ids = {artifact["story_id"] for artifact in chain.values()}
    if len(story_ids) != 1 or (expected_story_id is not None and story_ids != {expected_story_id}):
        raise HandoffError("A cadeia mistura artigos ou story_id inesperado.")
    dossier = chain["evidence_dossier"]
    brief = chain["editorial_brief"]
    draft = chain["story_draft"]
    fact_check = chain["fact_check_verdict"]
    review = chain["editorial_review"]
    dossier_evidence_ids = {
        row["evidence_id"] for row in dossier["payload"]["evidence"]
    }
    if brief["payload"].get("evidence_dossier_sha256") != dossier["content_sha256"]:
        raise HandoffError("EditorialBrief aponta para outro EvidenceDossier.")
    if draft["payload"].get("evidence_dossier_sha256") != dossier["content_sha256"]:
        raise HandoffError("StoryDraft aponta para outro EvidenceDossier.")
    if draft["payload"].get("editorial_brief_sha256") != brief["content_sha256"]:
        raise HandoffError("StoryDraft aponta para outro EditorialBrief.")
    if any(
        not set(section["evidence_ids"]).issubset(dossier_evidence_ids)
        for section in draft["payload"]["sections"]
    ):
        raise HandoffError("StoryDraft cita evidência fora do EvidenceDossier vigente.")
    draft_hash = draft["payload"].get("draft_sha256")
    if not isinstance(draft_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", draft_hash):
        raise HandoffError("StoryDraft não possui hash válido.")
    if fact_check["payload"].get("draft_sha256") != draft_hash:
        raise HandoffError("FactCheckVerdict está preso a uma revisão antiga.")
    if fact_check["payload"].get("evidence_dossier_sha256") != dossier["content_sha256"]:
        raise HandoffError("FactCheckVerdict aponta para outro EvidenceDossier.")
    if any(
        not set(finding["evidence_ids"]).issubset(dossier_evidence_ids)
        for finding in fact_check["payload"]["findings"]
    ):
        raise HandoffError("FactCheckVerdict cita evidência fora do EvidenceDossier vigente.")
    if review["payload"].get("draft_sha256") != draft_hash:
        raise HandoffError("EditorialReview está preso a uma revisão antiga.")
    if review["payload"].get("fact_check_sha256") != fact_check["content_sha256"]:
        raise HandoffError("EditorialReview aponta para outro FactCheckVerdict.")
    if len({draft["revision_id"], fact_check["revision_id"], review["revision_id"]}) != 1:
        raise HandoffError("Draft, fact check e review declaram revisões diferentes.")
    if review["payload"].get("human_review_required") is not True or review["payload"].get("human_approval") is not False:
        raise HandoffError("EditorialReview não preserva o gate humano.")
    if expected_article is not None and draft_hash != article_revision_sha256(expected_article):
        raise HandoffError("StoryDraft não corresponde ao texto enviado ao StoryPackage.")
    if require_pass and (
        fact_check["payload"].get("status") != "pass"
        or review["payload"].get("verdict") != "pass"
    ):
        raise HandoffError("Fact check ou revisão editorial mantém a pauta bloqueada.")
    return chain
