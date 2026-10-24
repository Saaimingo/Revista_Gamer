"""Synthetic diagrammer and deterministic composition checks."""

from __future__ import annotations

import html
import hashlib
import re
from typing import Any, Iterable, Mapping

from .contracts import (
    SCHEMA_PLAN,
    SCHEMA_VALIDATION,
    ContractError,
    profile_sha256,
    seal_artifact,
    story_revision_sha256,
    validate_composition_validation,
    validate_layout_plan,
    validate_media_inventory,
    validate_story_package,
)


DIAGRAMMER_IDENTITY = {
    "role": "diagrammer",
    "profile_id": "offline-deterministic-layout-planner",
    "version": "0.1.0",
    "description": "Planejador sintético que ordena módulos a partir de necessidades e referências funcionais.",
}

_SOURCE_ROLE_IDENTITIES = ("editor", "writer_persona", "reviewer")


def build_visual_needs(story_package: Mapping[str, Any]) -> dict[str, Any]:
    story = validate_story_package(story_package)
    needs: list[dict[str, Any]] = []
    for section in story["payload"]["sections"]:
        kind = section["kind"]
        if kind == "figure_request":
            needs.append({
                "need_id": f"images-{section['block_id']}",
                "function": "captioned_editorial_images",
                "source_block_ids": [section["block_id"]],
                "tags": ["reportage", "figure", "caption", "small-image"],
            })
        elif kind == "comparison":
            needs.append({
                "need_id": f"comparison-{section['block_id']}",
                "function": "intentional_comparison_spread",
                "source_block_ids": [section["block_id"]],
                "tags": ["comparison", "spread", "desktop", "mobile", "side-by-side"],
            })
        elif kind == "map_request":
            needs.append({
                "need_id": f"map-{section['block_id']}",
                "function": "panoramic_map_spread",
                "source_block_ids": [section["block_id"]],
                "tags": ["map", "panorama", "spread", "mobile", "continuous"],
            })
    if not needs:
        needs.append({
            "need_id": "text-flow",
            "function": "readable_editorial_text_flow",
            "source_block_ids": [section["block_id"] for section in story["payload"]["sections"]],
            "tags": ["reportage", "text", "reading-flow"],
        })
    return {
        "schema_version": "VisualNeeds.v0",
        "story_id": story["payload"]["story_id"],
        "story_revision_sha256": story_revision_sha256(story["payload"]),
        "needs": needs,
    }


def _assets_for_section(section: Mapping[str, Any]) -> list[str]:
    if section.get("kind") == "figure_request":
        return [str(figure["asset_id"]) for figure in section.get("figures", [])]
    if section.get("kind") == "comparison":
        return [str(item["asset_id"]) for item in section.get("items", []) if item.get("asset_id")]
    if section.get("kind") == "map_request":
        return [str(section["asset_id"])]
    return []


