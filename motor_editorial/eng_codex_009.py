"""Prepare and run the private, curator-note-only ENG-CODEX-009 journalist trials.

This harness reads pinned persona documents from the approved Bloco 02 Git refs,
uses the existing AgentQueue/TaskDispatcher/SIWC role executor, and never prints
article text. Source bodies and rights remain explicitly unverified for this run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .agent_contracts import (
    AgentTaskEnvelope,
    enqueue_contract_task,
    load_builtin_role_catalog,
)
from .agent_siwc import (
    SIWC_ROLE_EXECUTOR_ID,
    SIWC_ROLE_EXECUTOR_PROFILE,
    register_siwc_role_executor,
)
from .db import Store, json_dumps, stable_hash
from .evidence_packages import (
    DOSSIERS,
    PACKAGE_ROOT,
    build_curated_trial_input,
    load_package,
    write_package_manifests,
)
from .orchestration import AgentQueue, TaskDispatcher, TaskFailure
from .siwc import CredentialStore, SIWCClient, SIWCError


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".codex" / "Revista_Gamer" / "ensaios-009"
MODEL = "gpt-6-luna"
REASONING_EFFORT = "max"
ROLE_ID = "persona_writer"
_NAMESPACE = uuid.UUID("588b8bcb-49b7-442f-8da2-c78f00225f42")
_WORD_RE = re.compile(r"\b[\wÀ-ÿ]+(?:[’'-][\wÀ-ÿ]+)*\b", re.UNICODE)
_RESEARCH_PROFILES = {
    "eng-codex-009-carranca": ("research.hardware.v1", "independent_measurement"),
    "eng-codex-009-beto": ("research.games.v1", "independent_measurement"),
    "eng-codex-009-nina": ("research.creators.v1", "official_statement"),
}
_CREATIVE_APPROVAL_REF = (
    "https://github.com/Saaimingo/Revista_Gamer/pull/27#issuecomment-6390829648"
)


class TrialError(RuntimeError):
    """A trial cannot proceed without risking a false or repeated inference."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _write_idempotent(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise TrialError(f"Existing private artifact differs: {path.name}")
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


def _replace_json(path: Path, value: Mapping[str, Any]) -> None:
    payload = _json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _git_show(commit: str, source_path: str, *, repo_root: Path) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{source_path}"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise TrialError(f"Pinned persona source is unavailable: {source_path}")
    return completed.stdout


def _research_route(package: Mapping[str, Any]) -> dict[str, str]:
    package_id = str(package["package_id"])
    profile_id, evidence_kind = _RESEARCH_PROFILES[package_id]
    question = (
        f"Quais registros com evidência do tipo {evidence_kind} sobre {package['topic']} "
        "já existem no índice local do Radar, com identificadores e versões conferíveis?"
    )
    purpose = (
        "Preencher uma lacuna do relatório usando exclusivamente read:radar_index; "
        "se não houver registro local correspondente, retornar not_found e manter a lacuna."
    )
    return {
        "question": question,
        "purpose": purpose,
        "profile_id": profile_id,
        "profile_version": "1.0.0",
        "evidence_kind": evidence_kind,
    }


def _trial_id(package_id: str) -> str:
    date_stamp = datetime.now().strftime("%Y%m%d")
    short_name = package_id.removeprefix("eng-codex-009-")
    return f"eng-codex-009-a-{short_name}-{date_stamp}"


