"""Synthetic end-to-end factory path through one durable task dispatcher."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .db import Store, json_dumps, stable_hash
from .editorial import (
    EDITORIAL_PROFILE,
    EDITORIAL_TASK_TYPE,
    article_revision_sha256,
    build_stage_input,
    normalize_source_packet,
    review_matches_revision,
    validate_stage_output,
)
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
FACTORY_EXECUTOR_ID = "synthetic-factory"
FACTORY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
LAYOUT_TASK_TYPE = "factory.layout_stage"
MEDIA_TASK_TYPE = "factory.media_inventory"
STORY_PACKAGE_TASK_TYPE = "factory.story_package"
PREVIEW_TASK_TYPE = "factory.internal_preview"
HUMAN_GATE_TASK_TYPE = "factory.simulated_human_gate"

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


class FactoryFixtureError(ValueError):
    """A synthetic fixture is malformed or contains a non-synthetic decision."""


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


def _editorial_output(
    stage: str, packet: Mapping[str, Any], previous: Mapping[str, Any]
) -> dict[str, Any]:
    ids = [str(source["id"]) for source in packet["sources"]]
    if stage == "source_analysis":
        source = packet["sources"][0]
        return {"claims": [{
            "claim_id": "fictional-claim-01",
            "claim": "Farol de Papel é um jogo fictício de exploração solo com mapas desenhados à mão.",
            "source_ids": ids,
            "evidence_excerpt": source["evidence"],
            "assessment": "supported",
            "confidence": "high",
            "caveat": "A fixture não descreve um jogo real.",
        }]}
    if stage == "outline":
        return {
            "headline": "Farol de Papel: exploração em mapas feitos à mão",
            "dek": "Uma pauta fictícia demonstra como organizar evidência sem inventar uma data de lançamento.",
            "sections": [{
                "heading": "Descoberta sem pressa",
                "focus": "Apresentar a proposta imaginária e registrar o limite do que as fontes dizem.",
                "source_ids": ids,
            }],
        }
    if stage == "draft":
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
        return {"findings": [{
            "claim": "As fontes fictícias descrevem mapas desenhados à mão e exploração solo.",
            "source_ids": ids,
            "status": "supported",
            "confidence": "high",
            "correction": "",
        }]}
    if stage in {"review", "final_review"}:
        return {"verdict": "pass", "findings": [], "human_review_required": True}
    if stage == "correction":
        article = previous["draft"]
        return {
            "headline": article["headline"],
            "dek": article["dek"],
            "body_markdown": article["body_markdown"],
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
    if review.get("verdict") != "pass" or not review_matches_revision(review, article):
        raise TaskFailure(
            "factory_review_not_current",
            "A revisão B2 não corresponde ao artigo corrente; StoryPackage não será criado.",
            blocked=True,
        )
    if review.get("reviewed_revision_stage") != "draft":
        raise TaskFailure(
            "factory_review_stage_mismatch", "A revisão deve apontar para o rascunho corrente.", blocked=True
        )
    story_id = f"story-{fixture['run_id']}"
    figure = fixture["synthetic_figure"]
    figure_block_id = f"{story_id}-{figure['block_id_suffix']}"
    sections = [
        {
            "block_id": f"{story_id}-heading-01",
            "kind": "heading",
            "text": outline["sections"][0]["heading"],
            "source_ids": list(outline["sections"][0]["source_ids"]),
        },
        {
            "block_id": f"{story_id}-body-01",
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
        "story_revision": 1,
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
            "source_ids": packet_source_ids,
            "synthetic_fixture_only": True,
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
        "human_approval": False,
        "synthetic_fixture": True,
    }
    story = seal_artifact(story_id, SCHEMA_STORY, 1, story_payload)
    return validate_story_package(story)


def _build_media_inventory(payload: Mapping[str, Any]) -> dict[str, Any]:
    fixture = payload["fixture"]
    story_id = f"story-{fixture['run_id']}"
    figure = fixture["synthetic_figure"]
    block_id = f"{story_id}-{figure['block_id_suffix']}"
    inventory_payload = {
        "inventory_id": f"media-inventory-{fixture['run_id']}",
        "assets": [{
            "asset_id": figure["asset_id"],
            "media_kind": "placeholder",
            "rights_status": "synthetic_fixture",
            "rights_holder": "SyntheticFactoryFixture.v0",
            "origin": "Placeholder textual definido pela fixture; sem bytes de imagem.",
            "credit": "Ativo fictício de validação interna.",
            "permitted_transformations": [],
            "linked_block_ids": [block_id],
            "license": {"status": "not_applicable_synthetic_placeholder"},
            "asset_sha256": None,
            "dimensions": None,
            "permitted_modes": ["internal_preview"],
            "synthetic": True,
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
        packet = normalize_source_packet(payload.get("packet", {}))
        previous = payload.get("previous_outputs", {})
        if not isinstance(previous, Mapping):
            raise TaskFailure("factory_previous_output_invalid", "Saídas anteriores inválidas.", blocked=True)
        build_stage_input(stage=stage, packet=packet, previous_outputs=previous)
        structured = validate_stage_output(
            stage, _editorial_output(stage, packet, previous), _source_ids(packet)
        )
        if stage in {"review", "final_review"}:
            revision_stage = "draft" if stage == "review" else "correction"
            structured["reviewed_revision_sha256"] = article_revision_sha256(previous[revision_stage])
            structured["reviewed_revision_stage"] = revision_stage
        elif stage == "final_fact_check":
            structured["checked_revision_sha256"] = article_revision_sha256(previous["correction"])
        return {
            "structured_output": structured,
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
        if validation["payload"].get("status") != "PASS" or digest != expected:
            raise TaskFailure("factory_preview_gate_failed", "Prévia não confere com a validação atual.", blocked=True)
        run_id = str(payload["run_id"])
        if not FACTORY_ID_RE.fullmatch(run_id):
            raise TaskFailure("factory_run_id_invalid", "run_id inválido para artefatos.", blocked=True)
        preview_path = self.artifact_dir / "factory-demo" / run_id / "internal-preview.html"
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(preview_html, encoding="utf-8")
        return {
            "preview_path": str(preview_path),
            "preview_sha256": digest,
            "internal_only": True,
            "published": False,
        }

    @staticmethod
    def _human_gate(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        validation = validate_composition_validation(payload["composition_validation"])
        preview = payload["internal_preview"]
        if validation["payload"].get("status") != "PASS" or preview.get("internal_only") is not True:
            raise TaskFailure("factory_human_gate_closed", "O gate simulado exige prévia interna validada.", blocked=True)
        if payload.get("preview_sha256") != preview.get("preview_sha256"):
            raise TaskFailure("factory_preview_hash_mismatch", "A prévia não corresponde ao hash validado.", blocked=True)
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
) -> dict[str, Any]:
    """Run a synthetic editorial-to-layout flow through one queue and dispatcher."""
    fixture = _load_fixture(fixture_path)
    if run_id is not None:
        if not FACTORY_ID_RE.fullmatch(run_id):
            raise FactoryFixtureError("run_id informado é inválido.")
        fixture["run_id"] = run_id
    packet = _packet(fixture)
    reference_index = LayoutReferenceIndex(
        Path(store.db_path).resolve().parent / "factory-reference-index.sqlite3"
    )
    _seed_reference_index(reference_index)

    queue = AgentQueue(store)
    dispatcher = TaskDispatcher(
        queue,
        executors={FACTORY_EXECUTOR_ID: SyntheticFactoryExecutor(artifact_dir=store.artifact_dir)},
        profiles={
            (profile.profile_id, profile.version): profile
            for profile in (EDITORIAL_PROFILE, LAYOUT_PROFILE, MEDIA_PROFILE, PACKAGE_PROFILE, GATE_PROFILE)
        },
    )
    tasks: list[AgentTask] = []
    outputs: dict[str, Mapping[str, Any]] = {}
    stage_identities: dict[str, Mapping[str, Any]] = {}

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
                "content_identity": _identity_for_stage(fixture, stage),
            },
            profile=EDITORIAL_PROFILE,
        )
        tasks.append(task)
        outputs[stage] = result["structured_output"]
        stage_identities[stage] = result["content_identity"]
        return outputs[stage]

    source_analysis = run_editorial("source_analysis", {})
    outline = run_editorial("outline", {"source_analysis": source_analysis})
    draft = run_editorial("draft", {"source_analysis": source_analysis, "outline": outline})
    fact_check = run_editorial("fact_check", {"draft": draft})
    review = run_editorial("review", {"draft": draft, "fact_check": fact_check})
    if review.get("verdict") != "pass" or not review_matches_revision(review, draft):
        raise TaskFailure("factory_review_not_current", "Revisão inicial não aprovou a revisão corrente.", blocked=True)

    run_fixture = {**fixture, "run_id": fixture["run_id"]}
    media_result, media_task = _run_task(
        queue, dispatcher,
        task_type=MEDIA_TASK_TYPE,
        stage="rights_inventory",
        payload={"run_id": fixture["run_id"], "fixture": run_fixture},
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
            "article": draft, "outline": outline, "review": review,
            "content_identities": {
                "editor": stage_identities["outline"],
                "writer_persona": stage_identities["draft"],
                "reviewer": stage_identities["review"],
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
            "composition_validation": composition_validation,
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
            "content_identity": task.payload.get("content_identity"),
            "state": task.state,
            "profile_id": task.profile_id,
            "profile_version": task.profile_version,
            "profile_hash": task.profile_hash,
        } for task in tasks],
        "article_revision_sha256": article_revision_sha256(draft),
        "reviewed_revision_sha256": review["reviewed_revision_sha256"],
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
