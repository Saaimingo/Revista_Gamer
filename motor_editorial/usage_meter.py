"""Private SIWC usage receipts and immutable full-text story version storage."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent_contracts import AgentTaskEnvelope
from .db import json_dumps
from .orchestration import AgentTask, _assert_no_credentials


USAGE_RECORD_SCHEMA_VERSION = "AgentUsageRecord.v1"
STORY_VERSION_SCHEMA_VERSION = "StoryVersionArtifact.v1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _safe_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{field} inválido para armazenamento privado.")
    return value


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        return None
    return value


def _token(usage: Mapping[str, Any] | None, primary: str, *alternates: str) -> int | None:
    if not isinstance(usage, Mapping):
        return None
    for key in (primary, *alternates):
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    return None


def build_usage_record(
    *,
    task: AgentTask,
    envelope: AgentTaskEnvelope,
    metadata: Mapping[str, Any],
    raw_response: bytes,
    research_request_count: int | None,
    schema_status: str,
    story_revision_id: str | None = None,
) -> dict[str, Any]:
    """Normalize provider usage without deriving cost or subscription quota."""
    usage = metadata.get("usage") if isinstance(metadata.get("usage"), Mapping) else None
    input_details = usage.get("input_tokens_details") if isinstance(usage, Mapping) else None
    output_details = usage.get("output_tokens_details") if isinstance(usage, Mapping) else None
    reasoning_tokens = _token(usage, "reasoning_tokens")
    if reasoning_tokens is None and isinstance(output_details, Mapping):
        reasoning_tokens = _token(output_details, "reasoning_tokens")
    cached_input_tokens = _token(usage, "cached_input_tokens", "cached_tokens")
    if cached_input_tokens is None and isinstance(input_details, Mapping):
        cached_input_tokens = _token(input_details, "cached_tokens")
    model = metadata.get("model") if isinstance(metadata.get("model"), str) else None
    effort = metadata.get("reasoning_effort") if isinstance(metadata.get("reasoning_effort"), str) else None
    duration_ms = _number(metadata.get("duration_ms"))
    response_completed = metadata.get("response_completed") is True
    external_call_count = _token(metadata, "external_call_count")
    input_payload = task.payload.get("input") if isinstance(task.payload.get("input"), Mapping) else {}
    brief = input_payload.get("editorial_brief") if isinstance(input_payload.get("editorial_brief"), Mapping) else {}
    dossier = input_payload.get("evidence_dossier") if isinstance(input_payload.get("evidence_dossier"), Mapping) else {}
    outcome = metadata.get("provider_call_outcome")
    if outcome not in {"success", "failed", "uncertain"}:
        outcome = "success" if response_completed else "failed"
    return {
        "schema_version": USAGE_RECORD_SCHEMA_VERSION,
        "recorded_at": metadata.get("completed_at") if isinstance(metadata.get("completed_at"), str)
            else datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "test_id": metadata.get("test_id") or brief.get("test_id") or brief.get("case_id"),
        "task_id": task.task_id,
        "attempt_number": task.attempts,
        "retry_count": max(0, task.attempts - 1),
        "run_id": envelope.run_id,
        "story_id": envelope.story_id,
        "dossier_version": dossier.get("dossier_version"),
        "dossier_sha256": dossier.get("dossier_sha256"),
        "context_bytes": _number(metadata.get("context_bytes")),
        "story_revision_id": story_revision_id or (
            envelope.research_mediation_policy.get("story_revision_id")
            if envelope.research_mediation_policy else None
        ),
        "role_id": envelope.role_id,
        "role_version": envelope.role_version,
        "role_hash": envelope.role_hash,
        "persona_id": envelope.persona_id,
        "persona_version": envelope.persona_version,
        "persona_hash": envelope.persona_hash,
        "model_requested": metadata.get("model_requested") if isinstance(metadata.get("model_requested"), str) else None,
        "model": model,
        "reasoning_effort_requested": metadata.get("reasoning_effort_requested") if isinstance(metadata.get("reasoning_effort_requested"), str) else None,
        "reasoning_effort": effort,
        "provider_call_outcome": outcome,
        "provider_call_status": "completed" if response_completed else "incomplete_or_unreported",
        "provider_response_id": metadata.get("response_id") if isinstance(metadata.get("response_id"), str) else None,
        "schema_status": schema_status,
        "input_tokens": _token(usage, "input_tokens", "prompt_tokens"),
        "output_tokens": _token(usage, "output_tokens", "completion_tokens"),
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": _token(usage, "total_tokens"),
        "cached_input_tokens": cached_input_tokens,
        "latency_ms": duration_ms,
        "request_count": external_call_count,
        "siwc_network_requests": external_call_count,
        "research_request_count": research_request_count,
        "research_suggestion_count": metadata.get("research_suggestion_count") if isinstance(metadata.get("research_suggestion_count"), int) and not isinstance(metadata.get("research_suggestion_count"), bool) else None,
        "research_index_hits": None,
        "research_cache_hits": None,
        "research_network_requests": None,
        "raw_response_sha256": _sha256(raw_response),
        "raw_response_bytes": len(raw_response),
        "calls_success": 1 if outcome == "success" else 0,
        "calls_failed": 1 if outcome == "failed" else 0,
        "calls_uncertain": 1 if outcome == "uncertain" else 0,
        "blocked_reason": metadata.get("blocked_reason") if isinstance(metadata.get("blocked_reason"), str) else None,
        "actual_billed_api_cost": None,
        "actual_billed_api_cost_status": "not_available_without_billing_receipt",
        "franchise_percent": None,
        "franchise_percent_status": "manual_observation_not_attached_to_token_usage",
        "published": False,
    }


class AgentUsageArtifactStore:
    """Persist one usage receipt per role-task attempt under a private root."""

    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self.directory = (self.root / "agent-usage").resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        if not self.directory.is_relative_to(self.root):
            raise ValueError("Diretório de uso precisa permanecer sob a raiz configurada.")

    def write(self, record: Mapping[str, Any]) -> dict[str, str]:
        task_id = _safe_id(str(record.get("task_id", "")), "task_id")
        attempt = record.get("attempt_number")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            raise ValueError("attempt_number precisa ser inteiro positivo.")
        payload = json_dumps(dict(record)).encode("utf-8")
        _assert_no_credentials(payload.decode("utf-8"), "agent_usage_record")
        path = self.directory / f"{task_id}.attempt-{attempt:03d}.json"
        if path.exists():
            existing = path.read_bytes()
            if existing != payload:
                raise ValueError("Registro de uso existente diverge do mesmo task/attempt; sobrescrita bloqueada.")
        else:
            self._write_new(path, payload)
        return {"ref": path.relative_to(self.root).as_posix(), "sha256": _sha256(payload)}

    def read(self, ref: str, expected_sha256: str) -> dict[str, Any]:
        candidate = (self.root / Path(ref)).resolve()
        if not candidate.is_relative_to(self.directory) or not candidate.is_file():
            raise ValueError("ReferÃªncia de recibo de uso fora do diretÃ³rio local permitido.")
        payload = candidate.read_bytes()
        if _sha256(payload) != expected_sha256:
            raise ValueError("Hash do recibo de uso nÃ£o confere com a referÃªncia persistida.")
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Recibo de uso precisa conter um objeto JSON.")
        return value

    def read_for_attempt(self, task_id: str, attempt: int) -> tuple[dict[str, Any], dict[str, str]] | None:
        task_id = _safe_id(task_id, "task_id")
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
            raise ValueError("attempt precisa ser inteiro positivo.")
        path = self.directory / f"{task_id}.attempt-{attempt:03d}.json"
        if not path.is_file():
            return None
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Recibo de uso precisa conter um objeto JSON.")
        if value.get("task_id") != task_id or value.get("attempt_number") != attempt:
            raise ValueError("Recibo de uso não corresponde à tentativa solicitada.")
        return value, {
            "ref": path.relative_to(self.root).as_posix(),
            "sha256": _sha256(payload),
        }

    @staticmethod
    def _write_new(path: Path, payload: bytes) -> None:
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("xb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.rename(temp, path)
        except FileExistsError:
            raise ValueError("Registro de uso já existe; sobrescrita bloqueada.") from None
        finally:
            temp.unlink(missing_ok=True)


class StoryVersionArchive:
    """Store raw provider output and a readable full-story render by version."""

    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self.directory = (self.root / "story-versions").resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        if not self.directory.is_relative_to(self.root):
            raise ValueError("Arquivo de versões precisa permanecer sob a raiz configurada.")

    @staticmethod
    def _render(story: Mapping[str, Any]) -> str:
        title, dek, sections = story.get("title"), story.get("dek"), story.get("sections")
        if not isinstance(title, str) or not title.strip() or not isinstance(dek, str) or not isinstance(sections, list) or not sections:
            raise ValueError("StoryDraft sem título, linha fina ou seções completas.")
        rendered = [f"# {title.strip()}", "", dek.strip()]
        for index, section in enumerate(sections, start=1):
            if not isinstance(section, Mapping):
                raise ValueError(f"Seção {index} do StoryDraft inválida.")
            heading, body = section.get("heading"), section.get("body")
            if not isinstance(heading, str) or not heading.strip() or not isinstance(body, str) or not body.strip():
                raise ValueError(f"Seção {index} do StoryDraft está incompleta.")
            rendered.extend(["", f"## {heading.strip()}", "", body.rstrip()])
        return "\n".join(rendered) + "\n"

    def write(
        self,
        *,
        task: AgentTask,
        envelope: AgentTaskEnvelope,
        raw_response: bytes,
        structured_story: Mapping[str, Any],
        response_ref: Mapping[str, str],
        usage_ref: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        if envelope.role_id != "persona_writer":
            raise ValueError("Somente saída de persona_writer pode entrar no arquivo de matérias.")
        if _sha256(raw_response) != response_ref.get("sha256"):
            raise ValueError("Hash da resposta bruta diverge do artefato original SIWC.")
        story_id = envelope.story_id
        if (
            not isinstance(story_id, str)
            or not story_id.strip()
            or len(story_id) > 512
            or any(ord(character) < 32 for character in story_id)
        ):
            raise ValueError("story_id invÃ¡lido para armazenamento privado.")
        task_id = _safe_id(task.task_id, "task_id")
        if usage_ref is not None:
            if not isinstance(usage_ref, Mapping) or not isinstance(usage_ref.get("ref"), str) or not isinstance(usage_ref.get("sha256"), str):
                raise ValueError("Referência de recibo de uso inválida.")
            receipt = AgentUsageArtifactStore(self.root).read(usage_ref["ref"], usage_ref["sha256"])
            if (receipt.get("task_id") != task_id or receipt.get("attempt_number") != task.attempts
                    or receipt.get("raw_response_sha256") != _sha256(raw_response)):
                raise ValueError("Recibo de uso não corresponde à tarefa, tentativa e resposta arquivadas.")
        story_key = _sha256(story_id.encode("utf-8"))[:32]
        story_dir = (self.directory / story_key).resolve()
        if not story_dir.is_relative_to(self.directory):
            raise ValueError("story_id fora do diretório permitido.")
        markdown = self._render(structured_story).encode("utf-8")
        existing_manifest = next(story_dir.glob(f"**/{task_id}/manifest.json"), None)
        if existing_manifest is not None:
            current = json.loads(existing_manifest.read_text(encoding="utf-8"))
            if (current.get("task_id") != task_id or current.get("story_id") != story_id
                    or current.get("persona_id") != envelope.persona_id
                    or current.get("persona_version") != envelope.persona_version
                    or current.get("persona_hash") != envelope.persona_hash
                    or current.get("attempt_number") != task.attempts
                    or current.get("response_ref") != dict(response_ref)
                    or current.get("usage_record_ref") != (dict(usage_ref) if usage_ref else None)
                    or current.get("raw_response_sha256") != _sha256(raw_response)
                    or current.get("full_text_sha256") != _sha256(markdown)):
                raise ValueError("Tarefa já arquivada com outro conteúdo; sobrescrita bloqueada.")
            for field, name, payload in (
                ("raw_response_ref", "response.raw.json", raw_response),
                ("full_text_ref", "story.full.md", markdown),
            ):
                expected_path = (existing_manifest.parent / name).resolve()
                ref = current.get(field)
                if not isinstance(ref, str) or (self.root / ref).resolve() != expected_path or not expected_path.is_relative_to(story_dir):
                    raise ValueError("Referência de versão arquivada fora do diretório esperado.")
                self._write_idempotent(expected_path, payload)
            return {
                "version_kind": current["version_kind"],
                "revision_id": current["story_revision_id"],
                "manifest_ref": existing_manifest.relative_to(self.root).as_posix(),
                "raw_response_ref": current["raw_response_ref"],
                "full_text_ref": current["full_text_ref"],
                "manifest_sha256": _sha256(existing_manifest.read_bytes()),
                "full_text_sha256": current["full_text_sha256"],
            }
        original_exists = any(story_dir.glob("original/**/manifest.json"))
        kind = "revision" if original_exists else "original"
        revision_id = (
            envelope.research_mediation_policy.get("story_revision_id")
            if envelope.research_mediation_policy else None
        ) or f"revision-{task_id}"
        revision_key = _sha256(str(revision_id).encode("utf-8"))[:20]
        version_dir = story_dir / kind / (revision_key if kind == "revision" else "initial") / task_id
        version_dir.mkdir(parents=True, exist_ok=True)
        raw_path = version_dir / "response.raw.json"
        text_path = version_dir / "story.full.md"
        manifest_path = version_dir / "manifest.json"
        manifest = {
            "schema_version": STORY_VERSION_SCHEMA_VERSION,
            "story_id": story_id,
            "story_revision_id": revision_id,
            "version_kind": kind,
            "task_id": task_id,
            "attempt_number": task.attempts,
            "persona_id": envelope.persona_id,
            "persona_version": envelope.persona_version,
            "persona_hash": envelope.persona_hash,
            "response_ref": dict(response_ref),
            "raw_response_ref": raw_path.relative_to(self.root).as_posix(),
            "raw_response_sha256": _sha256(raw_response),
            "raw_response_bytes": len(raw_response),
            "full_text_ref": text_path.relative_to(self.root).as_posix(),
            "full_text_sha256": _sha256(markdown),
            "full_text_bytes": len(markdown),
            "usage_record_ref": dict(usage_ref) if usage_ref else None,
            "human_evaluation_status": "pending",
            "published": False,
        }
        manifest_bytes = json_dumps(manifest).encode("utf-8")
        self._write_idempotent(raw_path, raw_response)
        self._write_idempotent(text_path, markdown)
        self._write_idempotent(manifest_path, manifest_bytes)
        self._write_index(story_dir, story_id)
        return {
            "version_kind": kind,
            "revision_id": revision_id,
            "manifest_ref": manifest_path.relative_to(self.root).as_posix(),
            "raw_response_ref": raw_path.relative_to(self.root).as_posix(),
            "full_text_ref": text_path.relative_to(self.root).as_posix(),
            "manifest_sha256": _sha256(manifest_bytes),
            "full_text_sha256": _sha256(markdown),
        }

    def _write_index(self, story_dir: Path, story_id: str) -> None:
        entries: list[dict[str, Any]] = []
        for manifest_path in sorted(story_dir.glob("**/manifest.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries.append({
                "version_kind": manifest["version_kind"],
                "story_revision_id": manifest["story_revision_id"],
                "task_id": manifest["task_id"],
                "manifest_ref": manifest_path.relative_to(self.root).as_posix(),
                "full_text_ref": manifest["full_text_ref"],
                "full_text_sha256": manifest["full_text_sha256"],
            })
        payload = json_dumps({"story_id": story_id, "versions": entries, "published": False}).encode("utf-8")
        path = story_dir / "INDEX.json"
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("xb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    @staticmethod
    def _write_idempotent(path: Path, payload: bytes) -> None:
        if path.exists():
            if path.read_bytes() != payload:
                raise ValueError("Versão de matéria existente diverge; sobrescrita bloqueada.")
            return
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("xb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.rename(temp, path)
        finally:
            temp.unlink(missing_ok=True)


def aggregate_usage_by_persona(
    records: Sequence[Mapping[str, Any]],
    *,
    research_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Summarize reported metrics without filling missing values with zero."""
    research_results = research_results or {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in records:
        record = dict(raw)
        persona = record.get("persona_id") or "unassigned"
        research_result = research_results.get(str(record.get("task_id")))
        if research_result:
            record["research_index_hits"] = research_result.get("index_hit_count")
            record["research_cache_hits"] = int(research_result["cache_hit"]) if isinstance(research_result.get("cache_hit"), bool) else None
            record["research_network_requests"] = int(research_result["provider_called"]) if isinstance(research_result.get("provider_called"), bool) else None
        grouped[str(persona)].append(record)

    metrics = ("input_tokens", "output_tokens", "reasoning_tokens", "total_tokens", "latency_ms", "research_index_hits", "research_cache_hits")
    summary: dict[str, Any] = {"schema_version": "AgentUsageSummary.v1", "personas": {}}
    for persona_id, rows in sorted(grouped.items()):
        persona_summary: dict[str, Any] = {
            "call_count": len(rows),
            "provider_call_status_counts": {},
            "role_counts": {},
            "metrics": {},
            "actual_billed_api_cost": None,
            "franchise_percent": None,
        }
        for row in rows:
            status = str(row.get("provider_call_status") or "not_available")
            persona_summary["provider_call_status_counts"][status] = persona_summary["provider_call_status_counts"].get(status, 0) + 1
            role = str(row.get("role_id") or "not_available")
            persona_summary["role_counts"][role] = persona_summary["role_counts"].get(role, 0) + 1
        for metric in metrics:
            values = [value for row in rows if (value := _number(row.get(metric))) is not None]
            persona_summary["metrics"][metric] = {
                "reported_count": len(values),
                "median": statistics.median(values) if values else None,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            }
        summary["personas"][persona_id] = persona_summary
    return summary
