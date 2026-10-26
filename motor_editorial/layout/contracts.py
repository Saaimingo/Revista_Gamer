"""Versioned, dependency-free JSON contracts for offline composition."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


SCHEMA_STORY = "StoryPackage.v0"
SCHEMA_MEDIA = "MediaInventory.v0"
SCHEMA_REFERENCE = "LayoutReference.v0"
SCHEMA_PLAN = "LayoutPlan.v0"
SCHEMA_VALIDATION = "CompositionValidation.v0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SECTION_KINDS = {"heading", "paragraph", "figure_request", "comparison", "map_request"}
_LICENSE_STATUSES = {
    "authorized", "pending", "blocked", "not_applicable_synthetic_placeholder",
    "not_applicable_synthetic_generated",
}


class ContractError(ValueError):
    """Raised when a versioned layout artifact is incomplete or stale."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def seal_artifact(
    artifact_id: str, schema_version: str, revision: int, payload: Mapping[str, Any]
) -> dict[str, Any]:
    if not artifact_id or not schema_version or revision < 1:
        raise ContractError("Artifact id, schema version e revisão são obrigatórios.")
    payload_copy = dict(payload)
    return {
        "artifact_id": artifact_id,
        "schema_version": schema_version,
        "revision": revision,
        "content_sha256": sha256_json(payload_copy),
        "payload": payload_copy,
    }


def validate_envelope(value: Any, schema_version: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError("O artefato precisa ser um objeto JSON.")
    if value.get("schema_version") != schema_version:
        raise ContractError(f"schema_version precisa ser {schema_version}.")
    artifact_id = value.get("artifact_id")
    revision = value.get("revision")
    payload = value.get("payload")
    digest = value.get("content_sha256")
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        raise ContractError("artifact_id precisa ser um texto não vazio.")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ContractError("revision precisa ser um inteiro positivo.")
    if not isinstance(payload, Mapping):
        raise ContractError("payload precisa ser um objeto JSON.")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ContractError("content_sha256 precisa conter 64 caracteres hexadecimais.")
    if digest != sha256_json(payload):
        raise ContractError("content_sha256 não corresponde ao payload vigente.")
    return dict(value)


def story_revision_sha256(payload: Mapping[str, Any]) -> str:
    """Hash only the reviewed article revision, excluding the review itself."""
    revision = {
        "story_id": payload.get("story_id"),
        "story_revision": payload.get("story_revision"),
        "title": payload.get("title"),
        "dek": payload.get("dek"),
        "sections": payload.get("sections"),
        "source_ids": payload.get("source_ids"),
        "identities": payload.get("identities"),
    }
    return sha256_json(revision)


def profile_sha256(identity: Mapping[str, Any]) -> str:
    return sha256_json({
        "role": identity.get("role"),
        "profile_id": identity.get("profile_id"),
        "version": identity.get("version"),
        "description": identity.get("description"),
    })


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} precisa ser um texto não vazio.")
    return value


def _validate_identity(identity: Any, role: str) -> dict[str, Any]:
    if not isinstance(identity, Mapping):
        raise ContractError(f"Identidade de {role} ausente.")
    if identity.get("role") != role:
        raise ContractError(f"A identidade precisa declarar o papel {role}.")
    for field in ("profile_id", "version", "description"):
        _nonempty(identity.get(field), f"identities.{role}.{field}")
    return {
        **dict(identity),
        "profile_sha256": profile_sha256(identity),
    }


