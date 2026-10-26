"""Curated, source-linked dossier manifests for ENG-CODEX-009.

These manifests expose the project-authored source notes to preparation and
validation code. They deliberately do not turn curator summaries into source
evidence: every third-party body remains marked as not obtained until a
permitted local Radar ingest records it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit


PACKAGE_SCHEMA_VERSION = "EditorialEvidencePackage.v1"
PACKAGE_ROOT = Path(__file__).parent / "evidence_packages" / "eng_codex_009"
DOSSIER_ROOT = Path(__file__).resolve().parents[1] / "docs" / "engenharia" / "ensaios-009"
_SOURCE_LINE_DETAIL = re.compile(r"^\s*-\s+\*\*([A-Z]\d{2})\s+(.*?)\*\*(?:\s+(.*))?$")

_SOURCE_LINE = re.compile(
    r"^\s*-\s+\*\*([A-Z]\d{2})\s*(?:[—–-]\s*)?(.*?)\*\*"
    r"(?:\s+(https://\S+))?(?:\s+.*)?$"
)
_QUESTION_HEADING = re.compile(r"^##\s+(?:Perguntas|Questões)", re.IGNORECASE)


@dataclass(frozen=True)
class DossierSpec:
    package_id: str
    journalist: str
    persona_id: str
    persona_version: str
    persona_document: str
    persona_documents: tuple[str, ...]
    persona_source_ref: str
    persona_source_commit: str
    dossier_document: str
    topic: str


DOSSIERS: tuple[DossierSpec, ...] = (
    DossierSpec(
        "eng-codex-009-carranca", "Arlindo Carranca", "ranzinza", "v1.0",
        "docs/personagens/RANZINZA-DNA-CONCEITUAL-v1.0.md",
        (
            "docs/personagens/RANZINZA-DNA-CONCEITUAL-v1.0.md",
            "docs/personagens/RANZINZA-DNA-OPERACIONAL-v0.2.md",
            "docs/personagens/RANZINZA-DNA-EDITORIAL-v0.1.md",
            "docs/personagens/RANZINZA-CONTRATO-CARREGAMENTO-AGENTE-v0.1.md",
        ),
        "bloco-02/ranzinza-dna-editorial-v01",
        "3d651fe1951818767b4a6b935732857f08cb7849",
        "01-CARRANCA-RX9050-DOSSIE-INVESTIGATIVO.md",
        "Radeon RX 9050 4/8 GB e RX 9060 XT 8/16 GB: limites, variantes e metodologia de benchmarks",
    ),
    DossierSpec(
        "eng-codex-009-beto", "Beto Cartucho", "beto-cartucho", "v0.2",
        "docs/personagens/GAMER.md",
        (
            "docs/personagens/GAMER.md",
            "docs/personagens/GAMER-CONTRATO-COGNITIVO-v0.2.md",
            "docs/personagens/GAMER-CONTRATO-EXPRESSAO-v0.2.md",
            "docs/personagens/GAMER-CONTRATO-EDITORIAL-v0.2.md",
            "docs/personagens/GAMER-CONTRATO-CARREGAMENTO-E-VALIDACAO-v0.2.md",
        ),
        "bloco-02/gamer-dna-v02",
        "21381c0975bef1da048d7887cbdfbd0dd97bed96",
        "02-BETO-RESIDENT-EVIL-REQUIEM-DOSSIE.md",
        "Resident Evil Requiem: campanha, recepção crítica e desempenho de PC",
    ),
    DossierSpec(
        "eng-codex-009-nina", "Nina Prisma", "nina-prisma", "v1.0",
        "docs/personagens/NINA-PRISMA.md",
        (
            "docs/personagens/NINA-PRISMA.md",
            "docs/personagens/NINA-PRISMA-CONTRATO-COGNITIVO-v1.0.md",
            "docs/personagens/NINA-PRISMA-CONTRATO-EXPRESSAO-v1.0.md",
            "docs/personagens/NINA-PRISMA-CONTRATO-EDITORIAL-v1.0.md",
            "docs/personagens/NINA-PRISMA-CONTRATO-CARREGAMENTO-E-VALIDACAO-v1.0.md",
        ),
        "bloco-02/gamer-dna-v02",
        "21381c0975bef1da048d7887cbdfbd0dd97bed96",
        "03-NINA-REQUIEM-REFRAMEWORK-MODS-DOSSIE.md",
        "REFramework e o ecossistema de mods de Resident Evil Requiem",
    ),
)


class EvidencePackageError(ValueError):
    """A dossier manifest is malformed or cannot be used as source evidence."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _source_type(title: str) -> str:
    value = title.casefold()
    if any(token in value for token in ("benchmark", "teste independente", "review", "crítica", "crítica")):
        return "independent_test_or_review"
    if any(token in value for token in ("issue github", "bug", "usuário", "comunidade", "reddit")):
        return "individual_or_community_report"
    if any(token in value for token in ("nexus", "catálogo", "listagem", "agregador")):
        return "catalog_or_aggregator"
    if any(token in value for token in ("amd", "capcom", "steam", "fabricante", "oficial", "readme oficial", "releases")):
        return "primary_or_official_material"
    return "secondary_reporting_or_curated_candidate"


