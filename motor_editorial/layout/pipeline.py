"""Offline layout path executed by Motor's existing durable step mechanism."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .contracts import (
    SCHEMA_MEDIA,
    SCHEMA_REFERENCE,
    SCHEMA_STORY,
    ContractError,
    seal_artifact,
    sha256_json,
    story_revision_sha256,
    validate_media_inventory,
    validate_story_package,
)
from .engine import (
    build_visual_needs,
    plan_layout,
    render_preview,
    validate_plan,
    validate_rendered_preview,
)
from .index import LayoutReferenceIndex


DEFAULT_FIXTURE = Path(__file__).parent / "fixtures" / "layout-demo.json"
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")


def _read_fixture(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        fixture = json.load(stream)
    if not isinstance(fixture, dict) or fixture.get("fixture_version") != "LayoutDemoFixture.v0":
        raise ContractError("Fixture de layout precisa usar LayoutDemoFixture.v0.")
    if not isinstance(fixture.get("scenarios"), list) or len(fixture["scenarios"]) < 3:
        raise ContractError("A fixture precisa conter os três cenários de composição.")
    if not _SAFE_ID.fullmatch(str(fixture.get("run_id", ""))):
        raise ContractError("run_id da fixture é inválido.")
    return fixture


def _materialize_story(raw_payload: Mapping[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(dict(raw_payload))
    review = payload.get("review")
    if not isinstance(review, dict):
        raise ContractError("A fixture da matéria precisa declarar review.")
    review["reviewed_story_sha256"] = story_revision_sha256(payload)
    return validate_story_package(seal_artifact(
        str(payload.get("story_id", "")), SCHEMA_STORY,
        int(payload.get("story_revision", 0)), payload,
    ))


def _materialize_inventory(raw_payload: Mapping[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(dict(raw_payload))
    return validate_media_inventory(seal_artifact(
        str(payload.get("inventory_id", "")), SCHEMA_MEDIA,
        int(payload.get("revision", 0)), payload,
    ))


def _materialize_references(raw_references: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw in raw_references:
        payload = dict(raw)
        result.append(seal_artifact(
            str(payload.get("reference_id", "")), SCHEMA_REFERENCE,
            int(payload.get("revision", 0)), payload,
        ))
    return result


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_layout_demo(motor: Any, fixture_path: Path | None = None) -> dict[str, Any]:
    """Run three synthetic layout cases through Motor's existing stage ledger."""
    fixture = _read_fixture(fixture_path or DEFAULT_FIXTURE)
    run_id = fixture["run_id"]
    motor._ensure_run(run_id, fixture["label"])
    motor._set_run_status(run_id, "running")

    data_dir = Path(motor.store.db_path).resolve().parent
    index = LayoutReferenceIndex(data_dir / "layout-reference-index.sqlite3")
    references = _materialize_references(fixture["references"])
    index.add_references(references)
    index_sha256 = index.fingerprint()
    artifact_dir = Path(motor.store.artifact_dir).resolve() / "layout-demo"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    scenario_results: list[dict[str, Any]] = []
    for scenario in fixture["scenarios"]:
        scenario_id = str(scenario.get("scenario_id", ""))
        if not _SAFE_ID.fullmatch(scenario_id):
            raise ContractError("scenario_id da fixture é inválido.")
        story = _materialize_story(scenario["story_package"])
        inventory = _materialize_inventory(scenario["media_inventory"])
        story_payload = story["payload"]
        story_hash = story_revision_sha256(story_payload)
        story_key = story_hash[:16]

        needs = motor._execute_step(
            run_id, None, f"layout-{scenario_id}-needs-{story_key}",
            lambda connection, attempt, story=story: build_visual_needs(story),
        )
        needs_hash = sha256_json(needs)
        selected = motor._execute_step(
            run_id, None,
            f"layout-{scenario_id}-references-{story_key}-{needs_hash[:12]}-{index_sha256[:12]}",
            lambda connection, attempt, needs=needs: {
                "references": index.search(
                    [tag for need in needs["needs"] for tag in need["tags"]], limit=3
                ),
                "index_sha256": index_sha256,
            },
        )
        selected_references = selected["references"]
        selected_hash = sha256_json([
            {"reference_id": row["payload"]["reference_id"], "content_sha256": row["content_sha256"]}
            for row in selected_references
        ])
        plan = motor._execute_step(
            run_id, None,
            f"layout-{scenario_id}-plan-{story_key}-{inventory['content_sha256'][:12]}-{selected_hash[:12]}",
            lambda connection, attempt, story=story, inventory=inventory,
                   needs=needs, refs=selected_references: plan_layout(
                       story, inventory, needs, refs, index_sha256
                   ),
        )
        plan_hash = plan["content_sha256"]
        validation = motor._execute_step(
            run_id, None,
            f"layout-{scenario_id}-validate-{plan_hash[:16]}-{index_sha256[:12]}",
            lambda connection, attempt, story=story, inventory=inventory,
                   plan=plan: validate_plan(
                       story, inventory, plan, index_sha256, index.references()
                   ),
        )

        if validation["payload"]["status"] == "PASS":
            candidate_html = render_preview(story, plan, validation)
            candidate_sha256 = sha256_json(candidate_html)
            validation = motor._execute_step(
                run_id, None,
                f"layout-{scenario_id}-render-check-{plan_hash[:16]}-{candidate_sha256[:12]}",
                lambda connection, attempt, story=story, plan=plan,
                       base_validation=validation, html=candidate_html: validate_rendered_preview(
                           story, plan, base_validation, html
                       ),
            )

        name = scenario_id
        plan_path = artifact_dir / f"{name}-layout-plan.json"
        validation_path = artifact_dir / f"{name}-composition-validation.json"
        preview_path = artifact_dir / f"{name}-internal-preview.html"
        _write_json(plan_path, plan)
        preview_html = render_preview(story, plan, validation)
        _write_json(validation_path, validation)
        preview = motor._execute_step(
            run_id, None,
            f"layout-{scenario_id}-preview-{plan_hash[:16]}-{validation['content_sha256'][:12]}",
            lambda connection, attempt, path=preview_path, html=preview_html: {
                "preview_path": str(path),
                "preview_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
                "internal_only": True,
            },
        )
        # Restore a missing artifact on an idempotent rerun without repeating the stage.
        if not preview_path.is_file() or preview_path.read_text(encoding="utf-8") != preview_html:
            preview_path.write_text(preview_html, encoding="utf-8")

        validation_payload = validation["payload"]
        scenario_results.append({
            "scenario_id": scenario_id,
            "status": validation_payload["status"],
            "story_revision_sha256": story_hash,
            "media_inventory_sha256": inventory["content_sha256"],
            "reference_index_sha256": index_sha256,
            "reference_ids": [row["payload"]["reference_id"] for row in selected_references],
            "plan_sha256": plan_hash,
            "validation_sha256": validation["content_sha256"],
            "checks": validation_payload["checks"],
            "plan_path": str(plan_path),
            "validation_path": str(validation_path),
            "preview_path": preview["preview_path"],
            "preview_sha256": preview["preview_sha256"],
            "publication_state": "not_published",
        })

    passed = all(item["status"] == "PASS" for item in scenario_results)
    status = "awaiting_approval" if passed else "failed_intervention"
    motor._set_run_status(run_id, status)
    report = {
        "run_id": run_id,
        "status": status,
        "fixture_version": fixture["fixture_version"],
        "scenario_count": len(scenario_results),
        "scenario_results": scenario_results,
        "reference_index_path": str(index.database_path),
        "reference_index_sha256": index_sha256,
        "synthetic_fixture_only": True,
        "network_calls": 0,
        "siwc_calls": 0,
        "paid_api_calls": 0,
        "published": False,
    }
    _write_json(artifact_dir / "layout-demo-report.json", report)
    return report