def validate_story_package(value: Any) -> dict[str, Any]:
    artifact = validate_envelope(value, SCHEMA_STORY)
    payload = artifact["payload"]
    for field in ("story_id", "edition_id", "title", "dek"):
        _nonempty(payload.get(field), f"StoryPackage.payload.{field}")
    revision = payload.get("story_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ContractError("story_revision precisa ser um inteiro positivo.")
    sections = payload.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ContractError("StoryPackage precisa conter sections.")
    seen: set[str] = set()
    for index, section in enumerate(sections):
        if not isinstance(section, Mapping):
            raise ContractError(f"sections[{index}] precisa ser um objeto.")
        block_id = _nonempty(section.get("block_id"), f"sections[{index}].block_id")
        if block_id in seen:
            raise ContractError(f"block_id repetido: {block_id}.")
        seen.add(block_id)
        if section.get("kind") not in _SECTION_KINDS:
            raise ContractError(f"Tipo de bloco não suportado em {block_id}.")
        _nonempty(section.get("text"), f"sections[{index}].text")
        source_ids = section.get("source_ids", [])
        if not isinstance(source_ids, list) or any(not isinstance(item, str) for item in source_ids):
            raise ContractError(f"sections[{index}].source_ids precisa ser uma lista de textos.")
        if section.get("kind") == "figure_request":
            figures = section.get("figures")
            if not isinstance(figures, list) or not figures:
                raise ContractError(f"figure_request {block_id} precisa listar figuras e legendas.")
            for figure in figures:
                if not isinstance(figure, Mapping):
                    raise ContractError(f"Figura inválida em {block_id}.")
                for field in ("asset_id", "caption", "alt_text"):
                    _nonempty(figure.get(field), f"{block_id}.{field}")
        if section.get("kind") == "comparison":
            items = section.get("items")
            if not isinstance(items, list) or len(items) < 2:
                raise ContractError(f"Comparação {block_id} precisa de ao menos dois itens.")
            for item in items:
                if not isinstance(item, Mapping):
                    raise ContractError(f"Item de comparação inválido em {block_id}.")
                for field in ("label", "detail", "asset_id", "caption"):
                    _nonempty(item.get(field), f"{block_id}.{field}")
        if section.get("kind") == "map_request":
            _nonempty(section.get("asset_id"), f"{block_id}.asset_id")
            _nonempty(section.get("caption"), f"{block_id}.caption")
            _nonempty(section.get("alt_text"), f"{block_id}.alt_text")

    source_ids = payload.get("source_ids")
    if not isinstance(source_ids, list) or not source_ids:
        raise ContractError("StoryPackage precisa declarar source_ids, inclusive IDs de fixture.")
    if any(not isinstance(item, str) or not item.strip() for item in source_ids):
        raise ContractError("source_ids contém um valor inválido.")
    identities = payload.get("identities")
    if not isinstance(identities, Mapping):
        raise ContractError("StoryPackage precisa registrar identities.")
    for role in ("editor", "writer_persona", "reviewer"):
        _validate_identity(identities.get(role), role)

    review = payload.get("review")
    if not isinstance(review, Mapping) or review.get("verdict") != "pass":
        raise ContractError("A fixture precisa trazer uma revisão sintética aprovada.")
    reviewed_hash = review.get("reviewed_story_sha256")
    if reviewed_hash != story_revision_sha256(payload):
        raise ContractError("A revisão não corresponde ao hash da matéria vigente.")
    if review.get("synthetic_fixture") is not True:
        raise ContractError("A revisão do ensaio precisa estar identificada como sintética.")
    return artifact


def validate_media_inventory(value: Any) -> dict[str, Any]:
    artifact = validate_envelope(value, SCHEMA_MEDIA)
    payload = artifact["payload"]
    _nonempty(payload.get("inventory_id"), "MediaInventory.payload.inventory_id")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise ContractError("MediaInventory.payload.assets precisa ser uma lista.")
    seen: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, Mapping):
            raise ContractError(f"assets[{index}] precisa ser um objeto.")
        asset_id = _nonempty(asset.get("asset_id"), f"assets[{index}].asset_id")
        if asset_id in seen:
            raise ContractError(f"asset_id repetido: {asset_id}.")
        seen.add(asset_id)
        if asset.get("media_kind") not in {
            "placeholder", "synthetic_generated", "editorial", "advertising"
        }:
            raise ContractError(f"media_kind inválido para {asset_id}.")
        if asset.get("rights_status") not in {
            "authorized", "pending", "blocked", "synthetic_fixture"
        }:
            raise ContractError(f"rights_status inválido para {asset_id}.")
        for field in ("rights_holder", "origin", "credit"):
            _nonempty(asset.get(field), f"assets[{index}].{field}")
        transformations = asset.get("permitted_transformations")
        linked_blocks = asset.get("linked_block_ids")
        if not isinstance(transformations, list) or any(not isinstance(item, str) for item in transformations):
            raise ContractError(f"permitted_transformations inválido para {asset_id}.")
        if not isinstance(linked_blocks, list) or any(not isinstance(item, str) for item in linked_blocks):
            raise ContractError(f"linked_block_ids inválido para {asset_id}.")
        license_info = asset.get("license")
        license_status = license_info.get("status") if isinstance(license_info, Mapping) else None
        if not isinstance(license_status, str) or license_status not in _LICENSE_STATUSES:
            raise ContractError(
                f"license.status precisa usar um estado conhecido para {asset_id}."
            )
        asset_sha256 = asset.get("asset_sha256")
        dimensions = asset.get("dimensions")
        if asset.get("media_kind") == "placeholder":
            if asset_sha256 is not None or dimensions is not None:
                raise ContractError(f"Placeholder {asset_id} não pode fingir bytes ou dimensões de imagem.")
        elif asset.get("media_kind") == "synthetic_generated":
            if asset.get("rights_status") != "synthetic_fixture":
                raise ContractError(f"Imagem gerada {asset_id} precisa manter rights_status=synthetic_fixture.")
            if license_status != "not_applicable_synthetic_generated":
                raise ContractError(f"Imagem gerada {asset_id} precisa da licença sintética específica.")
            if asset.get("synthetic") is not True:
                raise ContractError(f"Imagem gerada {asset_id} precisa marcar synthetic=true.")
            if not isinstance(asset_sha256, str) or not _SHA256_RE.fullmatch(asset_sha256):
                raise ContractError(f"Imagem gerada {asset_id} precisa ter SHA-256.")
            if not isinstance(dimensions, Mapping) or not all(
                isinstance(dimensions.get(key), int) and dimensions[key] > 0
                for key in ("width", "height")
            ):
                raise ContractError(f"Imagem gerada {asset_id} precisa ter dimensões verificadas.")
        elif asset.get("rights_status") == "authorized":
            if not isinstance(asset_sha256, str) or not _SHA256_RE.fullmatch(asset_sha256):
                raise ContractError(f"Mídia autorizada {asset_id} precisa ter SHA-256.")
            if not isinstance(dimensions, Mapping) or not all(
                isinstance(dimensions.get(key), int) and dimensions[key] > 0
                for key in ("width", "height")
            ):
                raise ContractError(f"Mídia autorizada {asset_id} precisa ter dimensões verificadas.")
        modes = asset.get("permitted_modes")
        if not isinstance(modes, list) or any(not isinstance(mode, str) for mode in modes):
            raise ContractError(f"permitted_modes inválido para {asset_id}.")
        if asset.get("media_kind") == "synthetic_generated" and modes != ["internal_preview"]:
            raise ContractError(f"Imagem gerada {asset_id} só pode ser usada em prévia interna.")
        if asset.get("rights_status") == "synthetic_fixture" and asset.get("synthetic") is not True:
            raise ContractError(f"{asset_id} precisa marcar synthetic=true.")
    return artifact