def _load_checkpoint(private_root: Path) -> dict[str, Any]:
    path = private_root / "checkpoint.json"
    if not path.is_file():
        return {
            "schema_version": "EngCodex009PrivateCheckpoint.v1",
            "mission": "ENG-CODEX-009",
            "updated_at": _utc_now(),
            "phase": "prepared",
            "franchise_observation": {
                "percent": 88,
                "source": "user_reported_in_conversation",
                "observed_at": None,
                "token_or_quota_conversion": False,
            },
            "after_observation": "not_available",
            "api_paid": False,
            "published": False,
            "journalists": {},
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TrialError(f"Private checkpoint cannot be read ({type(error).__name__})") from None


def _save_checkpoint(private_root: Path, checkpoint: dict[str, Any]) -> None:
    checkpoint["updated_at"] = _utc_now()
    _replace_json(private_root / "checkpoint.json", checkpoint)


def _persona_snapshot(spec: Any, *, private_root: Path, repo_root: Path) -> dict[str, Any]:
    source_records: list[tuple[str, bytes, str]] = []
    for source_path in spec.persona_documents:
        raw = _git_show(spec.persona_source_commit, source_path, repo_root=repo_root)
        source_records.append((source_path, raw, raw.decode("utf-8")))
    instruction_parts: list[str] = [
        "BEGIN APPROVED PERSONA DNA DOCUMENTS. Each source document is reproduced verbatim below."
    ]
    for index, (source_path, _raw, text) in enumerate(source_records, start=1):
        instruction_parts.append(
            f"VERBATIM APPROVED PERSONA DOCUMENT {index}: {source_path}\n\n{text}"
        )
    instruction_parts.append("END APPROVED PERSONA DNA DOCUMENTS")
    instructions = "\n\n".join(instruction_parts)
    instruction_bytes = instructions.encode("utf-8")
    instruction_sha256 = _sha256(instruction_bytes)
    folder = private_root / "persona-dna" / spec.persona_id / instruction_sha256[:16]
    components: list[dict[str, Any]] = []
    for index, (source_path, raw, text) in enumerate(source_records, start=1):
        target = folder / f"{index:02d}-{Path(source_path).name}"
        _write_idempotent(target, raw)
        components.append({
            "source_path": source_path,
            "source_commit": spec.persona_source_commit,
            "source_ref": spec.persona_source_ref,
            "private_copy_ref": target.relative_to(private_root).as_posix(),
            "sha256": _sha256(raw),
            "bytes": len(raw),
            "characters": len(text),
        })
    instruction_path = folder / "persona-instructions.verbatim-composite.md"
    _write_idempotent(instruction_path, instruction_bytes)
    manifest = {
        "schema_version": "ApprovedPersonaSnapshot.v1",
        "approval_reference": _CREATIVE_APPROVAL_REF,
        "approval_status": "creative_approval_recorded; operational_test_pending",
        "persona_id": spec.persona_id,
        "persona_version": spec.persona_version,
        "source_ref": spec.persona_source_ref,
        "source_commit": spec.persona_source_commit,
        "documents": components,
        "instruction_ref": instruction_path.relative_to(private_root).as_posix(),
        "instruction_sha256": instruction_sha256,
        "instruction_bytes": len(instruction_bytes),
        "instruction_characters": len(instructions),
        "original_documents_unchanged": True,
        "approved_sample_texts_included": False,
    }
    manifest_path = folder / "manifest.json"
    _write_idempotent(manifest_path, _json_bytes(manifest))
    return {
        **manifest,
        "manifest_ref": manifest_path.relative_to(private_root).as_posix(),
        "instructions": instructions,
    }


def prepare_battery(
    *,
    private_root: Path = PRIVATE_ROOT,
    repo_root: Path = REPOSITORY_ROOT,
    franchise_percent_reported: int | None = None,
) -> list[dict[str, Any]]:
    """Build checked manifests and exact persona snapshots without SIWC calls."""
    if franchise_percent_reported is not None and not 0 <= franchise_percent_reported <= 100:
        raise TrialError("Reported franchise percent must be between 0 and 100.")
    private_root = Path(private_root).expanduser().resolve()
    private_root.mkdir(parents=True, exist_ok=True)
    write_package_manifests(target=PACKAGE_ROOT)
    prepared: list[dict[str, Any]] = []
    checkpoint = _load_checkpoint(private_root)
    if franchise_percent_reported is not None:
        checkpoint["franchise_observation"] = {
            "percent": franchise_percent_reported,
            "source": "user_reported_in_conversation",
            "observed_at": _utc_now(),
            "token_or_quota_conversion": False,
        }
        checkpoint["after_observation"] = "not_available"
    for spec in DOSSIERS:
        package = load_package(spec.package_id)
        persona = _persona_snapshot(spec, private_root=private_root, repo_root=repo_root)
        route = _research_route(package)
        trial = build_curated_trial_input(
            package, test_id=_trial_id(spec.package_id), local_research_route=route,
        )
        trial["editorial_brief"]["persona_id"] = spec.persona_id
        trial["editorial_brief"]["persona_version"] = spec.persona_version
        trial["editorial_brief"]["corpus_status"] = "project_curated_notes_only"
        trial["editorial_brief"]["source_body_accessed"] = False
        input_bytes = _json_bytes(trial)
        input_path = private_root / "trial-inputs" / f"{trial['editorial_brief']['test_id']}.json"
        _write_idempotent(input_path, input_bytes)
        entry = {
            "package_id": spec.package_id,
            "journalist": spec.journalist,
            "persona_id": spec.persona_id,
            "persona_version": spec.persona_version,
            "persona_hash": persona["instruction_sha256"],
            "persona_manifest_ref": persona["manifest_ref"],
            "persona_component_count": len(persona["documents"]),
            "persona_instruction_characters": persona["instruction_characters"],
            "persona_source_commit": spec.persona_source_commit,
            "dossier_sha256": package["dossier_sha256"],
            "package_sha256": package["package_sha256"],
            "input_ref": input_path.relative_to(private_root).as_posix(),
            "input_sha256": _sha256(input_bytes),
            "input_bytes": len(input_bytes),
            "source_count": len(package["source_candidates"]),
            "curated_note_count": sum(
                item["source_body_status"] == "not_obtained" and bool(item["curator_note"])
                for item in package["source_candidates"]
            ),
            "curator_note_candidate_count": sum(bool(item["curator_note"]) for item in package["source_candidates"]),
            "source_bodies_obtained": False,
            "rights_revalidated": False,
            "ready_for_article_generation": False,
        }
        prepared.append(entry)
        initial_entry = {
            "status": "prepared_not_started",
            **{key: value for key, value in entry.items() if key != "journalist"},
            "journalist": spec.journalist,
        }
        existing_entry = checkpoint.setdefault("journalists", {}).get(spec.persona_id)
        if existing_entry is None or existing_entry.get("status") == "prepared_not_started":
            checkpoint["journalists"][spec.persona_id] = initial_entry
    checkpoint["phase"] = "prepared"
    checkpoint["corpus_status"] = "curator_notes_only; independent_source_verification_pending"
    checkpoint["research_scope"] = ["read:radar_index"]
    checkpoint["external_retrieval_authorized"] = False
    checkpoint["h04_real_tests_repeated"] = 0
    _save_checkpoint(private_root, checkpoint)
    return prepared


def _private_file(root: Path, ref: str) -> Path:
    path = (root / Path(ref)).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise TrialError("Private artifact reference is missing or outside its root.")
    return path


def _read_story_evidence(private_root: Path, response_metadata: Mapping[str, Any]) -> dict[str, Any]:
    archive = response_metadata.get("story_archive")
    if not isinstance(archive, Mapping) or not isinstance(archive.get("manifest_ref"), str):
        raise TrialError("StoryVersionArchive manifest is missing.")
    manifest_path = _private_file(private_root, archive["manifest_ref"])
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    raw_path = _private_file(private_root, manifest["raw_response_ref"])
    text_path = _private_file(private_root, manifest["full_text_ref"])
    raw_bytes = raw_path.read_bytes()
    text_bytes = text_path.read_bytes()
    if _sha256(raw_bytes) != manifest["raw_response_sha256"]:
        raise TrialError("Archived raw response hash mismatch.")
    if _sha256(text_bytes) != manifest["full_text_sha256"]:
        raise TrialError("Archived full-text hash mismatch.")
    text = text_bytes.decode("utf-8")
    return {
        "version_kind": manifest["version_kind"],
        "story_revision_id": manifest["story_revision_id"],
        "manifest_ref": archive["manifest_ref"],
        "manifest_sha256": _sha256(manifest_bytes),
        "raw_response_ref": manifest["raw_response_ref"],
        "raw_response_sha256": manifest["raw_response_sha256"],
        "raw_response_bytes": len(raw_bytes),
        "full_text_ref": manifest["full_text_ref"],
        "full_text_sha256": manifest["full_text_sha256"],
        "full_text_bytes": len(text_bytes),
        "word_count": len(_WORD_RE.findall(text)),
        "published": manifest.get("published") is True,
    }


def _usage_receipt(private_root: Path, response_metadata: Mapping[str, Any]) -> dict[str, Any] | None:
    usage_ref = response_metadata.get("usage_record_ref")
    if not isinstance(usage_ref, Mapping) or not isinstance(usage_ref.get("ref"), str):
        return None
    path = _private_file(private_root, usage_ref["ref"])
    raw = path.read_bytes()
    if _sha256(raw) != usage_ref.get("sha256"):
        raise TrialError("Usage receipt hash mismatch.")
    return json.loads(raw.decode("utf-8"))


def _final_schema_status(
    response_metadata: Mapping[str, Any],
    usage_receipt: Mapping[str, Any] | None,
) -> str | None:
    final_status = response_metadata.get("output_validation")
    if isinstance(final_status, str) and final_status:
        return final_status
    captured_status = usage_receipt.get("schema_status") if usage_receipt is not None else None
    return captured_status if isinstance(captured_status, str) and captured_status else None


def _factory_bridge(
    *,
    queue: AgentQueue,
    dispatcher: TaskDispatcher,
    task_id: str,
    private_root: Path,
    package: Mapping[str, Any],
) -> dict[str, Any]:
    from .factory import run_factory_persona_draft_bridge

    trial = build_curated_trial_input(package, test_id="factory-bridge-reference")
    evidence_rows = [
        {"evidence_id": item["evidence_id"], "source_id": item["source_id"]}
        for item in trial["evidence_dossier"]["evidence"]
    ]
    valid_source_ids = sorted({item["source_id"] for item in trial["evidence_dossier"]["evidence"]})
    result = run_factory_persona_draft_bridge(
        queue=queue,
        dispatcher=dispatcher,
        role_task_id=task_id,
        artifact_root=private_root,
        evidence_rows=evidence_rows,
        valid_source_ids=valid_source_ids,
    )
    return {
        "status": result["status"],
        "factory_task_id": result["factory_task_id"],
        "article_draft_ref": result["article_draft_ref"],
        "article_draft_sha256": result["article_draft_sha256"],
        "human_review_required": result["human_review_required"],
        "fact_check_status": result["fact_check_status"],
        "editorial_review_status": result["editorial_review_status"],
        "published": result["published"],
    }


def run_one(
    package_id: str,
    *,
    private_root: Path = PRIVATE_ROOT,
    repo_root: Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    """Run at most one real SIWC inference for one journalist; never replay an attempt."""
    prepared = prepare_battery(private_root=private_root, repo_root=repo_root)
    entry = next((row for row in prepared if row["package_id"] == package_id), None)
    spec = next((row for row in DOSSIERS if row.package_id == package_id), None)
    if entry is None or spec is None:
        raise TrialError("Unknown ENG-CODEX-009 package id.")
    private_root = Path(private_root).expanduser().resolve()
    checkpoint = _load_checkpoint(private_root)
    journal = checkpoint["journalists"].get(spec.persona_id, {})
    if journal.get("status") in {"completed", "succeeded_needs_research", "blocked", "failed", "uncertain"}:
        return {"status": journal["status"], "task_id": journal.get("task_id"), "reused": True}

    catalog = load_builtin_role_catalog()
    row = next(item for item in catalog.to_mapping()["profiles"] if item["role_id"] == ROLE_ID)
    role = catalog.resolve(ROLE_ID, row["role_version"], row["profile_sha256"])
    trial_path = _private_file(private_root, entry["input_ref"])
    trial_bytes = trial_path.read_bytes()
    if _sha256(trial_bytes) != entry["input_sha256"]:
        raise TrialError("Prepared trial input hash diverged from the checkpoint.")
    trial = json.loads(trial_bytes.decode("utf-8"))
    story_id = f"eng-codex-009/{spec.persona_id}/{trial['editorial_brief']['test_id']}"
    task_id = str(uuid.uuid5(_NAMESPACE, trial["editorial_brief"]["test_id"]))
    idempotency_key = f"eng-codex-009:{trial['editorial_brief']['test_id']}:original"
    store = Store(private_root / "motor.sqlite3", private_root / "queue-artifacts")
    queue = AgentQueue(store)
    existing = queue.get(task_id)

    if existing is not None and (existing.state != "queued" or existing.attempts > 0):
        journal.update({"status": existing.state, "task_id": task_id, "reused": True})
        checkpoint["journalists"][spec.persona_id] = journal
        _save_checkpoint(private_root, checkpoint)
        return {"status": existing.state, "task_id": task_id, "reused": True}

    client = SIWCClient(CredentialStore())
    try:
        listed = client.models()
        visible = {
            str(item["slug"]) for item in listed
            if item.get("visibility") == "list" and isinstance(item.get("slug"), str)
        }
    except SIWCError as error:
        journal.update({
            "status": "blocked", "task_id": task_id,
            "blocker_code": error.code, "provider_call_started": False,
        })
        checkpoint["journalists"][spec.persona_id] = journal
        _save_checkpoint(private_root, checkpoint)
        return {"status": "blocked", "blocker_code": error.code, "task_id": task_id}
    if MODEL not in visible:
        journal.update({
            "status": "blocked", "task_id": task_id,
            "blocker_code": "siwc_model_not_visible", "provider_call_started": False,
        })
        checkpoint["journalists"][spec.persona_id] = journal
        _save_checkpoint(private_root, checkpoint)
        return {"status": "blocked", "blocker_code": "siwc_model_not_visible", "task_id": task_id}

    persona = _persona_snapshot(spec, private_root=private_root, repo_root=repo_root)
    input_payload_hash = stable_hash(json_dumps(trial))
    now = datetime.now(timezone.utc)
    route = _research_route(load_package(package_id))
    route_payload = {
        "route_id": f"local-radar-{spec.persona_id}",
        "question": route["question"],
        "purpose": route["purpose"],
        "research_profile_id": route["profile_id"],
        "research_profile_version": route["profile_version"],
        "required_evidence_kinds": [route["evidence_kind"]],
        "reason": "Mission 009 permits only an existing local Radar index read; source bodies remain unverified.",
        "languages": ["pt-BR"],
    }
    policy = {
        "schema_version": "ResearchMediationPolicy.v1",
        "story_revision_id": f"original-{trial['editorial_brief']['test_id']}",
        "routes": [route_payload],
    }
    envelope = AgentTaskEnvelope.from_mapping({
        "schema_version": "1.1",
        "task_id": task_id,
        "run_id": f"eng-codex-009-A-{datetime.now().strftime('%Y%m%d')}",
        "story_id": story_id,
        "edition_id": None,
        "role_id": ROLE_ID,
        "role_version": role.role_version,
        "role_hash": role.content_hash,
        "input_payload_hash": input_payload_hash,
        "persona_id": spec.persona_id,
        "persona_version": spec.persona_version,
        "persona_hash": persona["instruction_sha256"],
        "input_artifact_refs": [{
            "ref": f"private://ensaios-009/{entry['input_ref']}",
            "sha256": entry["input_sha256"],
        }],
        "source_snapshot_ids": [
            f"dossier:{package_id}:{entry['dossier_sha256']}",
            f"persona:{spec.persona_id}:{persona['instruction_sha256']}",
        ],
        "authorized_tools": [],
        "deadline": (now + timedelta(minutes=20)).isoformat(timespec="seconds"),
        "context_schema_version": "1.0",
        "usage_guardrails": {"max_calls": 1, "max_iterations": 1},
        "idempotency_key": idempotency_key,
        "correlation_id": f"{story_id}:{task_id}",
        "requires_human_gate": True,
        "research_mediation_policy": policy,
    })
    if existing is None:
        enqueue_contract_task(
            queue,
            envelope,
            trial,
            catalog=catalog,
            executor_profile=SIWC_ROLE_EXECUTOR_PROFILE,
            executor_id=SIWC_ROLE_EXECUTOR_ID,
            max_attempts=1,
        )

    checkpoint["phase"] = f"running_{spec.persona_id}"
    journal.update({
        "status": "in_progress",
        "task_id": task_id,
        "idempotency_key": idempotency_key,
        "input_sha256": entry["input_sha256"],
        "persona_hash": persona["instruction_sha256"],
        "provider_call_started": False,
        "quota_observation_after": "not_available",
    })
    checkpoint["journalists"][spec.persona_id] = journal
    _save_checkpoint(private_root, checkpoint)

    dispatcher = TaskDispatcher(
        queue,
        executors={},
        profiles={},
        role_catalog=catalog,
        persona_instruction_resolver=lambda task_envelope: (
            persona["instructions"] if task_envelope.persona_id == spec.persona_id else None
        ),
    )
    register_siwc_role_executor(
        dispatcher,
        client,
        artifact_root=private_root,
        model=MODEL,
        reasoning_effort=REASONING_EFFORT,
        catalog_models=visible,
    )
    outcome = dispatcher.dispatch_one(task_id)
    task = queue.get(task_id)
    if task is None:
        raise TrialError("Dispatched journalist task disappeared from the shared queue.")

    response_metadata_path = private_root / "siwc-role-responses" / f"{task_id}.metadata.json"
    response_metadata: dict[str, Any] = {}
    if response_metadata_path.is_file():
        response_metadata = json.loads(response_metadata_path.read_text(encoding="utf-8"))
    usage = _usage_receipt(private_root, response_metadata)
    story = _read_story_evidence(private_root, response_metadata) if response_metadata.get("story_archive") else None
    bridge: dict[str, Any]
    if task.state == "succeeded" and task.result and task.result.get("status") == "completed":
        try:
            bridge = _factory_bridge(
                queue=queue,
                dispatcher=dispatcher,
                task_id=task_id,
                private_root=private_root,
                package=load_package(package_id),
            )
        except TaskFailure as error:
            bridge = {"status": "blocked", "blocker_code": error.code, "published": False}
    elif task.state == "succeeded":
        bridge = {"status": "held_pending_research_or_review", "published": False}
    else:
        bridge = {"status": "not_run_task_not_succeeded", "published": False}

    final_status = (
        "completed" if task.state == "succeeded" and task.result and task.result.get("status") == "completed"
        else "succeeded_needs_research" if task.state == "succeeded"
        else task.state
    )
    safe_record = {
        "status": final_status,
        "task_state": task.state,
        "task_id": task_id,
        "journalist": spec.journalist,
        "persona_id": spec.persona_id,
        "persona_version": spec.persona_version,
        "persona_hash": persona["instruction_sha256"],
        "role_id": ROLE_ID,
        "model_requested": MODEL,
        "model_used": task.result.get("model_used") if task.result else None,
        "reasoning_effort_requested": REASONING_EFFORT,
        "reasoning_effort_used": task.result.get("model_effort") if task.result else None,
        "provider_outcome": usage.get("provider_call_status") if usage else (
            "uncertain" if task.state == "uncertain" else "not_available"
        ),
        "provider_call_count": usage.get("request_count") if usage else None,
        "input_tokens": usage.get("input_tokens") if usage else None,
        "output_tokens": usage.get("output_tokens") if usage else None,
        "reasoning_tokens": usage.get("reasoning_tokens") if usage else None,
        "total_tokens": usage.get("total_tokens") if usage else None,
        "cached_input_tokens": usage.get("cached_input_tokens") if usage else None,
        "latency_ms": usage.get("latency_ms") if usage else None,
        "context_bytes": usage.get("context_bytes") if usage else None,
        "schema_status": _final_schema_status(response_metadata, usage),
        "schema_status_at_usage_receipt": usage.get("schema_status") if usage else None,
        "usage_record_ref": response_metadata.get("usage_record_ref"),
        "article": story,
        "factory_adapter": bridge,
        "research_scope": ["read:radar_index"],
        "source_bodies_obtained": False,
        "rights_revalidated": False,
        "independent_fact_verification": False,
        "actual_billed_api_cost": None,
        "franchise_percent": None,
        "franchise_percent_status": "manual_after_observation_not_available; not inferred from tokens",
        "published": False,
        "api_paid": False,
        "dispatch_outcome": outcome.state,
        "dispatch_error_code": outcome.error_code,
    }
    _write_idempotent(
        private_root / "journalist-results" / f"{trial['editorial_brief']['test_id']}.json",
        _json_bytes(safe_record),
    )
    journal.update({
        "status": final_status,
        "task_state": task.state,
        "task_id": task_id,
        "provider_outcome": safe_record["provider_outcome"],
        "total_tokens": safe_record["total_tokens"],
        "latency_ms": safe_record["latency_ms"],
        "story_manifest_ref": story["manifest_ref"] if story else None,
        "story_full_text_sha256": story["full_text_sha256"] if story else None,
        "story_word_count": story["word_count"] if story else None,
        "factory_adapter_status": bridge["status"],
        "provider_call_started": bool(usage or response_metadata),
        "quota_observation_after": "not_available",
    })
    checkpoint["journalists"][spec.persona_id] = journal
    checkpoint["phase"] = "all_reports_attempted" if all(
        checkpoint["journalists"].get(item.persona_id, {}).get("status") in {
            "completed", "succeeded_needs_research", "blocked", "failed", "uncertain",
        }
        for item in DOSSIERS
    ) else "in_progress"
    _save_checkpoint(private_root, checkpoint)
    return safe_record


def _public_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    article = record.get("article") if isinstance(record.get("article"), Mapping) else {}
    return {
        key: record.get(key) for key in (
            "status", "task_state", "task_id", "journalist", "persona_id", "persona_version",
            "model_requested", "model_used", "reasoning_effort_used", "provider_outcome",
            "provider_call_count", "input_tokens", "output_tokens", "reasoning_tokens", "total_tokens",
            "latency_ms", "schema_status", "published", "dispatch_error_code",
        )
    } | {
        "word_count": article.get("word_count"),
        "full_text_sha256": article.get("full_text_sha256"),
        "factory_adapter_status": (record.get("factory_adapter") or {}).get("status"),
        "full_text_stored_privately": bool(article.get("full_text_ref")),
        "quota_after_observation": "not_available",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ENG-CODEX-009 private journalist trials")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare", help="Build dossiers and persona snapshots offline")
    prepare_parser.add_argument("--franchise-percent-reported", type=int)
    run_parser = commands.add_parser("run", help="Run one journalist once")
    run_parser.add_argument("package_id", choices=[item.package_id for item in DOSSIERS])
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_battery(franchise_percent_reported=args.franchise_percent_reported)
            print(json.dumps({"status": "prepared", "journalists": [
                {key: row[key] for key in ("journalist", "persona_id", "persona_version", "persona_hash", "source_count", "curated_note_count")}
                for row in result
            ], "private_root": str(PRIVATE_ROOT)}, ensure_ascii=False, indent=2))
            return 0
        record = run_one(args.package_id)
        print(json.dumps(_public_summary(record), ensure_ascii=False, indent=2))
        return 0 if record.get("task_state") == "succeeded" else 1
    except (TrialError, SIWCError) as error:
        print(json.dumps({"status": "blocked", "error_type": type(error).__name__, "error_code": getattr(error, "code", None)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