def _reader_layouts(story: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    kinds = {section["kind"] for section in story["payload"]["sections"]}
    if "map_request" in kinds:
        return {
            "desktop": {"composition": "panoramic-two-page-spread", "spread": True},
            "mobile": {
                "composition": "single-column",
                "fallback": "scrollable-panorama-with-zoom; readable-caption-below",
                "rotation_advice": "optional-horizontal-view",
            },
            "continuous": {"composition": "single-flow-with-expandable-panorama"},
        }
    if "comparison" in kinds:
        return {
            "desktop": {"composition": "two-page-comparison-spread", "spread": True},
            "mobile": {
                "composition": "single-column",
                "fallback": "stack-items-with-zoomable-placeholders",
                "rotation_advice": "optional-horizontal-view",
            },
            "continuous": {"composition": "inline-comparison-card"},
        }
    return {
        "desktop": {"composition": "editorial-page-flow", "spread": False},
        "mobile": {"composition": "single-column", "fallback": "reflow-text-and-figures"},
        "continuous": {"composition": "linear-editorial-flow"},
    }


def plan_layout(
    story_package: Mapping[str, Any],
    media_inventory: Mapping[str, Any],
    visual_needs: Mapping[str, Any],
    references: Iterable[Mapping[str, Any]],
    reference_index_sha256: str,
) -> dict[str, Any]:
    story = validate_story_package(story_package)
    inventory = validate_media_inventory(media_inventory)
    selected_references = list(references)
    payload = story["payload"]
    placements = []
    for position, section in enumerate(payload["sections"], start=1):
        placements.append({
            "block_id": section["block_id"],
            "component": section["kind"],
            "sequence": position,
            "asset_ids": _assets_for_section(section),
            "spread_id": (
                f"spread-{payload['story_id']}"
                if section["kind"] in {"comparison", "map_request"} else None
            ),
        })
    plan_payload = {
        "plan_id": f"layout-plan-{payload['story_id']}",
        "story_id": payload["story_id"],
        "story_revision_sha256": story_revision_sha256(payload),
        "media_inventory_sha256": inventory["content_sha256"],
        "reference_index_sha256": reference_index_sha256,
        "template_id": "revista-gamer-responsive-v0",
        "status": "proposed",
        "visual_needs": dict(visual_needs),
        "references": [
            {
                "reference_id": reference["payload"]["reference_id"],
                "content_sha256": reference["content_sha256"],
                "function": reference["payload"]["composition_function"],
                "selection_rationale": "Correspondência de tags com necessidade visual sintética; metadados sem página ou imagem-fonte.",
            }
            for reference in selected_references
        ],
        "block_placements": placements,
        "layouts": _reader_layouts(story),
        "media_inventory_id": inventory["payload"]["inventory_id"],
        "diagrammer_identity": DIAGRAMMER_IDENTITY,
        "source_role_identities": {
            role: {
                "profile_id": payload["identities"][role]["profile_id"],
                "version": payload["identities"][role]["version"],
                "profile_sha256": profile_sha256(payload["identities"][role]),
            }
            for role in _SOURCE_ROLE_IDENTITIES
        },
        "ad_slots": [],
    }
    return seal_artifact(
        plan_payload["plan_id"], SCHEMA_PLAN,
        payload["story_revision"], plan_payload,
    )


def validate_plan(
    story_package: Mapping[str, Any],
    media_inventory: Mapping[str, Any],
    plan: Mapping[str, Any],
    reference_index_sha256: str,
    indexed_references: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    story = validate_story_package(story_package)
    inventory = validate_media_inventory(media_inventory)
    checked_plan = validate_layout_plan(plan)
    payload = checked_plan["payload"]
    story_payload = story["payload"]
    ref_by_id = {
        reference["payload"]["reference_id"]: reference
        for reference in indexed_references
    }
    inventory_by_id = {
        asset["asset_id"]: asset
        for asset in inventory["payload"]["assets"]
    }
    input_block_ids = [section["block_id"] for section in story_payload["sections"]]
    plan_block_ids = [item["block_id"] for item in payload["block_placements"]]
    editorial_asset_ids = {
        asset_id
        for placement in payload["block_placements"]
        for asset_id in placement.get("asset_ids", [])
    }
    requested_asset_ids = {
        asset_id
        for section in story_payload["sections"]
        for asset_id in _assets_for_section(section)
    }
    checks: list[dict[str, str]] = []

    def check(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"check_id": check_id, "status": "PASS" if passed else "FAIL", "detail": detail})

    current_story_hash = story_revision_sha256(story_payload)
    check(
        "story_revision_current",
        payload["story_revision_sha256"] == current_story_hash
        and story_payload["review"]["reviewed_story_sha256"] == current_story_hash,
        "O plano e a revisão apontam para a revisão atual da matéria.",
    )
    expected_role_identities = {
        role: {
            "profile_id": story_payload["identities"][role]["profile_id"],
            "version": story_payload["identities"][role]["version"],
            "profile_sha256": profile_sha256(story_payload["identities"][role]),
        }
        for role in _SOURCE_ROLE_IDENTITIES
    }
    source_role_identities = payload.get("source_role_identities")
    role_identities_match = (
        isinstance(source_role_identities, Mapping)
        and set(source_role_identities) == set(expected_role_identities)
    )
    if role_identities_match:
        role_identities_match = all(
            isinstance(source_role_identities[role], Mapping)
            and all(
                source_role_identities[role].get(field) == expected_value
                for field, expected_value in expected.items()
            )
            for role, expected in expected_role_identities.items()
        )
    check(
        "source_role_identities_match_story_package",
        role_identities_match,
        "Editor, redator/persona e revisor no plano correspondem às identidades e hashes canônicos do StoryPackage.",
    )
    check(
        "media_inventory_current",
        payload["media_inventory_sha256"] == inventory["content_sha256"],
        "O plano depende do inventário de mídia vigente.",
    )
    check(
        "reference_index_current",
        payload["reference_index_sha256"] == reference_index_sha256,
        "O plano depende da versão atual do índice de referências.",
    )
    reference_rows = payload["references"]
    check(
        "three_references_present",
        len(reference_rows) == 3
        and all(
            row["reference_id"] in ref_by_id
            and ref_by_id[row["reference_id"]]["content_sha256"] == row["content_sha256"]
            for row in reference_rows
        ),
        "As três referências existem no índice e seus hashes conferem.",
    )
    check(
        "all_blocks_placed_once",
        len(input_block_ids) == len(plan_block_ids)
        and set(input_block_ids) == set(plan_block_ids)
        and len(plan_block_ids) == len(set(plan_block_ids)),
        "Cada bloco semântico da matéria aparece uma vez no plano.",
    )
    expected_sequences = list(range(1, len(input_block_ids) + 1))
    check(
        "editorial_order_and_sequence",
        plan_block_ids == input_block_ids
        and [placement["sequence"] for placement in payload["block_placements"]]
        == expected_sequences,
        "A ordem dos blocos e as sequências 1-based correspondem às sections do StoryPackage.",
    )
    check(
        "requested_assets_placed",
        requested_asset_ids == editorial_asset_ids,
        "O plano preserva todos os pedidos de mídia da matéria.",
    )

    media_allowed = True
    lineage_matches = True
    for asset_id in editorial_asset_ids:
        asset = inventory_by_id.get(asset_id)
        if asset is None:
            media_allowed = False
            lineage_matches = False
            continue
        if asset["media_kind"] == "advertising":
            media_allowed = False
            continue
        if asset["rights_status"] == "synthetic_fixture":
            media_allowed = (
                media_allowed
                and asset["media_kind"] == "placeholder"
                and asset["synthetic"] is True
                and asset["license"]["status"] == "not_applicable_synthetic_placeholder"
                and "internal_preview" in asset["permitted_modes"]
            )
        elif asset["rights_status"] == "authorized":
            media_allowed = (
                media_allowed
                and asset["media_kind"] == "editorial"
                and asset["license"]["status"] == "authorized"
                and "internal_preview" in asset["permitted_modes"]
            )
        else:
            media_allowed = False
    section_by_block = {section["block_id"]: section for section in story_payload["sections"]}
    for placement in payload["block_placements"]:
        section = section_by_block.get(placement["block_id"])
        for asset_id in placement.get("asset_ids", []):
            asset = inventory_by_id.get(asset_id)
            if asset is None or placement["block_id"] not in asset.get("linked_block_ids", []):
                lineage_matches = False
    check(
        "media_rights_gate",
        media_allowed,
        "Só mídia autorizada para prévia interna ou placeholder sintético pode entrar no plano.",
    )
    check(
        "asset_block_lineage",
        lineage_matches,
        "Cada ativo do inventário está ligado ao bloco semântico que o solicita.",
    )

    ad_slots = payload["ad_slots"]
    ad_asset_ids: set[str] = set()
    ads_valid = isinstance(ad_slots, list)
    ads_in_editorial = any(
        inventory_by_id.get(asset_id, {}).get("media_kind") == "advertising"
        for asset_id in editorial_asset_ids
    )
    for slot in ad_slots:
        if not isinstance(slot, Mapping):
            ads_valid = False
            continue
        asset_id = slot.get("asset_id")
        ad_asset_ids.add(asset_id)
        asset = inventory_by_id.get(asset_id)
        ads_valid = ads_valid and asset is not None and asset["media_kind"] == "advertising"
        ads_valid = ads_valid and asset is not None and asset["rights_status"] == "authorized"
        ads_valid = ads_valid and asset is not None and asset["license"]["status"] == "authorized"
        ads_valid = ads_valid and asset is not None and "internal_preview" in asset["permitted_modes"]
    check(
        "advertising_separated",
        ads_valid and not ads_in_editorial and not (ad_asset_ids & editorial_asset_ids),
        "Publicidade não pode ocupar blocos editoriais nem entrar sem autorização.",
    )

    captions_valid = True
    for section in story_payload["sections"]:
        if section["kind"] == "figure_request":
            captions_valid = captions_valid and all(
                bool(figure.get("caption", "").strip()) for figure in section["figures"]
            )
        elif section["kind"] == "comparison":
            captions_valid = captions_valid and all(
                bool(item.get("caption", "").strip()) for item in section["items"]
            )
        elif section["kind"] == "map_request":
            captions_valid = captions_valid and bool(section.get("caption", "").strip())
    check("figure_caption_association", captions_valid, "Cada imagem continua ligada à sua legenda.")

    has_spread = any(
        section["kind"] in {"comparison", "map_request"}
        for section in story_payload["sections"]
    )
    mobile = payload["layouts"]["mobile"]
    continuous = payload["layouts"]["continuous"]
    mobile_fallback = bool(mobile.get("fallback")) if has_spread else True
    check(
        "spread_mobile_fallback",
        mobile_fallback and bool(continuous.get("composition")),
        "Duplas mantêm alternativa legível em celular e no modo contínuo.",
    )
    check(
        "internal_only",
        "publication" not in payload and payload.get("status") == "proposed",
        "O plano é uma proposta interna e não autoriza publicação.",
    )

    passed = all(item["status"] == "PASS" for item in checks)
    validation_payload = {
        "plan_id": payload["plan_id"],
        "plan_sha256": checked_plan["content_sha256"],
        "story_revision_sha256": current_story_hash,
        "media_inventory_sha256": inventory["content_sha256"],
        "reference_index_sha256": reference_index_sha256,
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "preview_allowed": passed,
        "publication_state": "not_published",
    }
    return seal_artifact(
        f"composition-validation-{payload['plan_id']}",
        SCHEMA_VALIDATION, checked_plan["revision"], validation_payload,
    )


def render_preview(
    story_package: Mapping[str, Any],
    plan: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> str:
    story = validate_story_package(story_package)
    checked_plan = validate_layout_plan(plan)
    checked_validation = validate_composition_validation(validation)
    story_payload = story["payload"]
    plan_payload = checked_plan["payload"]
    validation_payload = checked_validation["payload"]
    if validation_payload["status"] != "PASS" or not validation_payload["preview_allowed"]:
        details = "".join(
            f"<li><strong>{html.escape(item['check_id'])}</strong>: {html.escape(item['detail'])}</li>"
            for item in validation_payload["checks"] if item["status"] == "FAIL"
        )
        return _document(
            story_payload["title"],
            "<main><h1>Prévia bloqueada</h1><p>O validador não liberou a composição para visualização de conteúdo.</p>"
            f"<ul>{details}</ul></main>",
        )

    placement_by_id = {item["block_id"]: item for item in plan_payload["block_placements"]}
    body: list[str] = [
        '<main class="page-pair" aria-label="Prévia interna da matéria">',
        '<header class="story-header">',
        f"<p class=\"eyebrow\">{html.escape(story_payload['edition_id'])} · MOCK FICTÍCIO</p>",
        f"<h1>{html.escape(story_payload['title'])}</h1>",
        f"<p class=\"dek\">{html.escape(story_payload['dek'])}</p>",
        "</header>",
    ]
    for section in story_payload["sections"]:
        block_id = section["block_id"]
        placement = placement_by_id[block_id]
        kind = section["kind"]
        content = html.escape(section["text"])
        if kind == "heading":
            body.append(
                f'<section data-block-id="{html.escape(block_id)}" class="content-block"><h2>{content}</h2></section>'
            )
        elif kind == "paragraph":
            body.append(
                f'<section data-block-id="{html.escape(block_id)}" class="content-block"><p>{content}</p></section>'
            )
        elif kind == "figure_request":
            figures = []
            for figure in section["figures"]:
                figures.append(
                    '<figure class="context-figure">'
                    f'<div class="asset-placeholder" role="img" aria-label="{html.escape(figure["alt_text"])}">'
                    f'Placeholder sintético · {html.escape(figure["asset_id"])}'
                    '</div>'
                    f'<figcaption>{html.escape(figure["caption"])}</figcaption>'
                    '</figure>'
                )
            body.append(
                f'<section data-block-id="{html.escape(block_id)}" class="content-block">'
                f'<p>{content}</p><div class="figure-pair">{"".join(figures)}</div></section>'
            )
        elif kind == "comparison":
            groups = {2: [], 3: []}
            for index, item in enumerate(section["items"]):
                page_number = 2 if index == 0 else 3
                groups[page_number].append(
                    '<figure class="comparison-item">'
                    f'<div class="asset-placeholder" role="img" aria-label="{html.escape(item["label"])}">'
                    f'Placeholder sintético · {html.escape(item["asset_id"])}'
                    '</div>'
                    f'<h3>{html.escape(item["label"])}</h3>'
                    f'<p>{html.escape(item["detail"])}</p>'
                    f'<figcaption>{html.escape(item["caption"])}</figcaption>'
                    '</figure>'
                )
            spread_id = html.escape(placement["spread_id"] or f"spread-{block_id}")
            body.append(
                f'<section data-block-id="{html.escape(block_id)}" data-spread-id="{spread_id}" '
                'class="spread-block comparison-spread">'
                f'<p class="spread-intro">{content}</p>'
                '<p class="mobile-guidance">Em telas estreitas, você pode girar o aparelho se preferir. '
                'Se a rotação estiver bloqueada, os itens ficam em coluna e continuam legíveis.</p>'
                '<article class="spread-page" data-page-number="2"><span class="page-number">Página 2</span>'
                f'{"".join(groups[2])}</article>'
                '<article class="spread-page" data-page-number="3"><span class="page-number">Página 3</span>'
                f'{"".join(groups[3])}</article>'
                '</section>'
            )
        elif kind == "map_request":
            map_id = f"map-{block_id}"
            spread_id = html.escape(placement["spread_id"] or f"spread-{block_id}")
            body.append(
                f'<section data-block-id="{html.escape(block_id)}" data-spread-id="{spread_id}" '
                'class="spread-block map-section">'
                f'<p class="spread-intro">{content}</p>'
                '<p class="mobile-guidance">Em telas estreitas, você pode girar o aparelho se quiser. '
                'Se a rotação estiver bloqueada, percorra o mapa na horizontal, use o zoom e leia em modo Contínua.</p>'
                f'<figure class="panorama-spread"><div class="panorama-scroll" tabindex="0" '
                f'aria-label="Mapa panorâmico com rolagem horizontal"><div id="{html.escape(map_id)}" '
                'class="panorama-canvas" data-zoom="normal" role="img" '
                f'aria-label="{html.escape(section["alt_text"])}">'
                '<span class="map-half" data-page-number="2"><span class="page-number">Página 2</span>'
                f'Mapa fictício · {html.escape(section["asset_id"])} · metade inicial</span>'
                '<span class="map-half" data-page-number="3"><span class="page-number">Página 3</span>'
                'Continuação do mapa fictício · metade final</span>'
                f'</div></div><figcaption>{html.escape(section["caption"])}</figcaption></figure>'
                f'<button class="zoom-toggle" type="button" aria-pressed="false" '
                f'aria-controls="{html.escape(map_id)}">Ampliar mapa</button>'
                '</section>'
            )
    body.extend([
        '<p class="internal-note">Prévia local de Fase 0 · conteúdo fictício · não publicar</p>',
        '</main>',
    ])
    return _document(story_payload["title"], "".join(body), plan_payload["layouts"])


def validate_rendered_preview(
    story_package: Mapping[str, Any],
    plan: Mapping[str, Any],
    validation: Mapping[str, Any],
    preview_html: str,
) -> dict[str, Any]:
    """Add deterministic checks for text, captions, responsive modes and clipping."""
    story = validate_story_package(story_package)
    checked_plan = validate_layout_plan(plan)
    checked_validation = validate_composition_validation(validation)
    base = checked_validation["payload"]
    if base["status"] != "PASS":
        return checked_validation

    story_payload = story["payload"]
    required_text = [story_payload["title"], story_payload["dek"]]
    required_captions: list[str] = []
    for section in story_payload["sections"]:
        required_text.append(section["text"])
        if section["kind"] == "figure_request":
            for figure in section["figures"]:
                required_text.append(figure["alt_text"])
                required_captions.append(figure["caption"])
        elif section["kind"] == "comparison":
            for item in section["items"]:
                required_text.extend((item["label"], item["detail"]))
                required_captions.append(item["caption"])
        elif section["kind"] == "map_request":
            required_text.append(section["alt_text"])
            required_captions.append(section["caption"])
    text_complete = all(html.escape(value) in preview_html for value in required_text)
    ids_complete = all(
        preview_html.count(f'data-block-id="{html.escape(section["block_id"])}"') == 1
        for section in story_payload["sections"]
    )
    captions_associated = all(
        f"<figcaption>{html.escape(caption)}</figcaption>" in preview_html
        for caption in required_captions
    )
    no_hidden_overflow = not re.search(
        r"overflow\s*:\s*hidden|display\s*:\s*none", preview_html, flags=re.IGNORECASE
    )
    modes_present = (
        'data-mode="folhear"' in preview_html
        and "data-mode=continuous" in preview_html
        and "Alternar para leitura contínua" in preview_html
        and "viewport" in preview_html
    )
    has_spread = any(
        section["kind"] in {"comparison", "map_request"}
        for section in story_payload["sections"]
    )
    spread_pages_present = (
        not has_spread
        or (
            'data-page-number="2"' in preview_html
            and 'data-page-number="3"' in preview_html
            and "grid-template-columns:repeat(2,minmax(0,1fr))" in preview_html
        )
    )
    rotation_fallback_present = (
        not has_spread
        or (
            "girar o aparelho" in preview_html
            and "rotação estiver bloqueada" in preview_html
            and "coluna" in preview_html
        )
    )
    map_has_zoom = not any(
        section["kind"] == "map_request"
        for section in story_payload["sections"]
    ) or (
        "zoom-toggle" in preview_html
        and "Ampliar mapa" in preview_html
        and "overflow:auto" in preview_html
    )
    local_only = not re.search(
        r"<img\b|<iframe\b|<script\s+src|https?://", preview_html,
        flags=re.IGNORECASE,
    )
    checks = list(base["checks"])
    checks.extend([
        {"check_id": "rendered_text_integrity", "status": "PASS" if text_complete and ids_complete else "FAIL",
         "detail": "Texto, títulos e IDs semânticos aparecem no HTML interno."},
        {"check_id": "rendered_caption_association", "status": "PASS" if captions_associated else "FAIL",
         "detail": "Legendas permanecem em figcaption junto ao respectivo placeholder."},
        {"check_id": "responsive_reader_modes", "status": "PASS" if modes_present else "FAIL",
         "detail": "A prévia oferece Folhear, Contínua e viewport responsivo."},
        {"check_id": "spread_pages_side_by_side", "status": "PASS" if spread_pages_present else "FAIL",
         "detail": "A dupla identifica as páginas 2 e 3 e oferece grade lado a lado em desktop."},
        {"check_id": "mobile_rotation_fallback", "status": "PASS" if rotation_fallback_present else "FAIL",
         "detail": "A orientação horizontal é opcional e a alternativa em coluna continua disponível."},
        {"check_id": "panorama_zoom_and_scroll", "status": "PASS" if map_has_zoom else "FAIL",
         "detail": "O panorama oferece controle de zoom e rolagem horizontal."},
        {"check_id": "no_hidden_overflow", "status": "PASS" if no_hidden_overflow else "FAIL",
         "detail": "A composição não usa overflow:hidden nem display:none para ocultar conteúdo."},
        {"check_id": "internal_artifact_only", "status": "PASS" if local_only else "FAIL",
         "detail": "A prévia não carrega imagens, iframes, scripts remotos ou URLs externas."},
    ])
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    payload = {
        **dict(base),
        "status": status,
        "checks": checks,
        "preview_allowed": status == "PASS",
        "rendered_preview_sha256": hashlib.sha256(preview_html.encode("utf-8")).hexdigest(),
    }
    return seal_artifact(
        checked_validation["artifact_id"], SCHEMA_VALIDATION,
        checked_validation["revision"], payload,
    )


def _document(title: str, body: str, layouts: Mapping[str, Any] | None = None) -> str:
    layouts = layouts or {}
    encoded_layouts = html.escape(str(layouts.get("desktop", {}).get("composition", "single-column")))
    body = body.replace(
        'class="page-pair"',
        f'class="page-pair" data-layout="{encoded_layouts}"',
        1,
    )
    return (
        "<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)} · prévia interna</title>"
        "<style>"
        ":root{font-family:system-ui,sans-serif;color:#171717;background:#ececec}"
        "*{box-sizing:border-box}body{margin:0;line-height:1.6}"
        ".toolbar{display:flex;gap:.75rem;align-items:center;justify-content:space-between;padding:1rem;"
        "background:#181818;color:#fff}.toolbar button{font:inherit;padding:.5rem .8rem}"
        ".notice{font-weight:700;color:#ffd35a}.page-pair{display:grid;grid-template-columns:minmax(0,1fr);"
        "gap:1rem;max-width:1280px;margin:1rem auto;padding:0 1rem}.story-header,.content-block,.internal-note{"
        "min-width:0}.story-header{grid-column:1/-1}.spread-block{display:grid;grid-template-columns:minmax(0,1fr);"
        "gap:1rem;margin:1.5rem 0}.spread-intro,.mobile-guidance,.panorama-spread{grid-column:1/-1}"
        ".spread-page{background:#fff;padding:clamp(1rem,4vw,3rem);border:1px solid #d0d0d0;min-width:0}"
        ".page-number{display:block;font-size:.8rem;font-weight:700;color:#555;margin-bottom:.75rem}"
        ".eyebrow{font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;color:#8a1025}"
        "h1{font-size:clamp(2rem,5vw,4rem);line-height:1.05;margin:.25em 0}h2{font-size:1.6rem;line-height:1.2}"
        ".dek{font-size:1.2rem;color:#444}.content-block{margin:1.5rem 0}.figure-pair,.comparison-grid{display:grid;"
        "grid-template-columns:minmax(0,1fr);gap:1rem}.context-figure,figure{margin:1rem 0}.asset-placeholder,.panorama-canvas{"
        "display:grid;place-items:center;min-height:9rem;padding:1rem;background:#d9dce2;color:#30343b;text-align:center;"
        "border:1px dashed #687080}.panorama-scroll{max-width:100%;overflow:auto;overscroll-behavior-inline:contain}"
        ".panorama-canvas{display:grid;grid-template-columns:repeat(2,minmax(20rem,1fr));min-width:42rem;"
        "min-height:14rem;background:linear-gradient(120deg,#d9dce2,#c2c9d3);transition:transform .15s ease}"
        ".panorama-canvas[data-zoom=large]{transform:scale(1.35);transform-origin:left top}"
        ".map-half{display:grid;align-content:center;min-height:14rem;padding:1rem;border:1px dashed #687080;text-align:center}"
        "figcaption,.caption{font-size:.92rem;color:#424242;margin-top:.5rem}.comparison-item{border:1px solid #c5c5c5;padding:1rem}"
        ".mobile-guidance{padding:.75rem 1rem;background:#fff7df;border-left:4px solid #a36b00}"
        ".zoom-toggle{font:inherit;padding:.5rem .8rem}.panorama-spread{min-width:0}"
        ".internal-note{border-top:1px solid #aaa;padding-top:1rem;color:#7b1023;font-weight:700}"
        ".reader[data-mode=continuous] .page-pair{display:block}"
        ".reader[data-mode=continuous] .spread-block{grid-template-columns:minmax(0,1fr)}"
        ".reader[data-mode=continuous] .spread-page{margin:0 auto 1rem}"
        ".reader[data-mode=continuous] .panorama-canvas{grid-template-columns:minmax(0,1fr);min-width:0}"
        ".reader[data-mode=folhear] .page-pair{display:grid}"
        "@media(min-width:900px){.spread-block{grid-template-columns:repeat(2,minmax(0,1fr))}"
        ".figure-pair,.comparison-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}"
        "@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}"
        "</style></head><body><div class=\"reader\" data-mode=\"folhear\">"
        "<div class=\"toolbar\"><span class=\"notice\">SIMULAÇÃO INTERNA — NÃO PUBLICAR</span>"
        "<button id=\"mode-toggle\" type=\"button\" aria-pressed=\"false\">Alternar para leitura contínua</button></div>"
        f"<div class=\"layout-marker\" data-desktop-composition=\"{encoded_layouts}\"></div>"
        f"{body}"
        "<script>const root=document.querySelector('.reader');const button=document.getElementById('mode-toggle');"
        "button.addEventListener('click',()=>{const continuous=root.dataset.mode!=='continuous';"
        "root.dataset.mode=continuous?'continuous':'folhear';button.setAttribute('aria-pressed',String(continuous));"
        "button.textContent=continuous?'Alternar para modo Folhear':'Alternar para leitura contínua';});"
        "document.querySelectorAll('.zoom-toggle').forEach(control=>{const canvas=document.getElementById(control.getAttribute('aria-controls'));"
        "control.addEventListener('click',()=>{const zoomed=canvas.dataset.zoom!=='large';canvas.dataset.zoom=zoomed?'large':'normal';"
        "control.setAttribute('aria-pressed',String(zoomed));control.textContent=zoomed?'Reduzir mapa':'Ampliar mapa';});});</script>"
        "</div></body></html>"
    )