def validate_layout_reference(value: Any) -> dict[str, Any]:
    artifact = validate_envelope(value, SCHEMA_REFERENCE)
    payload = artifact["payload"]
    for field in (
        "reference_id", "title", "description", "era", "composition_function",
        "editorial_purpose", "problem_solved", "strengths", "limitations",
        "digital_adaptation", "confidence", "access_scope",
    ):
        _nonempty(payload.get(field), f"LayoutReference.payload.{field}")
    if not isinstance(payload.get("orientation"), str) or not payload["orientation"]:
        raise ContractError("LayoutReference.orientation precisa ser registrada.")
    for field in ("source_publication", "source_year", "source_page", "position"):
        if field not in payload:
            raise ContractError(f"LayoutReference precisa registrar {field}, usando null se desconhecido.")
    tags = payload.get("tags")
    if not isinstance(tags, list) or not tags or any(not isinstance(tag, str) for tag in tags):
        raise ContractError("LayoutReference.tags precisa conter tags de busca.")
    media_roles = payload.get("media_roles")
    if not isinstance(media_roles, list) or not media_roles or any(
        not isinstance(role, str) or not role.strip() for role in media_roles
    ):
        raise ContractError("LayoutReference.media_roles precisa declarar papéis de mídia pesquisáveis.")
    affordances = payload.get("digital_affordances")
    if not isinstance(affordances, list) or any(not isinstance(item, str) for item in affordances):
        raise ContractError("LayoutReference.digital_affordances precisa ser uma lista.")
    if payload.get("source_type") != "synthetic_fixture" or payload.get("rights_scope") != "metadata_only":
        raise ContractError("A Fase 0 aceita somente metadados sintéticos de referência.")
    if any(key in payload for key in ("image_path", "scan_path", "image_bytes", "url")):
        raise ContractError("LayoutReference não pode carregar scans, bytes ou fontes remotas.")
    return artifact