def _parse_sources(text: str) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = _SOURCE_LINE.match(line)
        if not match:
            continue
        source_id, title, url = match.groups()
        title = title.strip().rstrip(".")
        if not title:
            raise EvidencePackageError(f"Fonte {source_id} sem título curatorial.")
        source = {
            "source_id": source_id,
            "title": title,
            "url": url,
            "source_type": _source_type(title),
            "curation_reference": source_id,
            "source_body_status": "not_obtained" if url else "unresolved_candidate",
            "rights_review_status": "not_revalidated",
            "access_scope": "read:radar_index",
            "external_retrieval_authorized": False,
        }
        parts = urlsplit(url) if url else None
        if parts and (parts.scheme != "https" or not parts.hostname or parts.username or parts.password):
            raise EvidencePackageError(f"URL HTTPS inválida na fonte {source_id}.")
        sources.append(source)
    if not sources:
        raise EvidencePackageError("Dossiê não contém fontes identificáveis pelo formato aprovado.")
    ids = [source["source_id"] for source in sources]
    if len(ids) != len(set(ids)):
        raise EvidencePackageError("Dossiê contém source_id duplicado.")
    return sources


def _parse_curator_notes(text: str) -> dict[str, str]:
    notes: dict[str, str] = {}
    current_id: str | None = None
    current_lines: list[str] = []

    def finish() -> None:
        if current_id is not None:
            notes[current_id] = " ".join(line.strip() for line in current_lines if line.strip())

    for line in text.splitlines():
        if line.startswith("## "):
            finish()
            current_id, current_lines = None, []
            continue
        match = _SOURCE_LINE_DETAIL.match(line)
        if match:
            finish()
            current_id, current_lines = match.group(1), []
            tail = match.group(3) or ""
            url = re.search(r"https://\S+", tail)
            if url:
                tail = tail.replace(url.group(0), "", 1)
            if tail.strip():
                current_lines.append(tail.strip())
            continue
        if current_id is not None and line.strip() and not line.lstrip().startswith("#"):
            current_lines.append(line.strip())
    finish()
    return notes


def _parse_questions(text: str) -> list[str]:
    questions: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            if in_section:
                break
            in_section = bool(_QUESTION_HEADING.match(line))
            continue
        if in_section:
            item = re.match(r"^\s*\d+\.\s+(.+)$", line)
            if item:
                questions.append(item.group(1).strip())
    return questions


