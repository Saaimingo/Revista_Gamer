"""Synthetic end-to-end factory path through one durable task dispatcher."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .db import Store, json_dumps, stable_hash
from .editorial import (
    EDITORIAL_PROFILE,
    EDITORIAL_TASK_TYPE,
    SOURCE_CITATION_PATTERN,
    article_revision_sha256,
    build_stage_input,
    normalize_source_packet,
    review_matches_revision,
    validate_stage_output,
)
from .editorial_handoffs import (
    ARTIFACT_KEYS,
    HandoffError,
    build_handoff_artifact,
    validate_handoff_chain,
)
from .agent_contracts import (
    AgentTaskEnvelope,
    ResearchPacket,
    envelope_from_payload,
    load_builtin_role_catalog,
    validate_json_schema,
)
from .agent_siwc import SIWCResponseArtifactStore
from .usage_meter import StoryVersionArchive
from .layout.contracts import (
    SCHEMA_MEDIA,
    SCHEMA_REFERENCE,
    SCHEMA_STORY,
    profile_sha256,
    seal_artifact,
    story_revision_sha256,
    validate_composition_validation,
    validate_layout_plan,
    validate_media_inventory,
    validate_story_package,
)
from .layout.engine import (
    build_visual_needs,
    plan_layout,
    render_preview,
    validate_plan,
    validate_rendered_preview,
)
from .layout.index import LayoutReferenceIndex
from .layout.pipeline import DEFAULT_FIXTURE
from .orchestration import (
    AgentProfile,
    AgentQueue,
    AgentTask,
    TaskDispatcher,
    TaskExecutionContext,
    TaskFailure,
)


FACTORY_FIXTURE = Path(__file__).parent / "fixtures" / "factory-demo.json"
FACTORY_E14_CASES_FIXTURE = Path(__file__).parent / "fixtures" / "factory-e14-cases.json"
FACTORY_EXECUTOR_ID = "synthetic-factory"
FACTORY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
LAYOUT_TASK_TYPE = "factory.layout_stage"
MEDIA_TASK_TYPE = "factory.media_inventory"
STORY_PACKAGE_TASK_TYPE = "factory.story_package"
PREVIEW_TASK_TYPE = "factory.internal_preview"
HUMAN_GATE_TASK_TYPE = "factory.simulated_human_gate"
PERSONA_DRAFT_BRIDGE_TASK_TYPE = "factory.persona_draft_bridge"
PERSONA_DRAFT_BRIDGE_EXECUTOR_ID = "factory-persona-draft-bridge"
FACTORY_TASK_ROUTES = {
    EDITORIAL_TASK_TYPE: FACTORY_EXECUTOR_ID,
    LAYOUT_TASK_TYPE: FACTORY_EXECUTOR_ID,
    MEDIA_TASK_TYPE: FACTORY_EXECUTOR_ID,
    STORY_PACKAGE_TASK_TYPE: FACTORY_EXECUTOR_ID,
    PREVIEW_TASK_TYPE: FACTORY_EXECUTOR_ID,
    HUMAN_GATE_TASK_TYPE: FACTORY_EXECUTOR_ID,
}
PERSONA_DRAFT_BRIDGE_PROFILE = AgentProfile(
    profile_id="persona-draft-factory-adapter",
    version="1.0.0",
    instructions=(
        "Valida e adapta uma resposta persona_writer já persistida; não chama SIWC, "
        "não pesquisa, não checa fatos, não aprova e não publica."
    ),
)

LAYOUT_PROFILE = AgentProfile(
    profile_id="synthetic-layout-engine",
    version="0.1.0",
    instructions="Executa somente funções determinísticas de composição sobre dados fictícios.",
)
MEDIA_PROFILE = AgentProfile(
    profile_id="synthetic-rights-inventory",
    version="0.1.0",
    instructions="Monta inventário local de placeholders sintéticos e direitos de prévia interna.",
)
PACKAGE_PROFILE = AgentProfile(
    profile_id="synthetic-contract-adapter",
    version="0.1.0",
    instructions="Converte saídas estruturadas em StoryPackage.v0 sem perder a proveniência de origem.",
)
GATE_PROFILE = AgentProfile(
    profile_id="fixture-human-approval-gate",
    version="0.1.0",
    instructions="Marca somente a decisão de aprovação humana explicitamente simulada pela fixture.",
)

_STAGE_ROLES = {
    "source_analysis": "researcher",
    "outline": "editor",
    "draft": "writer_persona",
    "fact_check": "reviewer",
    "review": "reviewer",
    "correction": "writer_persona",
    "final_fact_check": "reviewer",
    "final_review": "reviewer",
}

_FUNCTIONAL_STAGE_ROLES = {
    "source_analysis": "evidence_investigator",
    "outline": "assignment_editor",
    "draft": "persona_writer",
    "fact_check": "fact_checker",
    "review": "editorial_reviewer",
    "correction": "persona_writer",
    "final_fact_check": "fact_checker",
    "final_review": "editorial_reviewer",
}


class FactoryFixtureError(ValueError):
    """A synthetic fixture is malformed or contains a non-synthetic decision."""


@dataclass(frozen=True)
class FactoryStoryRun:
    """One isolated story fixture composed into a shared multipauta run."""

    run_id: str
    fixture_path: Path
    review_flow: str = "pass"
    source_disagreement: bool = False
    research_packet: ResearchPacket | Mapping[str, Any] | None = None
    research_source_bindings: Mapping[str, str] | None = None


def _build_factory_dispatcher(queue: AgentQueue) -> TaskDispatcher:
    return TaskDispatcher(
        queue,
        executors={FACTORY_EXECUTOR_ID: SyntheticFactoryExecutor(artifact_dir=queue.store.artifact_dir)},
        profiles={
            (profile.profile_id, profile.version): profile
            for profile in (EDITORIAL_PROFILE, LAYOUT_PROFILE, MEDIA_PROFILE, PACKAGE_PROFILE, GATE_PROFILE)
        },
    )


def _load_fixture(path: Path | None = None) -> dict[str, Any]:
    fixture_path = path or FACTORY_FIXTURE
    with fixture_path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict) or value.get("fixture_version") != "SyntheticFactoryFixture.v0":
        raise FactoryFixtureError("Fixture precisa usar SyntheticFactoryFixture.v0.")
    if not FACTORY_ID_RE.fullmatch(str(value.get("run_id", ""))):
        raise FactoryFixtureError("run_id da fixture é inválido.")
    if value.get("simulated_human_decision") not in {"approve_internally", "hold"}:
        raise FactoryFixtureError("A decisão humana da fixture deve ser approve_internally ou hold.")
    normalize_source_packet({
        key: value[key]
        for key in ("article_type", "topic", "research_note", "sources")
    })
    case = value.get("e14_case")
    if case is not None:
        if not isinstance(case, Mapping) or case.get("case_type") not in {
            "attributed_rumor", "hardware", "game_mod",
        }:
            raise FactoryFixtureError("e14_case precisa declarar um tipo de caso conhecido.")
        required_case_fields = (
            "genre", "angle", "claim", "assessment", "headline", "dek",
            "section_heading", "section_focus", "body_markdown", "fact_claim", "source_ids",
        )
        if any(not isinstance(case.get(field), str) or not case[field].strip() for field in required_case_fields[:-1]):
            raise FactoryFixtureError("e14_case contém texto obrigatório vazio ou inválido.")
        if case.get("genre") not in {"news", "rumor", "investigation", "analysis", "review", "guide"}:
            raise FactoryFixtureError("e14_case.genre fora do contrato funcional.")
        if case.get("assessment") not in {"supported", "uncertain", "rumor", "contradicted"}:
            raise FactoryFixtureError("e14_case.assessment fora do contrato editorial.")
        if not isinstance(case.get("source_ids"), list) or not case["source_ids"] or any(
            not isinstance(item, str) for item in case["source_ids"]
        ):
            raise FactoryFixtureError("e14_case.source_ids precisa listar fontes da fixture.")
        if not set(case["source_ids"]).issubset(_source_ids(_packet(value))):
            raise FactoryFixtureError("e14_case cita ID ausente do pacote de evidências.")
        if case.get("fact_status", "supported") not in {"supported", "uncertain", "contradicted", "unsupported"}:
            raise FactoryFixtureError("e14_case.fact_status fora do contrato de checagem.")
        correction_body = case.get("correction_body_markdown")
        if correction_body is not None and (
            not isinstance(correction_body, str) or not correction_body.strip()
            or correction_body == case.get("body_markdown")
        ):
            raise FactoryFixtureError("e14_case.correction_body_markdown precisa criar um texto corrigido distinto.")
        if case.get("case_type") == "attributed_rumor" and case.get("assessment") != "rumor":
            raise FactoryFixtureError("Caso de rumor precisa manter epistemic status rumor.")
        if case.get("case_type") == "attributed_rumor" and case.get("genre") != "rumor":
            raise FactoryFixtureError("Caso de rumor precisa usar gênero rumor.")
    identities = value.get("identities")
    if not isinstance(identities, Mapping) or set(identities) != {
        "editor", "writer_persona", "reviewer",
    }:
        raise FactoryFixtureError("A fixture precisa declarar as três identidades A4 exigidas.")
    for role, identity in identities.items():
        if not isinstance(identity, Mapping) or not all(
            isinstance(identity.get(field), str) and identity[field].strip()
            for field in ("profile_id", "version", "description")
        ):
            raise FactoryFixtureError(f"Identidade sintética inválida: {role}.")
    identity_ids = [str(identity["profile_id"]) for identity in identities.values()]
    if len(set(identity_ids)) != len(identity_ids):
        raise FactoryFixtureError("Os perfis sintéticos de editor, redator e revisor devem ser distintos.")
    figure = value.get("synthetic_figure")
    if not isinstance(figure, Mapping) or not all(
        isinstance(figure.get(field), str) and figure[field].strip()
        for field in ("asset_id", "block_id_suffix", "caption", "alt_text")
    ):
        raise FactoryFixtureError("A fixture precisa identificar um placeholder sintético completo.")
    return value


def _packet(fixture: Mapping[str, Any]) -> dict[str, Any]:
    return normalize_source_packet({
        key: fixture[key]
        for key in ("article_type", "topic", "research_note", "sources")
    })


def _source_ids(packet: Mapping[str, Any]) -> set[str]:
    return {str(source["id"]) for source in packet["sources"]}


def role_story_draft_to_editorial_output(
    role_output: Mapping[str, Any],
    *,
    evidence_rows: Sequence[Mapping[str, Any]],
    valid_source_ids: set[str],
) -> dict[str, Any]:
    """Adapt a validated persona StoryDraft to the factory's article-stage shape.

    The adapter preserves the agent's section text and adds inline source markers
    from its evidence references. It fails closed when a reference cannot be
    mapped through the supplied EvidenceDossier.
    """
    if not isinstance(role_output, Mapping):
        raise TaskFailure("factory_storydraft_invalid", "StoryDraft do papel precisa ser um objeto.", blocked=True)

    evidence_to_source: dict[str, str] = {}
    for row in evidence_rows:
        if not isinstance(row, Mapping):
            raise TaskFailure("factory_storydraft_evidence_invalid", "EvidenceDossier contém item inválido.", blocked=True)
        evidence_id = row.get("evidence_id")
        source_id = row.get("source_id")
        if not isinstance(evidence_id, str) or not evidence_id or not isinstance(source_id, str):
            raise TaskFailure("factory_storydraft_evidence_invalid", "EvidenceDossier não vincula evidence_id a source_id.", blocked=True)
        if source_id not in valid_source_ids:
            raise TaskFailure("factory_storydraft_source_invalid", "EvidenceDossier aponta para fonte fora do pacote corrente.", blocked=True)
        previous_source = evidence_to_source.get(evidence_id)
        if previous_source is not None and previous_source != source_id:
            raise TaskFailure("factory_storydraft_evidence_ambiguous", "EvidenceDossier vincula uma evidência a fontes divergentes.", blocked=True)
        evidence_to_source[evidence_id] = source_id

    sections = role_output.get("sections")
    if not isinstance(sections, list) or not sections:
        raise TaskFailure("factory_storydraft_sections_missing", "StoryDraft precisa conter seções.", blocked=True)

    body_sections: list[str] = []
    ordered_source_ids: list[str] = []
    for section in sections:
        if not isinstance(section, Mapping):
            raise TaskFailure("factory_storydraft_section_invalid", "StoryDraft contém seção inválida.", blocked=True)
        heading = section.get("heading")
        body = section.get("body")
        evidence_ids = section.get("evidence_ids")
        if (
            not isinstance(heading, str) or not heading.strip()
            or not isinstance(body, str) or not body.strip()
            or not isinstance(evidence_ids, list) or not evidence_ids
            or any(not isinstance(item, str) for item in evidence_ids)
        ):
            raise TaskFailure("factory_storydraft_section_invalid", "Seção do StoryDraft precisa de título, texto e evidências.", blocked=True)

        section_source_ids: list[str] = []
        for evidence_id in evidence_ids:
            source_id = evidence_to_source.get(evidence_id)
            if source_id is None:
                raise TaskFailure("factory_storydraft_unknown_evidence", "StoryDraft cita evidence_id ausente do EvidenceDossier.", blocked=True)
            if source_id not in section_source_ids:
                section_source_ids.append(source_id)
            if source_id not in ordered_source_ids:
                ordered_source_ids.append(source_id)

        existing_citations = set(SOURCE_CITATION_PATTERN.findall(body))
        if not existing_citations.issubset(section_source_ids):
            raise TaskFailure("factory_storydraft_citation_mismatch", "Citação inline não corresponde às evidências da seção.", blocked=True)
        missing_citations = [source_id for source_id in section_source_ids if source_id not in existing_citations]
        rendered_body = f"## {heading.strip()}\n\n{body.strip()}"
        if missing_citations:
            rendered_body += " " + " ".join(f"[{source_id}]" for source_id in missing_citations)
        body_sections.append(rendered_body)

    converted = {
        "headline": role_output.get("title"),
        "dek": role_output.get("dek"),
        "body_markdown": "\n\n".join(body_sections),
        "source_ids": ordered_source_ids,
    }
    return validate_stage_output("draft", converted, valid_source_ids)


def _editorial_output(
    stage: str,
    packet: Mapping[str, Any],
    previous: Mapping[str, Any],
    *,
    review_flow: str = "pass",
    source_disagreement: bool = False,
    case: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    case = case or {}
    ids = [str(source["id"]) for source in packet["sources"]]
    if stage == "source_analysis":
        source = packet["sources"][0]
        assessment = "uncertain" if source_disagreement else str(case.get("assessment", "supported"))
        return {"claims": [{
            "claim_id": "fictional-claim-01",
            "claim": (
                "As fontes fictícias divergem sobre a exploração solo e os mapas desenhados à mão."
                if source_disagreement else
                str(case.get("claim") or "Farol de Papel é um jogo fictício de exploração solo com mapas desenhados à mão.")
            ),
            "source_ids": list(case.get("source_ids") or ids),
            "evidence_excerpt": source["evidence"],
            "assessment": assessment,
            "confidence": "low" if assessment == "rumor" else "medium" if assessment == "uncertain" else "high",
            "caveat": (
                "A divergência precisa permanecer explícita; a fixture não descreve um jogo real."
                if source_disagreement else str(case.get("caveat") or "A fixture não descreve um produto real.")
            ),
        }]}
    if stage == "outline":
        return {
            "headline": str(case.get("headline") or "Farol de Papel: exploração em mapas feitos à mão"),
            "dek": str(case.get("dek") or "Uma pauta fictícia demonstra como organizar evidência sem inventar uma data de lançamento."),
            "sections": [{
                "heading": str(case.get("section_heading") or "Descoberta sem pressa"),
                "focus": str(case.get("section_focus") or "Apresentar a proposta imaginária e registrar o limite do que as fontes dizem."),
                "source_ids": list(case.get("source_ids") or ids),
            }],
        }
    if stage == "draft":
        if case:
            return {
                "headline": case["headline"],
                "dek": case["dek"],
                "body_markdown": case["body_markdown"],
                "source_ids": list(case["source_ids"]),
            }
        return {
            "headline": "Farol de Papel: exploração em mapas feitos à mão",
            "dek": "Uma pauta fictícia demonstra como organizar evidência sem inventar uma data de lançamento.",
            "body_markdown": (
                "Farol de Papel existe apenas nesta fixture e serve para testar uma cadeia editorial offline. "
                "No cenário inventado, o projeto propõe exploração solo em mapas desenhados à mão, uma ideia "
                "que aproxima navegação e descoberta sem depender de competição entre jogadores [S1]. A cobertura "
                "secundária fictícia descreve a mesma combinação e também ressalta que não há data de lançamento "
                "informada [S2]. Por isso, este rascunho não atribui calendário, plataforma, preço ou recursos que "
                "as fontes não mencionam. O pacote demonstra como uma pauta curta pode separar o que foi declarado "
                "do que ainda falta saber. Os nomes, as publicações e o jogo são inventados para o ensaio; nenhuma "
                "afirmação deve ser lida como notícia real. A matéria preserva as referências por IDs estruturados, "
                "para que a revisão possa conferir cada frase sem buscar material externo."
            ),
            "source_ids": ids,
        }
    if stage in {"fact_check", "final_fact_check"}:
        article = previous["draft"] if stage == "fact_check" else previous["correction"]
        fact_status = "uncertain" if source_disagreement else str(case.get("fact_status", "supported"))
        return {"findings": [{
            "claim": (
                "As fontes fictícias divergem sobre mapas desenhados à mão e exploração solo."
                if source_disagreement else
                str(case.get("fact_claim") or "As fontes fictícias descrevem mapas desenhados à mão e exploração solo.")
            ),
            "source_ids": list(case.get("source_ids") or ids),
            "status": fact_status,
            "confidence": "low" if fact_status == "uncertain" else "high",
            "correction": (
                "Preservar a divergência e pedir decisão editorial."
                if source_disagreement else str(case.get("fact_correction", ""))
            ),
        }]}
    if stage in {"review", "final_review"}:
        if stage == "review" and source_disagreement:
            return {
                "verdict": "hold",
                "findings": ["As fontes fictícias divergem; falta decisão editorial para resolver a afirmação."],
                "human_review_required": True,
            }
        if stage == "review" and review_flow == "hold":
            return {
                "verdict": "hold",
                "findings": ["A fixture mantém a pauta em espera para decisão humana."],
                "human_review_required": True,
            }
        if stage == "review" and review_flow == "revise":
            return {
                "verdict": "revise",
                "findings": ["Esclarecer o que a nota secundária fictícia afirma e preservar o limite sobre a data."],
                "human_review_required": True,
            }
        return {"verdict": "pass", "findings": [], "human_review_required": True}
    if stage == "correction":
        article = previous["draft"]
        original_sentence = (
            "A cobertura secundária fictícia descreve a mesma combinação e também ressalta que não há data de lançamento informada [S2]."
        )
        corrected_sentence = (
            "A nota secundária fictícia também descreve mapas desenhados à mão e exploração solo, sem informar data de lançamento [S2]."
        )
        return {
            "headline": article["headline"],
            "dek": article["dek"],
            "body_markdown": str(
                case.get("correction_body_markdown")
                or article["body_markdown"].replace(original_sentence, corrected_sentence)
            ),
            "source_ids": article["source_ids"],
            "remaining_issues": [],
            "human_review_required": True,
        }
    raise TaskFailure("factory_stage_unknown", "Etapa sintética desconhecida.", blocked=True)


def _identity_for_stage(fixture: Mapping[str, Any], stage: str) -> dict[str, Any]:
    role = _STAGE_ROLES[stage]
    if role == "researcher":
        return {
            "role": role,
            "profile_id": "synthetic-researcher",
            "version": "0.1.0",
            "description": "Pesquisadora fictícia que organiza somente evidência da fixture.",
        }
    return {"role": role, **dict(fixture["identities"][role])}


def _build_story_package(payload: Mapping[str, Any]) -> dict[str, Any]:
    article = payload["article"]
    review = payload["review"]
    outline = payload["outline"]
    fixture = payload["fixture"]
    packet = payload["packet"]
    content_identities = payload["content_identities"]
    story_id = f"story-{fixture['run_id']}"
    try:
        handoff_chain = validate_handoff_chain(
            payload.get("editorial_handoffs", {}),
            expected_story_id=story_id,
            expected_article=article,
            require_pass=True,
        )
    except HandoffError as error:
        raise TaskFailure(
            "factory_typed_handoff_not_current",
            f"Cadeia EvidenceDossier→Review bloqueada: {error}",
            blocked=True,
        ) from error
    revision_stage = review.get("reviewed_revision_stage")
    if review.get("verdict") != "pass" or not review_matches_revision(review, article):
        raise TaskFailure(
            "factory_review_not_current",
            "A revisão B2 não corresponde ao artigo corrente; StoryPackage não será criado.",
            blocked=True,
        )
    if revision_stage not in {"draft", "correction"}:
        raise TaskFailure(
            "factory_review_stage_mismatch", "A revisão deve apontar para o rascunho ou correção corrente.", blocked=True
        )
    if revision_stage == "correction":
        final_fact_check = payload.get("final_fact_check")
        if not isinstance(final_fact_check, Mapping) or final_fact_check.get(
            "checked_revision_sha256"
        ) != article_revision_sha256(article):
            raise TaskFailure(
                "factory_fact_check_not_current",
                "A checagem final não corresponde à correção vigente; StoryPackage não será criado.",
                blocked=True,
            )
    story_revision = 2 if revision_stage == "correction" else 1
    figure = fixture["synthetic_figure"]
    revision_prefix = f"{story_id}-r{story_revision}"
    figure_block_id = f"{revision_prefix}-{figure['block_id_suffix']}"
    sections = [
        {
            "block_id": f"{revision_prefix}-heading-01",
            "kind": "heading",
            "text": outline["sections"][0]["heading"],
            "source_ids": list(outline["sections"][0]["source_ids"]),
        },
        {
            "block_id": f"{revision_prefix}-body-01",
            "kind": "paragraph",
            "text": article["body_markdown"],
            "source_ids": list(article["source_ids"]),
        },
        {
            "block_id": figure_block_id,
            "kind": "figure_request",
            "text": "Área visual reservada a um placeholder sintético, sem imagem ou referência a jogo real.",
            "source_ids": [],
            "figures": [{
                "asset_id": figure["asset_id"],
                "caption": figure["caption"],
                "alt_text": figure["alt_text"],
            }],
        },
    ]
    packet_source_ids = [str(source["id"]) for source in packet["sources"]]
    required_roles = {"editor", "writer_persona", "reviewer"}
    if not isinstance(content_identities, Mapping) or set(content_identities) != required_roles:
        raise TaskFailure("factory_identity_lineage_invalid", "Identidades de conteúdo ausentes ou extras.", blocked=True)
    for role in required_roles:
        expected = {"role": role, **dict(fixture["identities"][role])}
        if dict(content_identities[role]) != expected:
            raise TaskFailure("factory_identity_lineage_invalid", f"Identidade de {role} divergiu da fixture.", blocked=True)
    story_payload: dict[str, Any] = {
        "story_id": story_id,
        "edition_id": f"edition-{fixture['run_id']}",
        "story_revision": story_revision,
        "title": article["headline"],
        "dek": article["dek"],
        "sections": sections,
        "source_ids": list(article["source_ids"]),
        "identities": {role: dict(content_identities[role]) for role in (
            "editor", "writer_persona", "reviewer",
        )},
        "editorial_provenance": {
            "article_revision_sha256": article_revision_sha256(article),
            "reviewed_revision_sha256": review["reviewed_revision_sha256"],
            "reviewed_revision_stage": review["reviewed_revision_stage"],
            "story_revision": story_revision,
            "source_ids": packet_source_ids,
            "synthetic_fixture_only": True,
            "typed_handoffs": {
                key: handoff_chain[key]["content_sha256"]
                for key in ARTIFACT_KEYS
            },
            "epistemic_claims": [dict(claim) for claim in handoff_chain["evidence_dossier"]["payload"]["claims"]],
        },
        "review": {},
    }
    if not set(story_payload["source_ids"]).issubset(set(packet_source_ids)):
        raise TaskFailure("factory_source_lineage_invalid", "O artigo cita ID ausente do pacote.", blocked=True)
    story_payload["review"] = {
        "verdict": "pass",
        "reviewed_story_sha256": story_revision_sha256(story_payload),
        "reviewed_article_revision_sha256": review["reviewed_revision_sha256"],
        "reviewed_revision_stage": review["reviewed_revision_stage"],
        "reviewer_profile_id": story_payload["identities"]["reviewer"]["profile_id"],
        "reviewer_profile_version": story_payload["identities"]["reviewer"]["version"],
        "review_kind": "synthetic_contract_bridge",
        "editorial_review_sha256": handoff_chain["editorial_review"]["content_sha256"],
        "human_approval": False,
        "synthetic_fixture": True,
    }
    story = seal_artifact(story_id, SCHEMA_STORY, story_revision, story_payload)
    return validate_story_package(story)


def _build_media_inventory(payload: Mapping[str, Any]) -> dict[str, Any]:
    fixture = payload["fixture"]
    story_id = f"story-{fixture['run_id']}"
    figure = fixture["synthetic_figure"]
    story_revision = int(payload.get("story_revision", 1))
    revision_prefix = f"{story_id}-r{story_revision}"
    rights_status = str(figure.get("test_rights_status", "synthetic_fixture"))
    license_status = str(figure.get("test_license_status", "not_applicable_synthetic_placeholder"))
    permitted_modes = list(figure.get("test_permitted_modes", ["internal_preview"]))
    inventory_payload = {
        "inventory_id": f"media-inventory-{fixture['run_id']}",
        "assets": [{
            "asset_id": figure["asset_id"],
            "media_kind": "placeholder",
            "rights_status": rights_status,
            "rights_holder": "SyntheticFactoryFixture.v0",
            "origin": "Placeholder textual definido pela fixture; sem bytes de imagem.",
            "credit": "Ativo fictício de validação interna.",
            "permitted_transformations": [],
            "linked_block_ids": [f"{revision_prefix}-{figure['block_id_suffix']}"],
            "license": {"status": license_status},
            "asset_sha256": None,
            "dimensions": None,
            "permitted_modes": permitted_modes,
            "synthetic": rights_status == "synthetic_fixture",
        }],
    }
    artifact = seal_artifact(
        inventory_payload["inventory_id"], SCHEMA_MEDIA, 1, inventory_payload
    )
    return validate_media_inventory(artifact)


def _seed_reference_index(index: LayoutReferenceIndex) -> None:
    with DEFAULT_FIXTURE.open("r", encoding="utf-8") as stream:
        fixture = json.load(stream)
    references = [
        seal_artifact(
            str(payload["reference_id"]), SCHEMA_REFERENCE,
            int(payload["revision"]), payload,
        )
        for payload in fixture["references"]
    ]
    index.add_references(references)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class SyntheticFactoryExecutor:
    """Offline executor for editorial, contract, layout and simulated gate tasks."""

    executor_id = FACTORY_EXECUTOR_ID

    def __init__(self, *, artifact_dir: Path):
        self.artifact_dir = artifact_dir.resolve()

    def execute(
        self,
        task: AgentTask,
        profile: AgentProfile,
        context: TaskExecutionContext,
    ) -> Mapping[str, Any]:
        payload = task.payload
        if task.task_type == EDITORIAL_TASK_TYPE:
            return self._editorial(task, profile, payload)
        if task.task_type == MEDIA_TASK_TYPE:
            return {"media_inventory": _build_media_inventory(payload)}
        if task.task_type == STORY_PACKAGE_TASK_TYPE:
            return {"story_package": _build_story_package(payload)}
        if task.task_type == LAYOUT_TASK_TYPE:
            return self._layout(payload)
        if task.task_type == PREVIEW_TASK_TYPE:
            return self._persist_preview(payload)
        if task.task_type == HUMAN_GATE_TASK_TYPE:
            return self._human_gate(payload)
        raise TaskFailure("factory_task_unknown", "Tipo de tarefa fora da esteira sintética.", blocked=True)

    @staticmethod
    def _editorial(
        task: AgentTask, profile: AgentProfile, payload: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        if profile.content_hash != EDITORIAL_PROFILE.content_hash:
            raise TaskFailure("factory_profile_mismatch", "Perfil B2 de execução divergiu.", blocked=True)
        stage = str(payload.get("stage", ""))
        expected_role_id = _FUNCTIONAL_STAGE_ROLES.get(stage)
        functional_role_id = str(payload.get("functional_role_id", ""))
        if expected_role_id is None or functional_role_id != expected_role_id:
            raise TaskFailure("factory_functional_role_mismatch", "Papel funcional não corresponde à etapa.", blocked=True)
        role_catalog = load_builtin_role_catalog()
        role_rows = role_catalog.to_mapping()["profiles"]
        role_row = next((row for row in role_rows if row["role_id"] == functional_role_id), None)
        if role_row is None:
            raise TaskFailure("factory_functional_role_missing", "Papel funcional ausente no catálogo versionado.", blocked=True)
        try:
            role_profile = role_catalog.resolve(
                functional_role_id, role_row["role_version"], role_row["profile_sha256"]
            )
        except (ValueError, KeyError) as error:
            raise TaskFailure("factory_functional_role_blocked", "Papel funcional não habilitado ou hash inválido.", blocked=True) from error
        packet = normalize_source_packet(payload.get("packet", {}))
        previous = payload.get("previous_outputs", {})
        if not isinstance(previous, Mapping):
            raise TaskFailure("factory_previous_output_invalid", "Saídas anteriores inválidas.", blocked=True)
        handoffs = payload.get("handoffs", {})
        if not isinstance(handoffs, Mapping):
            raise TaskFailure("factory_handoffs_invalid", "Handoffs anteriores inválidos.", blocked=True)
        build_stage_input(stage=stage, packet=packet, previous_outputs=previous)
        structured = validate_stage_output(
            stage,
            _editorial_output(
                stage,
                packet,
                previous,
                review_flow=str(payload.get("review_flow", "pass")),
                source_disagreement=bool(payload.get("source_disagreement", False)),
                case=payload.get("e14_case"),
            ),
            _source_ids(packet),
        )
        if stage in {"review", "final_review"}:
            revision_stage = "draft" if stage == "review" else "correction"
            structured["reviewed_revision_sha256"] = article_revision_sha256(previous[revision_stage])
            structured["reviewed_revision_stage"] = revision_stage
        elif stage == "final_fact_check":
            structured["checked_revision_sha256"] = article_revision_sha256(previous["correction"])
        artifact_output = dict(structured)
        if stage == "fact_check":
            artifact_output["article_for_check"] = previous["draft"]
        elif stage == "final_fact_check":
            artifact_output["article_for_check"] = previous["correction"]
        elif stage == "review":
            artifact_output["article_for_review"] = previous["draft"]
        elif stage == "final_review":
            artifact_output["article_for_review"] = previous["correction"]
        try:
            handoff_artifact = build_handoff_artifact(
                stage,
                run_id=str(payload.get("run_id", "")),
                packet=packet,
                output=artifact_output,
                inputs=handoffs,
                content_identity=payload.get("content_identity", {}),
                case=payload.get("e14_case"),
            )
        except (HandoffError, KeyError, TypeError, ValueError) as error:
            raise TaskFailure("factory_editorial_handoff_invalid", str(error), blocked=True) from error
        upstream_handoff_hashes = {
            key: value.get("content_sha256")
            for key, value in handoffs.items()
            if isinstance(value, Mapping)
        }
        return {
            "structured_output": structured,
            "handoff_artifact": handoff_artifact,
            "functional_role": {
                "role_id": role_profile.role_id,
                "role_version": role_profile.role_version,
                "role_hash": role_profile.content_hash,
            },
            "upstream_handoff_hashes": upstream_handoff_hashes,
            "stage": stage,
            "actor_role": payload.get("actor_role"),
            "content_identity": dict(payload.get("content_identity", {})),
            "executor_profile": {
                "profile_id": profile.profile_id,
                "version": profile.version,
                "content_hash": profile.content_hash,
            },
            "human_review_required": True,
            "publication_state": "not_published",
            "synthetic_fixture_only": True,
        }

    def _layout(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        stage = str(payload.get("stage", ""))
        if stage == "visual_needs":
            return {"visual_needs": build_visual_needs(payload["story_package"])}
        if stage == "references":
            references = list(payload.get("references", []))
            if len(references) != 3:
                raise TaskFailure("factory_references_missing", "São necessárias três referências sintéticas.", blocked=True)
            return {"references": references, "reference_index_sha256": payload["reference_index_sha256"]}
        if stage == "layout_plan":
            plan = plan_layout(
                payload["story_package"], payload["media_inventory"],
                payload["visual_needs"], payload["references"],
                str(payload["reference_index_sha256"]),
            )
            return {"layout_plan": validate_layout_plan(plan)}
        if stage == "composition_validation":
            validation = validate_plan(
                payload["story_package"], payload["media_inventory"],
                payload["layout_plan"], str(payload["reference_index_sha256"]),
                payload["indexed_references"],
            )
            return {"composition_validation": validate_composition_validation(validation)}
        if stage == "render":
            html = render_preview(
                payload["story_package"], payload["layout_plan"],
                payload["composition_validation"],
            )
            return {
                "preview_html": html,
                "preview_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
                "internal_only": True,
            }
        if stage == "render_validation":
            validation = validate_rendered_preview(
                payload["story_package"], payload["layout_plan"],
                payload["composition_validation"], payload["preview_html"],
            )
            return {"composition_validation": validate_composition_validation(validation)}
        raise TaskFailure("factory_layout_stage_unknown", "Etapa de layout desconhecida.", blocked=True)

    def _persist_preview(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        validation = validate_composition_validation(payload["composition_validation"])
        preview_html = str(payload["preview_html"])
        digest = hashlib.sha256(preview_html.encode("utf-8")).hexdigest()
        expected = validation["payload"].get("rendered_preview_sha256")
        story_hash = story_revision_sha256(payload["story_package"]["payload"])
        if (
            validation["payload"].get("status") != "PASS"
            or digest != expected
            or validation["payload"].get("story_revision_sha256") != story_hash
        ):
            raise TaskFailure("factory_preview_gate_failed", "Prévia não confere com a validação atual.", blocked=True)
        run_id = str(payload["run_id"])
        if not FACTORY_ID_RE.fullmatch(run_id):
            raise TaskFailure("factory_run_id_invalid", "run_id inválido para artefatos.", blocked=True)
        preview_path = self.artifact_dir / "factory-demo" / run_id / f"internal-preview-{digest[:16]}.html"
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(preview_html, encoding="utf-8")
        return {
            "preview_path": str(preview_path),
            "preview_sha256": digest,
            "story_revision_sha256": story_hash,
            "internal_only": True,
            "published": False,
        }

    @staticmethod
    def _human_gate(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        validation = validate_composition_validation(payload["composition_validation"])
        preview = payload["internal_preview"]
        story_hash = str(payload.get("story_revision_sha256", ""))
        if validation["payload"].get("status") != "PASS" or preview.get("internal_only") is not True:
            raise TaskFailure("factory_human_gate_closed", "O gate simulado exige prévia interna validada.", blocked=True)
        if payload.get("preview_sha256") != preview.get("preview_sha256"):
            raise TaskFailure("factory_preview_hash_mismatch", "A prévia não corresponde ao hash validado.", blocked=True)
        if (
            not story_hash
            or validation["payload"].get("story_revision_sha256") != story_hash
            or preview.get("story_revision_sha256") != story_hash
        ):
            raise TaskFailure("factory_story_revision_mismatch", "O gate não corresponde à revisão atual da matéria.", blocked=True)
        if payload.get("decision") == "hold":
            return {
                "status": "simulated_on_hold",
                "actor": "fixture-human-approver",
                "simulated": True,
                "publication_state": "not_published",
                "published": False,
            }
        if payload.get("decision") != "approve_internally":
            raise TaskFailure("factory_human_decision_invalid", "Decisão simulada não autorizada.", blocked=True)
        return {
            "status": "simulated_approved_internally",
            "actor": "fixture-human-approver",
            "simulated": True,
            "preview_sha256": preview["preview_sha256"],
            "story_revision_sha256": story_hash,
            "publication_state": "not_published",
            "published": False,
        }


class PersonaDraftFactoryBridgeExecutor:
    """Adapt a completed private persona draft without copying its text into SQLite."""

    executor_id = PERSONA_DRAFT_BRIDGE_EXECUTOR_ID

    def __init__(self, *, artifact_root: Path, role_catalog: Any):
        self.artifact_root = Path(artifact_root).expanduser().resolve()
        self.role_catalog = role_catalog

    def execute(
        self,
        task: AgentTask,
        profile: AgentProfile,
        context: TaskExecutionContext,
    ) -> Mapping[str, Any]:
        if profile.content_hash != PERSONA_DRAFT_BRIDGE_PROFILE.content_hash:
            raise TaskFailure("factory_persona_bridge_profile_mismatch", "Perfil do adaptador de persona divergiu.", blocked=True)
        if task.task_type != PERSONA_DRAFT_BRIDGE_TASK_TYPE:
            raise TaskFailure("factory_persona_bridge_route_mismatch", "Tipo fora da rota do adaptador de persona.", blocked=True)
        payload = task.payload
        if set(payload) != {"stage", "role_task_id", "evidence_rows", "valid_source_ids"} or payload.get("stage") != "draft":
            raise TaskFailure("factory_persona_bridge_payload_invalid", "Payload precisa conter somente referências e IDs de evidência.", blocked=True)
        role_task_id = payload.get("role_task_id")
        if not isinstance(role_task_id, str) or not role_task_id:
            raise TaskFailure("factory_persona_bridge_parent_missing", "role_task_id é obrigatório.", blocked=True)
        parent = context.queue.get(role_task_id)
        if parent is None or parent.state != "succeeded" or parent.task_type != "agent.role.persona_writer" or parent.result is None:
            raise TaskFailure("factory_persona_bridge_parent_unavailable", "A tarefa persona_writer precisa estar concluída no mesmo ledger.", blocked=True)
        try:
            envelope: AgentTaskEnvelope = envelope_from_payload(parent.payload)
            role = self.role_catalog.validate_task(envelope, input_payload=parent.payload.get("input"))
            result = self.role_catalog.validate_result(envelope, parent.result, role).to_dict()
        except (ValueError, TypeError, KeyError) as error:
            raise TaskFailure("factory_persona_bridge_contract_invalid", f"Contrato original não pôde ser revalidado ({type(error).__name__}).", blocked=True) from None
        if envelope.role_id != "persona_writer" or envelope.task_id != parent.task_id:
            raise TaskFailure("factory_persona_bridge_role_mismatch", "A origem precisa ser o persona_writer registrado no catálogo.", blocked=True)
        if result.get("status") != "completed" or result.get("requested_research") is not None:
            raise TaskFailure("factory_persona_bridge_research_pending", "Rascunho com pesquisa solicitada ou pendente não pode seguir para a fábrica.", blocked=True)
        artifact_ref = result.get("artifact_ref")
        if not isinstance(artifact_ref, Mapping) or not isinstance(artifact_ref.get("ref"), str) or not isinstance(artifact_ref.get("sha256"), str):
            raise TaskFailure("factory_persona_bridge_raw_ref_missing", "Resultado original não referencia resposta bruta com hash.", blocked=True)
        try:
            raw_response = SIWCResponseArtifactStore(self.artifact_root).read_response(
                artifact_ref["ref"], artifact_ref["sha256"],
            )
            role_output = json.loads(raw_response.decode("utf-8"))
            validate_json_schema(role_output, role.output_schema)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as error:
            raise TaskFailure("factory_persona_bridge_raw_invalid", f"Resposta bruta não confere com o contrato ({type(error).__name__}).", blocked=True) from None
        if not isinstance(role_output, Mapping) or role_output.get("requested_research") not in (None, []):
            raise TaskFailure("factory_persona_bridge_research_pending", "Saída original contém pesquisa ainda não resolvida.", blocked=True)

        story_id = envelope.story_id
        story_key = hashlib.sha256(story_id.encode("utf-8")).hexdigest()[:32]
        story_dir = (self.artifact_root / "story-versions" / story_key).resolve()
        if not story_dir.is_relative_to(self.artifact_root) or not story_dir.is_dir():
            raise TaskFailure("factory_persona_bridge_archive_missing", "Arquivo privado da matéria não existe sob a raiz configurada.", blocked=True)
        manifests: list[tuple[Path, dict[str, Any]]] = []
        for manifest_path in story_dir.glob("**/manifest.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if manifest.get("task_id") == parent.task_id:
                manifests.append((manifest_path, manifest))
        if len(manifests) != 1:
            raise TaskFailure("factory_persona_bridge_archive_ambiguous", "A origem precisa ter exatamente um manifesto imutável no arquivo privado.", blocked=True)
        manifest_path, manifest = manifests[0]
        try:
            raw_archive = (self.artifact_root / manifest["raw_response_ref"]).resolve()
            full_text_path = (self.artifact_root / manifest["full_text_ref"]).resolve()
            if not raw_archive.is_relative_to(self.artifact_root) or not full_text_path.is_relative_to(self.artifact_root):
                raise ValueError("referência de arquivo fora da raiz")
            archived_raw = raw_archive.read_bytes()
            full_text = full_text_path.read_bytes()
        except (KeyError, OSError, TypeError, ValueError) as error:
            raise TaskFailure("factory_persona_bridge_archive_invalid", f"Arquivo privado incompleto ({type(error).__name__}).", blocked=True) from None
        if (
            manifest.get("schema_version") != "StoryVersionArtifact.v1"
            or manifest.get("story_id") != story_id
            or manifest.get("persona_id") != envelope.persona_id
            or manifest.get("persona_version") != envelope.persona_version
            or manifest.get("persona_hash") != envelope.persona_hash
            or manifest.get("published") is not False
            or manifest.get("human_evaluation_status") != "pending"
            or manifest.get("raw_response_sha256") != hashlib.sha256(raw_response).hexdigest()
            or hashlib.sha256(archived_raw).digest() != hashlib.sha256(raw_response).digest()
            or manifest.get("full_text_sha256") != hashlib.sha256(full_text).hexdigest()
            or StoryVersionArchive._render(role_output).encode("utf-8") != full_text
            or artifact_ref.get("sha256") != result.get("output_hash")
        ):
            raise TaskFailure("factory_persona_bridge_identity_mismatch", "Hashes ou identidade persona_writer divergem do arquivo privado.", blocked=True)

        evidence_rows = payload.get("evidence_rows")
        valid_source_ids = payload.get("valid_source_ids")
        if (
            not isinstance(evidence_rows, list)
            or any(not isinstance(row, Mapping) or set(row) != {"evidence_id", "source_id"} for row in evidence_rows)
            or not isinstance(valid_source_ids, list)
            or any(not isinstance(source_id, str) or not source_id for source_id in valid_source_ids)
        ):
            raise TaskFailure("factory_persona_bridge_evidence_invalid", "Mapeamento precisa conter somente evidence_id e source_id aprovados.", blocked=True)
        try:
            converted = role_story_draft_to_editorial_output(
                role_output,
                evidence_rows=evidence_rows,
                valid_source_ids=set(valid_source_ids),
            )
        except TaskFailure:
            raise
        except (TypeError, ValueError) as error:
            raise TaskFailure("factory_persona_bridge_conversion_failed", f"Conversão determinística falhou ({type(error).__name__}).", blocked=True) from None

        draft_bytes = (json.dumps(converted, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        draft_dir = (self.artifact_root / "factory-persona-drafts").resolve()
        draft_dir.mkdir(parents=True, exist_ok=True)
        if not draft_dir.is_relative_to(self.artifact_root):
            raise TaskFailure("factory_persona_bridge_storage_invalid", "Saída da fábrica precisa permanecer na raiz privada.", blocked=True)
        draft_path = draft_dir / f"{task.task_id}.article-draft.json"
        self._write_idempotent(draft_path, draft_bytes)
        draft_manifest = {
            "schema_version": "FactoryPersonaDraftArtifact.v1",
            "factory_task_id": task.task_id,
            "role_task_id": parent.task_id,
            "story_id": story_id,
            "persona_id": envelope.persona_id,
            "persona_version": envelope.persona_version,
            "persona_hash": envelope.persona_hash,
            "role_response_ref": dict(artifact_ref),
            "story_version_manifest_ref": manifest_path.relative_to(self.artifact_root).as_posix(),
            "story_version_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "original_full_text_ref": manifest["full_text_ref"],
            "original_full_text_sha256": manifest["full_text_sha256"],
            "article_draft_ref": draft_path.relative_to(self.artifact_root).as_posix(),
            "article_draft_sha256": hashlib.sha256(draft_bytes).hexdigest(),
            "source_ids": converted["source_ids"],
            "human_review_required": True,
            "fact_check_status": "not_run",
            "editorial_review_status": "not_run",
            "published": False,
        }
        manifest_bytes = (json.dumps(draft_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        manifest_path_out = draft_dir / f"{task.task_id}.manifest.json"
        self._write_idempotent(manifest_path_out, manifest_bytes)
        return {
            "status": "awaiting_human_review",
            "factory_stage": "draft_adapter",
            "story_id": story_id,
            "persona_id": envelope.persona_id,
            "persona_hash": envelope.persona_hash,
            "role_task_id": parent.task_id,
            "role_response_ref": dict(artifact_ref),
            "story_version_manifest_ref": manifest_path.relative_to(self.artifact_root).as_posix(),
            "story_version_manifest_sha256": draft_manifest["story_version_manifest_sha256"],
            "original_full_text_ref": manifest["full_text_ref"],
            "original_full_text_sha256": manifest["full_text_sha256"],
            "article_draft_ref": draft_manifest["article_draft_ref"],
            "article_draft_sha256": draft_manifest["article_draft_sha256"],
            "source_ids": converted["source_ids"],
            "human_review_required": True,
            "fact_check_status": "not_run",
            "editorial_review_status": "not_run",
            "published": False,
        }

    @staticmethod
    def _write_idempotent(path: Path, payload: bytes) -> None:
        if path.exists():
            if path.read_bytes() != payload:
                raise TaskFailure("factory_persona_bridge_overwrite_blocked", "Artefato de fábrica existente diverge; sobrescrita bloqueada.", blocked=True)
            return
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def run_factory_persona_draft_bridge(
    *,
    queue: AgentQueue,
    dispatcher: TaskDispatcher,
    role_task_id: str,
    artifact_root: Path,
    evidence_rows: Sequence[Mapping[str, Any]],
    valid_source_ids: Sequence[str] | set[str],
) -> dict[str, Any]:
    """Run only the draft adapter on an existing shared queue and dispatcher."""
    if dispatcher.queue is not queue or queue.store is not dispatcher.queue.store:
        raise FactoryFixtureError("O adaptador exige a AgentQueue original do dispatcher compartilhado.")
    if dispatcher.role_catalog is None:
        raise FactoryFixtureError("O dispatcher compartilhado precisa manter o AgentRoleCatalog original.")
    if not isinstance(role_task_id, str) or not role_task_id.strip():
        raise FactoryFixtureError("role_task_id precisa identificar uma tarefa existente.")
    existing_executor = dispatcher.executors.get(PERSONA_DRAFT_BRIDGE_EXECUTOR_ID)
    if existing_executor is None:
        dispatcher.executors[PERSONA_DRAFT_BRIDGE_EXECUTOR_ID] = PersonaDraftFactoryBridgeExecutor(
            artifact_root=artifact_root,
            role_catalog=dispatcher.role_catalog,
        )
    elif (
        not isinstance(existing_executor, PersonaDraftFactoryBridgeExecutor)
        or existing_executor.artifact_root != Path(artifact_root).expanduser().resolve()
        or existing_executor.role_catalog is not dispatcher.role_catalog
    ):
        raise FactoryFixtureError("Executor de integração existente diverge da raiz privada ou do catálogo do dispatcher.")
    key = (PERSONA_DRAFT_BRIDGE_PROFILE.profile_id, PERSONA_DRAFT_BRIDGE_PROFILE.version)
    existing_profile = dispatcher.profiles.get(key)
    if existing_profile is not None and existing_profile.content_hash != PERSONA_DRAFT_BRIDGE_PROFILE.content_hash:
        raise FactoryFixtureError("Perfil do adaptador de rascunho diverge do dispatcher.")
    dispatcher.profiles[key] = PERSONA_DRAFT_BRIDGE_PROFILE
    dispatcher.deterministic_task_routes[PERSONA_DRAFT_BRIDGE_TASK_TYPE] = PERSONA_DRAFT_BRIDGE_EXECUTOR_ID
    if isinstance(evidence_rows, (str, bytes)) or not isinstance(evidence_rows, Sequence):
        raise FactoryFixtureError("evidence_rows precisa ser uma sequência de referências tipadas.")
    if isinstance(valid_source_ids, (str, bytes)) or not isinstance(valid_source_ids, (Sequence, set, frozenset)):
        raise FactoryFixtureError("valid_source_ids precisa ser uma sequência de IDs.")
    payload = {
        "stage": "draft",
        "role_task_id": role_task_id,
        "evidence_rows": [dict(row) for row in evidence_rows],
        "valid_source_ids": sorted(set(valid_source_ids)),
    }
    key_hash = stable_hash(json_dumps(payload))
    idempotency_key = f"factory-persona-draft:{role_task_id}:{key_hash[:24]}"
    task_id = str(uuid.uuid5(uuid.NAMESPACE_URL, idempotency_key))
    factory_task_id = queue.enqueue(
        task_type=PERSONA_DRAFT_BRIDGE_TASK_TYPE,
        payload=payload,
        profile=PERSONA_DRAFT_BRIDGE_PROFILE,
        executor_id=PERSONA_DRAFT_BRIDGE_EXECUTOR_ID,
        idempotency_key=idempotency_key,
        max_attempts=1,
        task_id=task_id,
        dependencies=[role_task_id],
    )
    task = queue.get(factory_task_id)
    if task is None:
        raise RuntimeError("Tarefa de integração recém-enfileirada não foi encontrada.")
    if task.state != "succeeded":
        outcome = dispatcher.dispatch_one(factory_task_id)
        task = queue.get(factory_task_id)
        if outcome.state != "succeeded" or task is None or task.state != "succeeded" or task.result is None:
            raise TaskFailure(
                outcome.error_code or "factory_persona_bridge_dispatch_failed",
                f"Adaptador terminou em {outcome.state}; artigo não avançou.",
                blocked=True,
            )
    assert task.result is not None
    return {
        "workflow": "persona_draft_bridge",
        "factory_task_id": task.task_id,
        "role_task_id": role_task_id,
        "status": task.result["status"],
        "factory_stage": task.result["factory_stage"],
        "story_id": task.result["story_id"],
        "persona_id": task.result["persona_id"],
        "persona_hash": task.result["persona_hash"],
        "story_version_manifest_ref": task.result["story_version_manifest_ref"],
        "story_version_manifest_sha256": task.result["story_version_manifest_sha256"],
        "original_full_text_ref": task.result["original_full_text_ref"],
        "original_full_text_sha256": task.result["original_full_text_sha256"],
        "article_draft_ref": task.result["article_draft_ref"],
        "article_draft_sha256": task.result["article_draft_sha256"],
        "source_ids": list(task.result["source_ids"]),
        "human_review_required": True,
        "fact_check_status": "not_run",
        "editorial_review_status": "not_run",
        "publication_state": "not_published",
        "published": False,
    }


def _run_task(
    queue: AgentQueue,
    dispatcher: TaskDispatcher,
    *,
    task_type: str,
    stage: str,
    payload: Mapping[str, Any],
    profile: AgentProfile,
) -> tuple[Mapping[str, Any], AgentTask]:
    task_payload = {"stage": stage, **dict(payload)}
    key_hash = stable_hash(json_dumps({
        "task_type": task_type,
        "payload": task_payload,
        "profile_id": profile.profile_id,
        "profile_version": profile.version,
        "profile_hash": profile.content_hash,
    }))
    run_id = str(task_payload.get("run_id") or task_payload.get("fixture", {}).get("run_id") or "run")
    idempotency_key = f"factory:{run_id}:{task_type}:{stage}:{key_hash[:20]}"
    task_id = queue.enqueue(
        task_type=task_type,
        payload=task_payload,
        profile=profile,
        executor_id=FACTORY_EXECUTOR_ID,
        idempotency_key=idempotency_key,
        max_attempts=2,
    )
    task = queue.get(task_id)
    if task is None:
        raise RuntimeError("Tarefa recém-enfileirada não foi encontrada no ledger.")
    if task.state != "succeeded":
        outcome = dispatcher.dispatch_one(task_id)
        task = queue.get(task_id)
        if outcome.state != "succeeded" or task is None or task.state != "succeeded" or task.result is None:
            raise TaskFailure(
                "factory_dispatch_failed",
                f"Etapa {stage} terminou em {outcome.state}; fluxo interrompido sem avanço.",
                blocked=True,
            )
    if task.result is None:
        raise RuntimeError(f"A etapa {stage} não possui saída estruturada persistida.")
    return task.result, task


def run_factory_demo(
    store: Store,
    fixture_path: Path | None = None,
    *,
    run_id: str | None = None,
    review_flow: str = "pass",
    source_disagreement: bool = False,
    queue: AgentQueue | None = None,
    dispatcher: TaskDispatcher | None = None,
    research_packet: ResearchPacket | Mapping[str, Any] | None = None,
    research_source_bindings: Mapping[str, str] | None = None,
    persona_draft_task_id: str | None = None,
    persona_draft_artifact_root: Path | None = None,
    persona_draft_evidence_rows: Sequence[Mapping[str, Any]] | None = None,
    persona_draft_valid_source_ids: Sequence[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Run the synthetic demo or adapt an existing persona draft on its shared queue."""
    bridge_values = (
        persona_draft_task_id,
        persona_draft_artifact_root,
        persona_draft_evidence_rows,
        persona_draft_valid_source_ids,
    )
    if any(value is not None for value in bridge_values):
        if any(value is None for value in bridge_values):
            raise FactoryFixtureError("Integração persona_writer exige task_id, raiz privada e pacote de fontes completos.")
        if (queue is None) != (dispatcher is None) or queue is None or dispatcher is None:
            raise FactoryFixtureError("Integração persona_writer exige AgentQueue e TaskDispatcher compartilhados explícitos.")
        result = run_factory_persona_draft_bridge(
            queue=queue,
            dispatcher=dispatcher,
            role_task_id=persona_draft_task_id or "",
            artifact_root=persona_draft_artifact_root or Path(),
            evidence_rows=persona_draft_evidence_rows or (),
            valid_source_ids=persona_draft_valid_source_ids or (),
        )
        report_path = store.artifact_dir / "factory-demo" / "persona-draft-bridge" / f"{result['factory_task_id']}.json"
        result["report_path"] = str(report_path.resolve())
        _write_json(report_path, result)
        return result
    fixture = _load_fixture(fixture_path)
    if review_flow not in {"pass", "revise", "hold"}:
        raise FactoryFixtureError("review_flow deve ser pass, revise ou hold.")
    if run_id is not None:
        if not FACTORY_ID_RE.fullmatch(run_id):
            raise FactoryFixtureError("run_id informado é inválido.")
        fixture["run_id"] = run_id
    if (queue is None) != (dispatcher is None):
        raise FactoryFixtureError("queue e dispatcher compartilhados precisam ser fornecidos juntos.")
    if queue is None:
        queue = AgentQueue(store)
        dispatcher = _build_factory_dispatcher(queue)
    elif dispatcher is None or dispatcher.queue is not queue:
        raise FactoryFixtureError("dispatcher compartilhado precisa usar a mesma AgentQueue.")
    if research_packet is None:
        validated_research_packet = None
    elif isinstance(research_packet, ResearchPacket):
        validated_research_packet = research_packet
    else:
        validated_research_packet = ResearchPacket.from_mapping(research_packet)
    packet = _packet(fixture)
    if research_source_bindings is not None:
        if validated_research_packet is None or not isinstance(research_source_bindings, Mapping):
            raise FactoryFixtureError("Vínculos de fonte Radar exigem ResearchPacket validado.")
        normalized_bindings = dict(research_source_bindings)
        expected_refs = {item.ref for item in validated_research_packet.document_refs}
        if (
            set(normalized_bindings) != expected_refs
            or any(not isinstance(source_id, str) for source_id in normalized_bindings.values())
            or not set(normalized_bindings.values()).issubset(_source_ids(packet))
        ):
            raise FactoryFixtureError("ResearchPacket precisa apontar para fontes presentes no pacote editorial.")
    elif validated_research_packet is not None:
        raise FactoryFixtureError("ResearchPacket exige vínculo explícito para cada fonte editorial Radar.")
    else:
        normalized_bindings = None
    reference_index = LayoutReferenceIndex(
        Path(store.db_path).resolve().parent / "factory-reference-index.sqlite3"
    )
    _seed_reference_index(reference_index)

    assert queue is not None and dispatcher is not None
    tasks: list[AgentTask] = []
    outputs: dict[str, Mapping[str, Any]] = {}
    stage_identities: dict[str, Mapping[str, Any]] = {}
    handoffs: dict[str, Mapping[str, Any]] = {}

    def run_editorial(stage: str, previous: Mapping[str, Any]) -> Mapping[str, Any]:
        result, task = _run_task(
            queue, dispatcher,
            task_type=EDITORIAL_TASK_TYPE,
            stage=stage,
            payload={
                "run_id": fixture["run_id"],
                "packet": packet,
                "previous_outputs": dict(previous),
                "actor_role": _STAGE_ROLES[stage],
                "functional_role_id": _FUNCTIONAL_STAGE_ROLES[stage],
                "content_identity": _identity_for_stage(fixture, stage),
                "handoffs": dict(handoffs),
                "e14_case": fixture.get("e14_case"),
                "review_flow": review_flow,
                "source_disagreement": source_disagreement,
                "radar_research_packet": (
                    validated_research_packet.to_dict()
                    if stage == "source_analysis" and validated_research_packet is not None
                    else None
                ),
                "radar_research_source_bindings": (
                    normalized_bindings if stage == "source_analysis" else None
                ),
            },
            profile=EDITORIAL_PROFILE,
        )
        tasks.append(task)
        outputs[stage] = result["structured_output"]
        stage_identities[stage] = result["content_identity"]
        artifact = result.get("handoff_artifact")
        artifact_key = next((key for key, kind in ARTIFACT_KEYS.items()
                             if isinstance(artifact, Mapping) and artifact.get("artifact_type") == kind), None)
        if artifact_key is None:
            raise TaskFailure("factory_handoff_missing", f"A etapa {stage} não persistiu um handoff tipado.", blocked=True)
        handoffs[artifact_key] = artifact
        return outputs[stage]

    source_analysis = run_editorial("source_analysis", {})
    outline = run_editorial("outline", {"source_analysis": source_analysis})
    draft = run_editorial("draft", {"source_analysis": source_analysis, "outline": outline})
    fact_check = run_editorial("fact_check", {"draft": draft})
    initial_review = run_editorial("review", {"draft": draft, "fact_check": fact_check})
    if not review_matches_revision(initial_review, draft):
        raise TaskFailure(
            "factory_initial_review_not_current",
            "A revisão inicial não corresponde ao rascunho corrente; o fluxo não pode avançar.",
            blocked=True,
        )
    if initial_review.get("verdict") == "revise":
        correction = run_editorial("correction", {
            "draft": draft, "fact_check": fact_check, "review": initial_review,
        })
        if article_revision_sha256(correction) == article_revision_sha256(draft):
            raise TaskFailure("factory_correction_not_new_revision", "A correção não criou um novo hash de artigo.", blocked=True)
        final_fact_check = run_editorial("final_fact_check", {"correction": correction})
        final_review = run_editorial("final_review", {
            "correction": correction, "final_fact_check": final_fact_check,
        })
        article = correction
        review = final_review
        if final_fact_check.get("checked_revision_sha256") != article_revision_sha256(article):
            raise TaskFailure("factory_fact_check_not_current", "A checagem final não corresponde à correção.", blocked=True)
    elif initial_review.get("verdict") == "pass":
        article = draft
        review = initial_review
    else:
        raise TaskFailure("factory_editorial_hold", "A pauta ficou em espera; o gate humano precisa resolver a divergência.", blocked=True)
    if not review_matches_revision(review, article):
        raise TaskFailure("factory_review_not_current", "Revisão final não aprova a revisão corrente.", blocked=True)
    story_revision = 2 if review.get("reviewed_revision_stage") == "correction" else 1

    run_fixture = {**fixture, "run_id": fixture["run_id"]}
    media_result, media_task = _run_task(
        queue, dispatcher,
        task_type=MEDIA_TASK_TYPE,
        stage="rights_inventory",
        payload={"run_id": fixture["run_id"], "fixture": run_fixture, "story_revision": story_revision},
        profile=MEDIA_PROFILE,
    )
    tasks.append(media_task)
    media_inventory = media_result["media_inventory"]

    package_result, package_task = _run_task(
        queue, dispatcher,
        task_type=STORY_PACKAGE_TASK_TYPE,
        stage="story_package",
        payload={
            "run_id": fixture["run_id"], "fixture": run_fixture, "packet": packet,
            "article": article, "outline": outline, "review": review,
            "final_fact_check": outputs.get("final_fact_check"),
            "editorial_handoffs": dict(handoffs),
            "content_identities": {
                "editor": stage_identities["outline"],
                "writer_persona": stage_identities.get("correction", stage_identities["draft"]),
                "reviewer": stage_identities.get("final_review", stage_identities["review"]),
            },
        },
        profile=PACKAGE_PROFILE,
    )
    tasks.append(package_task)
    story_package = package_result["story_package"]

    visual_result, visual_task = _run_task(
        queue, dispatcher,
        task_type=LAYOUT_TASK_TYPE,
        stage="visual_needs",
        payload={"run_id": fixture["run_id"], "story_package": story_package},
        profile=LAYOUT_PROFILE,
    )
    tasks.append(visual_task)
    visual_needs = visual_result["visual_needs"]
    index_hash = reference_index.fingerprint()
    search_tags = [tag for need in visual_needs["needs"] for tag in need["tags"]]
    selected_references = reference_index.search(search_tags, limit=3)
    reference_result, reference_task = _run_task(
        queue, dispatcher,
        task_type=LAYOUT_TASK_TYPE,
        stage="references",
        payload={
            "run_id": fixture["run_id"], "references": selected_references,
            "reference_index_sha256": index_hash,
        },
        profile=LAYOUT_PROFILE,
    )
    tasks.append(reference_task)
    references = reference_result["references"]

    plan_result, plan_task = _run_task(
        queue, dispatcher,
        task_type=LAYOUT_TASK_TYPE,
        stage="layout_plan",
        payload={
            "run_id": fixture["run_id"], "story_package": story_package,
            "media_inventory": media_inventory, "visual_needs": visual_needs,
            "references": references, "reference_index_sha256": index_hash,
        },
        profile=LAYOUT_PROFILE,
    )
    tasks.append(plan_task)
    layout_plan = plan_result["layout_plan"]

    indexed_references = reference_index.references()
    validation_result, validation_task = _run_task(
        queue, dispatcher,
        task_type=LAYOUT_TASK_TYPE,
        stage="composition_validation",
        payload={
            "run_id": fixture["run_id"], "story_package": story_package,
            "media_inventory": media_inventory, "layout_plan": layout_plan,
            "reference_index_sha256": index_hash, "indexed_references": indexed_references,
        },
        profile=LAYOUT_PROFILE,
    )
    tasks.append(validation_task)
    composition_validation = validation_result["composition_validation"]
    if composition_validation["payload"]["status"] != "PASS":
        raise TaskFailure("factory_composition_failed", "Composição não passou; gate humano permanece fechado.", blocked=True)

    render_result, render_task = _run_task(
        queue, dispatcher,
        task_type=LAYOUT_TASK_TYPE,
        stage="render",
        payload={
            "run_id": fixture["run_id"], "story_package": story_package,
            "layout_plan": layout_plan, "composition_validation": composition_validation,
        },
        profile=LAYOUT_PROFILE,
    )
    tasks.append(render_task)
    preview_html = str(render_result["preview_html"])
    render_validation_result, render_validation_task = _run_task(
        queue, dispatcher,
        task_type=LAYOUT_TASK_TYPE,
        stage="render_validation",
        payload={
            "run_id": fixture["run_id"], "story_package": story_package,
            "layout_plan": layout_plan, "composition_validation": composition_validation,
            "preview_html": preview_html,
        },
        profile=LAYOUT_PROFILE,
    )
    tasks.append(render_validation_task)
    composition_validation = render_validation_result["composition_validation"]
    if composition_validation["payload"]["status"] != "PASS":
        raise TaskFailure("factory_render_validation_failed", "Prévia não passou pela verificação renderizada.", blocked=True)

    preview_result, preview_task = _run_task(
        queue, dispatcher,
        task_type=PREVIEW_TASK_TYPE,
        stage="persist_internal_preview",
        payload={
            "run_id": fixture["run_id"], "preview_html": preview_html,
            "composition_validation": composition_validation, "story_package": story_package,
        },
        profile=LAYOUT_PROFILE,
    )
    tasks.append(preview_task)
    internal_preview = preview_result
    gate_result, gate_task = _run_task(
        queue, dispatcher,
        task_type=HUMAN_GATE_TASK_TYPE,
        stage="simulated_human_approval",
        payload={
            "run_id": fixture["run_id"],
            "decision": fixture["simulated_human_decision"],
            "internal_preview": internal_preview,
            "preview_sha256": internal_preview["preview_sha256"],
            "story_revision_sha256": story_revision_sha256(story_package["payload"]),
            "composition_validation": composition_validation,
        },
        profile=GATE_PROFILE,
    )
    tasks.append(gate_task)

    report = {
        "run_id": fixture["run_id"],
        "status": gate_result["status"],
        "synthetic_fixture_only": True,
        "task_ledger": "agent_tasks/agent_task_events",
        "task_count": len(tasks),
        "task_ids": [task.task_id for task in tasks],
        "task_stages": [{
            "task_id": task.task_id,
            "task_type": task.task_type,
            "stage": task.payload.get("stage"),
            "actor_role": task.payload.get("actor_role"),
            "functional_role_id": task.result.get("functional_role", {}).get("role_id") if isinstance(task.result, Mapping) else None,
            "functional_role_version": task.result.get("functional_role", {}).get("role_version") if isinstance(task.result, Mapping) else None,
            "handoff_artifact_type": task.result.get("handoff_artifact", {}).get("artifact_type") if isinstance(task.result, Mapping) else None,
            "handoff_artifact_sha256": task.result.get("handoff_artifact", {}).get("content_sha256") if isinstance(task.result, Mapping) else None,
            "upstream_handoff_hashes": task.result.get("upstream_handoff_hashes", {}) if isinstance(task.result, Mapping) else {},
            "content_identity": task.payload.get("content_identity"),
            "state": task.state,
            "profile_id": task.profile_id,
            "profile_version": task.profile_version,
            "profile_hash": task.profile_hash,
        } for task in tasks],
        "review_flow": review_flow,
        "source_disagreement": source_disagreement,
        "radar_research_packet": (
            {
                "request_id": validated_research_packet.request_id,
                "content_hash": validated_research_packet.content_hash,
                "status": validated_research_packet.status,
                "document_refs": [item.to_dict() for item in validated_research_packet.document_refs],
                "source_bindings": normalized_bindings,
            }
            if validated_research_packet is not None else None
        ),
        "e14_case_id": fixture.get("e14_case", {}).get("case_id") if isinstance(fixture.get("e14_case"), Mapping) else None,
        "editorial_handoffs": {
            key: {
                "artifact_type": value["artifact_type"],
                "artifact_id": value["artifact_id"],
                "story_id": value["story_id"],
                "revision_id": value["revision_id"],
                "content_sha256": value["content_sha256"],
            }
            for key, value in handoffs.items()
        },
        "editorial_handoff_chain_sha256": stable_hash(json_dumps({
            key: handoffs[key]["content_sha256"] for key in ARTIFACT_KEYS
        })),
        "initial_article_revision_sha256": article_revision_sha256(draft),
        "article_revision_sha256": article_revision_sha256(article),
        "initial_reviewed_revision_sha256": initial_review["reviewed_revision_sha256"],
        "reviewed_revision_sha256": review["reviewed_revision_sha256"],
        "reviewed_revision_stage": review["reviewed_revision_stage"],
        "story_revision": story_package["payload"]["story_revision"],
        "story_package": {
            "artifact_id": story_package["artifact_id"],
            "schema_version": story_package["schema_version"],
            "revision": story_package["revision"],
            "content_sha256": story_package["content_sha256"],
            "story_revision_sha256": story_revision_sha256(story_package["payload"]),
            "role_profiles": {
                role: {
                    "profile_id": identity["profile_id"],
                    "version": identity["version"],
                    "profile_sha256": profile_sha256(identity),
                }
                for role, identity in story_package["payload"]["identities"].items()
            },
        },
        "media_inventory_sha256": media_inventory["content_sha256"],
        "reference_index_sha256": index_hash,
        "layout_plan_sha256": layout_plan["content_sha256"],
        "composition_validation_sha256": composition_validation["content_sha256"],
        "composition_status": composition_validation["payload"]["status"],
        "composition_checks": len(composition_validation["payload"]["checks"]),
        "preview_sha256": internal_preview["preview_sha256"],
        "preview_path": internal_preview["preview_path"],
        "human_gate": gate_result,
        "publication_state": "not_published",
        "published": False,
        "network_calls": 0,
        "siwc_calls": 0,
        "paid_api_calls": 0,
    }
    report_path = store.artifact_dir / "factory-demo" / fixture["run_id"] / "factory-demo-report.json"
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def run_factory_multipauta_demo(
    store: Store,
    stories: Sequence[FactoryStoryRun],
    *,
    queue: AgentQueue | None = None,
    dispatcher: TaskDispatcher | None = None,
    batch_id: str = "factory-e15-multipauta",
) -> dict[str, Any]:
    """Run two or three synthetic stories through one durable queue/dispatcher."""
    if not FACTORY_ID_RE.fullmatch(batch_id):
        raise FactoryFixtureError("batch_id informado é inválido.")
    if isinstance(stories, (str, bytes)) or not isinstance(stories, Sequence) or not 2 <= len(stories) <= 3:
        raise FactoryFixtureError("Ensaio multipauta exige duas ou três pautas.")
    if (queue is None) != (dispatcher is None):
        raise FactoryFixtureError("queue e dispatcher compartilhados precisam ser fornecidos juntos.")
    if queue is None:
        queue = AgentQueue(store)
        dispatcher = _build_factory_dispatcher(queue)
    elif dispatcher is None or dispatcher.queue is not queue:
        raise FactoryFixtureError("dispatcher compartilhado precisa usar a mesma AgentQueue.")
    assert queue is not None and dispatcher is not None

    run_ids: list[str] = []
    for story in stories:
        if not isinstance(story, FactoryStoryRun):
            raise FactoryFixtureError("Cada pauta precisa ser FactoryStoryRun.")
        if not FACTORY_ID_RE.fullmatch(story.run_id):
            raise FactoryFixtureError("run_id de pauta multipauta é inválido.")
        if story.run_id in run_ids:
            raise FactoryFixtureError("run_id de pauta multipauta está duplicado.")
        if story.review_flow not in {"pass", "revise", "hold"}:
            raise FactoryFixtureError("review_flow deve ser pass, revise ou hold.")
        _load_fixture(story.fixture_path)
        if story.research_packet is not None:
            if isinstance(story.research_packet, ResearchPacket):
                ResearchPacket.from_mapping(story.research_packet.to_dict())
            else:
                ResearchPacket.from_mapping(story.research_packet)
        run_ids.append(story.run_id)

    outcomes: list[dict[str, Any]] = []
    for story in stories:
        if story.research_packet is None:
            story_research_summary = None
        else:
            packet_value = (
                ResearchPacket.from_mapping(story.research_packet.to_dict())
                if isinstance(story.research_packet, ResearchPacket)
                else ResearchPacket.from_mapping(story.research_packet)
            )
            story_research_summary = {
                "request_id": packet_value.request_id,
                "content_hash": packet_value.content_hash,
                "status": packet_value.status,
                "document_refs": [item.to_dict() for item in packet_value.document_refs],
                "source_bindings": story.research_source_bindings,
            }
        try:
            result = run_factory_demo(
                store,
                story.fixture_path,
                run_id=story.run_id,
                review_flow=story.review_flow,
                source_disagreement=story.source_disagreement,
                queue=queue,
                dispatcher=dispatcher,
                research_packet=story.research_packet,
                research_source_bindings=story.research_source_bindings,
            )
        except TaskFailure as error:
            story_tasks = [
                task for task in queue.list_tasks(limit=1000)
                if task.payload.get("run_id") == story.run_id
            ]
            failed_tasks = []
            for task in story_tasks:
                terminal_events = [event for event in queue.events(task.task_id) if event["action"] in {"failed", "blocked"}]
                if terminal_events:
                    failed_tasks.append({
                        "task_id": task.task_id,
                        "task_type": task.task_type,
                        "stage": task.payload.get("stage"),
                        "failure_code": terminal_events[-1]["detail"].get("error_code"),
                    })
            outcomes.append({
                "run_id": story.run_id,
                "outcome": "blocked",
                "failure_code": error.code,
                "summary": error.summary,
                "radar_research_packet": story_research_summary,
                "failed_tasks": failed_tasks,
                "task_ids": [task.task_id for task in story_tasks],
                "task_states": [task.state for task in story_tasks],
                "published": False,
            })
            continue

        if result["story_revision"] > 1:
            outcome = "corrected"
        elif result["status"] == "simulated_approved_internally":
            outcome = "approved_internal_preview"
        elif result["status"] == "simulated_on_hold":
            outcome = "preview_held_for_human"
        else:
            outcome = "completed"
        outcomes.append({
            "run_id": story.run_id,
            "outcome": outcome,
            "factory_status": result["status"],
            "review_flow": result["review_flow"],
            "story_revision": result["story_revision"],
            "article_revision_sha256": result["article_revision_sha256"],
            "reviewed_revision_sha256": result["reviewed_revision_sha256"],
            "radar_research_packet": result["radar_research_packet"],
            "preview_sha256": result["preview_sha256"],
            "preview_path": result["preview_path"],
            "task_ids": result["task_ids"],
            "published": False,
        })

    task_ids = [task_id for outcome in outcomes for task_id in outcome["task_ids"]]
    report = {
        "schema_version": "FactoryMultipautaRun.v1",
        "batch_id": batch_id,
        "status": "completed_with_blocked_stories" if any(item["outcome"] == "blocked" for item in outcomes) else "completed",
        "synthetic_fixture_only": True,
        "shared_task_ledger": "agent_tasks/agent_task_events",
        "shared_dispatcher": True,
        "story_count": len(outcomes),
        "story_outcomes": outcomes,
        "task_count": len(set(task_ids)),
        "task_ids": list(dict.fromkeys(task_ids)),
        "publication_state": "not_published",
        "published": False,
    }
    report_path = store.artifact_dir / "factory-demo" / batch_id / "multipauta-report.json"
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report