def validate_layout_plan(value: Any) -> dict[str, Any]:
    artifact = validate_envelope(value, SCHEMA_PLAN)
    payload = artifact["payload"]
    for field in (
        "plan_id", "story_id", "story_revision_sha256", "media_inventory_sha256",
        "reference_index_sha256", "template_id",
    ):
        _nonempty(payload.get(field), f"LayoutPlan.payload.{field}")
    if payload.get("status") != "proposed":
        raise ContractError("LayoutPlan precisa permanecer uma proposta revisável.")
    refs = payload.get("references")
    if not isinstance(refs, list) or len(refs) != 3:
        raise ContractError("LayoutPlan precisa registrar exatamente três referências.")
    reference_ids: set[str] = set()
    for ref in refs:
        if not isinstance(ref, Mapping):
            raise ContractError("Referência do LayoutPlan inválida.")
        for field in ("reference_id", "content_sha256", "function", "selection_rationale"):
            _nonempty(ref.get(field), f"LayoutPlan.references.{field}")
        if ref["reference_id"] in reference_ids:
            raise ContractError("LayoutPlan não pode repetir uma referência.")
        reference_ids.add(ref["reference_id"])
    placements = payload.get("block_placements")
    if not isinstance(placements, list) or not placements:
        raise ContractError("LayoutPlan precisa mapear blocos semânticos.")
    if any(not isinstance(placement, Mapping) for placement in placements):
        raise ContractError("Cada block_placement precisa ser um objeto.")
    placed = [placement.get("block_id") for placement in placements]
    if len(set(placed)) != len(placed):
        raise ContractError("Cada bloco deve aparecer exatamente uma vez no LayoutPlan.")
    sequences = [placement.get("sequence") for placement in placements]
    if any(
        not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1
        for sequence in sequences
    ):
        raise ContractError("Cada bloco precisa ter sequence como inteiro positivo.")
    if len(set(sequences)) != len(sequences):
        raise ContractError("Cada sequence precisa ser única no LayoutPlan.")
    layouts = payload.get("layouts")
    if not isinstance(layouts, Mapping) or any(
        not isinstance(layouts.get(mode), Mapping) for mode in ("desktop", "mobile", "continuous")
    ):
        raise ContractError("LayoutPlan precisa descrever desktop, mobile e continuous.")
    role = payload.get("diagrammer_identity")
    _validate_identity(role, "diagrammer")
    ad_slots = payload.get("ad_slots")
    if not isinstance(ad_slots, list):
        raise ContractError("ad_slots precisa ser uma lista, mesmo quando vazia.")
    return artifact


def validate_composition_validation(value: Any) -> dict[str, Any]:
    artifact = validate_envelope(value, SCHEMA_VALIDATION)
    payload = artifact["payload"]
    for field in ("plan_id", "plan_sha256", "story_revision_sha256", "status"):
        _nonempty(payload.get(field), f"CompositionValidation.payload.{field}")
    if payload.get("status") not in {"PASS", "FAIL", "INCONCLUSIVE"}:
        raise ContractError("CompositionValidation.status inválido.")
    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ContractError("CompositionValidation precisa registrar checks.")
    for check in checks:
        if not isinstance(check, Mapping) or check.get("status") not in {"PASS", "FAIL"}:
            raise ContractError("Cada check precisa declarar PASS ou FAIL.")
        _nonempty(check.get("check_id"), "CompositionValidation.check_id")
        _nonempty(check.get("detail"), "CompositionValidation.detail")
    expected_status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    if payload["status"] != expected_status:
        raise ContractError("CompositionValidation.status não corresponde aos checks.")
    return artifact


def story_text_blocks(story: Mapping[str, Any]) -> list[str]:
    payload = story["payload"]
    return [
        str(section["text"])
        for section in payload["sections"]
    ]