def build_package(spec: DossierSpec, *, dossier_root: Path = DOSSIER_ROOT) -> dict[str, Any]:
    dossier_path = dossier_root / spec.dossier_document
    if not dossier_path.is_file():
        raise EvidencePackageError(f"Dossiê ausente: {spec.dossier_document}.")
    dossier_bytes = dossier_path.read_bytes()
    dossier_text = dossier_bytes.decode("utf-8")
    source_candidates = _parse_sources(dossier_text)
    curated_notes = _parse_curator_notes(dossier_text)
    for source in source_candidates:
        source["curator_note"] = curated_notes.get(source["source_id"], "")
        source["curator_note_status"] = "project_curated_summary" if source["curator_note"] else "no_summary"
    word_ranges = {
        "eng-codex-009-carranca": [1400, 2000],
        "eng-codex-009-beto": [1500, 2100],
        "eng-codex-009-nina": [1300, 1900],
    }
    package: dict[str, Any] = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "package_id": spec.package_id,
        "journalist": spec.journalist,
        "persona_reference": {
            "persona_id": spec.persona_id,
            "persona_version": spec.persona_version,
            "document": spec.persona_document,
            "source_documents": list(spec.persona_documents),
            "source_ref": spec.persona_source_ref,
            "source_commit": spec.persona_source_commit,
            "must_remain_unchanged": True,
        },
        "topic": spec.topic,
        "requested_word_range": word_ranges[spec.package_id],
        "curation_date": "2026-10-25",
        "dossier_document": f"docs/engenharia/ensaios-009/{spec.dossier_document}",
        "dossier_sha256": _sha256(dossier_bytes),
        "source_candidates": source_candidates,
        "coverage_questions": _parse_questions(dossier_text),
        "readiness": {
            "curated_notes_available": any(source["curator_note"] for source in source_candidates),
            "curated_note_only_trial_ready": any(
                source["source_body_status"] == "not_obtained" and source["curator_note"]
                for source in source_candidates
            ),
            "source_bodies_obtained": False,
            "rights_revalidated": False,
            "external_retrieval_authorized": False,
            "radar_index_population_verified": False,
            "ready_for_article_generation": False,
            "blockers": [
                "source body is not locally obtained",
                "source terms and rights have not been revalidated for this run",
                "Issue #35 permits local Radar index reads only; no matching indexed evidence is present",
            ],
        },
    }
    return package


def package_digest(package: Mapping[str, Any]) -> str:
    clean = dict(package)
    clean.pop("package_sha256", None)
    payload = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256(payload)


def validate_package(package: Mapping[str, Any], *, dossier_root: Path = DOSSIER_ROOT) -> dict[str, Any]:
    if package.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        raise EvidencePackageError("schema_version do pacote não é suportada.")
    spec = next((item for item in DOSSIERS if item.package_id == package.get("package_id")), None)
    if spec is None:
        raise EvidencePackageError("package_id não pertence ao trio ENG-CODEX-009.")
    expected = build_package(spec, dossier_root=dossier_root)
    if package_digest(package) != package_digest(expected):
        raise EvidencePackageError("Pacote diverge do dossiê e da política de acesso vigente.")
    if package.get("readiness", {}).get("ready_for_article_generation") is not False:
        raise EvidencePackageError("Pacote sem corpo-fonte não pode estar pronto para gerar matéria.")
    return {
        "package_id": spec.package_id,
        "journalist": spec.journalist,
        "source_count": len(expected["source_candidates"]),
        "resolved_url_count": sum(bool(source["url"]) for source in expected["source_candidates"]),
        "unresolved_candidate_count": sum(source["url"] is None for source in expected["source_candidates"]),
        "coverage_question_count": len(expected["coverage_questions"]),
        "curated_note_count": sum(
            source["source_body_status"] == "not_obtained" and bool(source["curator_note"])
            for source in expected["source_candidates"]
        ),
        "curator_note_candidate_count": sum(bool(source["curator_note"]) for source in expected["source_candidates"]),
        "curated_note_only_trial_ready": expected["readiness"]["curated_note_only_trial_ready"],
        "source_bodies_obtained": False,
        "ready_for_article_generation": False,
        "blockers": list(expected["readiness"]["blockers"]),
    }


def load_package(package_id: str) -> dict[str, Any]:
    path = PACKAGE_ROOT / f"{package_id}.json"
    package = json.loads(path.read_text(encoding="utf-8"))
    validate_package(package)
    return package


def write_package_manifests(*, dossier_root: Path = DOSSIER_ROOT, target: Path = PACKAGE_ROOT) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for spec in DOSSIERS:
        package = build_package(spec, dossier_root=dossier_root)
        package["package_sha256"] = package_digest(package)
        path = target / f"{spec.package_id}.json"
        path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def require_factory_ready(package: Mapping[str, Any]) -> None:
    """Fail closed before factory tasks are enqueued for curation-only packages."""
    summary = validate_package(package)
    if not summary["ready_for_article_generation"]:
        raise EvidencePackageError(
            f"{summary['package_id']} bloqueado para fábrica: material curatorial sem corpo-fonte verificável."
        )


