"""Typed, revision-bound editorial handoffs for the offline factory circuit."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

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
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffError(f"{field} precisa ser texto não vazio.")
    return value


def _validate_payload(artifact_type: str, payload: Mapping[str, Any]) -> None:
    if artifact_type == ARTIFACT_KEYS["evidence_dossier"]:
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
        if not _is_sha256(payload.get("evidence_dossier_sha256")):
            raise HandoffError("EditorialBrief exige hash válido do EvidenceDossier.")
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
    if artifact_type not in ARTIFACT_KEYS.values():
        raise HandoffError("Tipo de handoff editorial desconhecido.")
    if not story_id.strip() or not revision_id.strip():
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
    if artifact.get("schema_version") != SCHEMA_VERSION or artifact.get("artifact_type") not in ARTIFACT_KEYS.values():
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