def build_curated_trial_input(
    package: Mapping[str, Any],
    *,
    test_id: str,
    local_research_route: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deep-work trial from project-authored notes, never source bodies."""
    summary = validate_package(package)
    if not summary["curated_note_only_trial_ready"]:
        raise EvidencePackageError("No curated notes available for this deep-work trial.")
    if not isinstance(test_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{3,79}", test_id):
        raise EvidencePackageError("Invalid ENG-CODEX-009 test_id.")
    if local_research_route is not None:
        required = {"question", "purpose", "profile_id", "profile_version", "evidence_kind"}
        if set(local_research_route) != required or any(
            not isinstance(local_research_route.get(key), str) or not local_research_route[key].strip()
            for key in required
        ):
            raise EvidencePackageError("Local research route must be complete and typed.")
        research_questions = [{
            "question": local_research_route["question"],
            "purpose": local_research_route["purpose"],
        }]
    else:
        research_questions = []

    evidence: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for source in package["source_candidates"]:
        if source["source_body_status"] != "not_obtained" or not source["curator_note"]:
            unresolved.append({
                "source_id": source["source_id"],
                "title": source["title"],
                "candidate_status": source["source_body_status"],
                "curator_note": source["curator_note"],
            })
            continue
        evidence_id = f"note-{source['source_id'].lower()}"
        evidence.append({
            "evidence_id": evidence_id,
            "source_id": source["source_id"],
            "source_title": source["title"],
            "source_url": source["url"],
            "source_type": source["source_type"],
            "summary": source["curator_note"],
            "provenance_status": "project_curated_summary_not_independently_revalidated",
            "source_body_obtained": False,
            "rights_revalidated": False,
        })
        claims.append({
            "claim_id": f"claim-{source['source_id'].lower()}",
            "evidence_ids": [evidence_id],
            "epistemic_status": "curator_summary_not_independently_revalidated",
        })

    dossier_version = f"{package['curation_date']}:{package['dossier_sha256'][:12]}"
    brief: dict[str, Any] = {
        "test_id": test_id,
        "topic": package["topic"],
        "assignment": (
            "Write a complete, original long-form investigative and explanatory report in Brazilian Portuguese "
            "within the requested word range. Explain the subject and its meaningful parts before the verdict; "
            "compare supplied evidence and perspectives; make the reasoning between evidence and conclusions visible; "
            "describe methods, contradictions, uncertainty, consequences, and unanswered questions where the notes support them. "
            "Use only the supplied project-curated notes, attribute material claims by source_id, distinguish fact, "
            "reported opinion, and your own interpretation, and preserve missing evidence instead of filling it in. "
            "Do not claim direct URL access, gameplay, testing, interviews, or installs that did not occur. "
            "Do not add outside facts, present a curator summary as an inspected source body, or copy source wording."
        ),
        "language": "pt-BR",
        "article_form": "full_investigative_report_with_expository_body_and_supported_editorial_conclusion",
        "coverage_questions": list(package["coverage_questions"]),
        "permitted_research_scope": ["read:radar_index"],
        "research_questions": research_questions,
    }
    if local_research_route:
        brief["research_profile_id"] = local_research_route["profile_id"]
        brief["research_profile_version"] = local_research_route["profile_version"]
        brief["required_evidence_kinds"] = [local_research_route["evidence_kind"]]

    return {
        "editorial_brief": brief,
        "evidence_dossier": {
            "package_id": package["package_id"],
            "dossier_version": dossier_version,
            "dossier_sha256": package["dossier_sha256"],
            "evidence": evidence,
            "claims": claims,
            "unresolved_source_candidates": unresolved,
            "corpus_status": "curator_notes_only_source_bodies_not_obtained",
            "rights_review_status": "not_revalidated_for_this_run",
            "limitations": [
                "The system received project-authored summaries, not underlying third-party source bodies.",
                "No external retrieval is authorized; only the local Radar index may be queried.",
                "Factuality can be compared with these notes, but independent source verification is pending.",
            ],
        },
        "writing_constraints": {
            "target_word_range": list(package["requested_word_range"]),
            "no_major_spoilers": package["package_id"] == "eng-codex-009-beto",
            "no_install_or_execution": package["package_id"] == "eng-codex-009-nina",
            "never_claim_firsthand_testing": True,
            "do_not_copy_third_party_material": True,
            "retain_uncertainty_and_missing_evidence": True,
            "publication_state": "not_published",
        },
    }


if __name__ == "__main__":
    for path in write_package_manifests():
        print(path)
