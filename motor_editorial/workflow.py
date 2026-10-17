"""Deterministic, offline editorial demonstration pipeline."""

from __future__ import annotations

import json
import re
import tempfile
import threading
from contextlib import closing
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from .db import Store, canonicalize_identifier, json_dumps, normalize_text, stable_hash, utc_now
from .domain import (
    InvalidApproval,
    InterventionRequired,
    RecoverableStepError,
)
from .render import render_preview


APPROVAL_PHRASE = "APROVAR APENAS INTERNAMENTE"
EXCLUSION_PHRASE = "EXCLUIR PAUTA DA EDICAO"
MAX_ATTEMPTS = 3


def _serialized_operation(method: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(method)
    def wrapped(self: "Motor", *args: Any, **kwargs: Any) -> Any:
        with self._operation_lock:
            return method(self, *args, **kwargs)
    return wrapped


@dataclass(frozen=True)
class SimulationResult:
    run_id: str
    status: str
    message: str
    edition_id: str | None = None


class Motor:
    """Coordinates local steps; adapters are fixed, deterministic demo functions."""

    def __init__(
        self,
        store: Store,
        fixture_path: Path | None = None,
        *,
        research_failures_to_inject: int = 1,
        max_attempts: int = MAX_ATTEMPTS,
        force_v2_review_failure: bool = False,
    ):
        if max_attempts < 1:
            raise ValueError("O limite de tentativas precisa ser pelo menos 1.")
        if research_failures_to_inject < 0:
            raise ValueError("A quantidade de falhas simuladas não pode ser negativa.")
        self.store = store
        self._operation_lock = threading.RLock()
        self.fixture_path = fixture_path or Path(__file__).parent / "fixtures" / "demo.json"
        self.research_failures_to_inject = research_failures_to_inject
        self.max_attempts = max_attempts
        self.force_v2_review_failure = force_v2_review_failure

    def load_fixture(self) -> dict[str, Any]:
        with self.fixture_path.open("r", encoding="utf-8") as fixture_file:
            data = json.load(fixture_file)
        if not data.get("scenario_id") or not data.get("items"):
            raise ValueError("A fixture precisa de um identificador e pelo menos um item.")
        return data

    def run_demo(self) -> SimulationResult:
        data = self.load_fixture()
        self._validate_single_selected_story(data)
        run_id = data["scenario_id"]
        self._ensure_run(run_id, data["scenario_label"])
        existing_run = self.store.get_run(run_id)
        if existing_run and existing_run["status"] == "approved_internally":
            edition = self.store.get_edition_by_run(run_id)
            return SimulationResult(
                run_id, "approved_internally", "A simulação já foi aprovada internamente.",
                edition["id"] if edition else None,
            )
        if existing_run and existing_run["status"] == "awaiting_approval":
            edition = self.store.get_edition_by_run(run_id)
            return SimulationResult(
                run_id,
                "awaiting_approval",
                "A prévia já está pronta e continua aguardando aprovação humana interna.",
                edition["id"] if edition else None,
            )
        if existing_run and existing_run["status"] == "failed_intervention":
            return SimulationResult(
                run_id,
                "failed_intervention",
                "A simulação atingiu o limite de tentativas e exige intervenção humana.",
            )

        self._set_run_status(run_id, "running")
        self._execute_step(
            run_id, None, "ingest", lambda connection, attempt: self._ingest(connection, run_id, data)
        )
        self._execute_step(
            run_id, None, "triage", lambda connection, attempt: self._triage(connection, run_id, data)
        )

        with closing(self.store.connect()) as connection:
            story_ids = [
                row["id"] for row in connection.execute(
                    "SELECT id FROM stories WHERE run_id = ? ORDER BY id", (run_id,)
                ).fetchall()
            ]

        try:
            for story_id in story_ids:
                self._run_story(run_id, story_id, data)
        except RecoverableStepError as error:
            return SimulationResult(
                run_id,
                "recoverable_failure",
                f"A etapa foi interrompida por uma falha transitória simulada: {error} "
                "Execute a mesma simulação novamente para retomar.",
            )
        except InterventionRequired as error:
            return SimulationResult(run_id, "failed_intervention", str(error))

        edition = self.store.get_edition_by_run(run_id)
        if edition:
            if edition["status"] == "approved_internally":
                self._set_run_status(run_id, "approved_internally")
                return SimulationResult(
                    run_id, "approved_internally", "A simulação já foi aprovada internamente.",
                    edition["id"],
                )
            self._set_run_status(run_id, "awaiting_approval")
            return SimulationResult(
                run_id,
                "awaiting_approval",
                "Prévia pronta; a simulação aguarda aprovação humana interna.",
                edition["id"],
            )
        return SimulationResult(run_id, "running", "A simulação foi retomada.")

    def _load_multipauta_fixture(self, run_id: str | None = None) -> dict[str, Any]:
        fixture_path = Path(__file__).parent / "fixtures" / "demo-multipauta.json"
        with fixture_path.open("r", encoding="utf-8") as fixture_file:
            data = json.load(fixture_file)
        actual_run_id = run_id or data["scenario_id"]
        run_slug = re.sub(r"[^a-z0-9-]+", "-", actual_run_id.casefold()).strip("-")[:64]
        if not run_slug:
            raise ValueError("O identificador da execucao multipauta e invalido.")
        safe_run_id = f"{run_slug}-{stable_hash(actual_run_id)[:8]}"
        if not data.get("items") or len(data.get("stories", [])) < 3:
            raise ValueError("A fixture multipauta exige pelo menos tres pautas ficticias.")
        id_map = {item["id"]: f"{safe_run_id}--{item['id']}" for item in data["items"]}

        def remap(value: Any) -> Any:
            if isinstance(value, str):
                for old, new in id_map.items():
                    value = value.replace(old, new)
                return value
            if isinstance(value, list):
                return [remap(item) for item in value]
            if isinstance(value, dict):
                return {key: remap(item) for key, item in value.items()}
            return value

        data = remap(data)
        data["scenario_id"] = actual_run_id
        data["_safe_run_id"] = safe_run_id
        data["_multipauta"] = True
        return data

    @_serialized_operation
    def run_multipauta_demo(self, run_id: str | None = None) -> SimulationResult:
        """Run or resume each v0.2 story independently, then compose the edition."""
        data = self._load_multipauta_fixture(run_id)
        actual_run_id = data["scenario_id"]
        self._ensure_run(actual_run_id, data["scenario_label"])
        existing_run = self.store.get_run(actual_run_id)
        edition = self.store.get_edition_by_run(actual_run_id)
        if existing_run and existing_run["status"] == "approved_internally":
            if edition and self._revalidate_approved_multipauta_edition(edition["id"]):
                edition = self.store.get_edition(edition["id"])
                return SimulationResult(
                    actual_run_id, edition["composition_status"],
                    "A aprovacao anterior foi invalidada. Resolva eventuais pendencias e "
                    "revise novamente a previa antes de aprovar.",
                    edition["id"],
                )
            return SimulationResult(
                actual_run_id, "approved_internally",
                "A edicao multipauta ja foi aprovada internamente.",
                edition["id"] if edition else None,
            )

        self._set_run_status(actual_run_id, "running")
        self._execute_step(
            actual_run_id, None, "ingest-v2",
            lambda connection, attempt: self._ingest(connection, actual_run_id, data),
        )
        self._execute_step(
            actual_run_id, None, "triage-v2",
            lambda connection, attempt: self._triage_multipauta(
                connection, actual_run_id, data
            ),
        )
        edition = self.store.get_edition_by_run(actual_run_id)
        if edition is None:
            raise ValueError("A edicao multipauta nao foi persistida durante a triagem.")
        members = self.store.edition_members(edition["id"], active_only=True)
        for member in members:
            story_id = member["story_id"]
            try:
                self._run_multipauta_story(actual_run_id, story_id, data)
                story = self.store.get_story(story_id)
                if story and story["state"] in {
                    "media_checked", "awaiting_human_approval", "approved_internally"
                }:
                    self._set_story_processing_status(
                        story_id, "ready_for_edition", "story_pipeline_completed"
                    )
            except RecoverableStepError as error:
                self._set_story_processing_status(
                    story_id, "recoverable_failure", "story_step_recoverable_failure",
                    detail={"error": str(error)},
                )
            except InterventionRequired as error:
                self._set_story_processing_status(
                    story_id, "intervention_required", "story_step_intervention_required",
                    detail={"error": str(error)},
                )
            except Exception as error:
                self._set_story_processing_status(
                    story_id, "intervention_required", "story_step_intervention_required",
                    detail={"error": f"{type(error).__name__}: {error}"[:500]},
                )

        self._compose_multipauta_edition(actual_run_id, edition["id"], data)
        edition = self.store.get_edition(edition["id"])
        active_members = self.store.edition_members(edition["id"], active_only=True)
        eligible_states = {
            "media_checked", "awaiting_human_approval", "approved_internally"
        }
        blockers = [
            row for row in active_members
            if row["required"] and row["state"] not in eligible_states
        ]
        if edition["composition_status"] == "ready_for_approval":
            self._set_run_status(actual_run_id, "awaiting_approval")
            return SimulationResult(
                actual_run_id, "awaiting_approval",
                "Previa interna multipauta pronta; aguardando aprovacao humana interna.",
                edition["id"],
            )
        return SimulationResult(
            actual_run_id, "waiting_on_blockers",
            f"Edicao aguardando resolucao de {len(blockers)} pauta(s). As demais foram processadas e persistidas; execute novamente para retomar falhas transitorias ou registre uma decisao humana de exclusao.",
            edition["id"],
        )

    @staticmethod
    def _validate_single_selected_story(data: dict[str, Any]) -> None:
        seen_identifiers: set[str] = set()
        seen_fingerprints: set[str] = set()
        selected_topics: set[str] = set()
        for item in data["items"]:
            canonical = canonicalize_identifier(item.get("source_identifier"))
            fingerprint = stable_hash(
                normalize_text(item["title"]) + "\0" + normalize_text(item["summary"])
            )
            duplicate = bool(
                (canonical and canonical in seen_identifiers)
                or fingerprint in seen_fingerprints
            )
            if duplicate:
                continue
            if canonical:
                seen_identifiers.add(canonical)
            seen_fingerprints.add(fingerprint)
            if item["relevance"]:
                selected_topics.add(item["topic_key"])
        if len(selected_topics) > 1:
            raise ValueError(
                "Fixture rejeitada: há mais de uma pauta selecionável; "
                "o Motor Editorial v0.1 monta uma pauta por edição."
            )

    def _set_story_processing_status(
        self, story_id: str, status: str, action: str,
        *, detail: dict[str, Any] | None = None,
    ) -> None:
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT processing_status FROM stories WHERE id = ?", (story_id,)
            ).fetchone()
            if row is None or row["processing_status"] == status:
                return
            connection.execute(
                "UPDATE stories SET processing_status = ?, updated_at = ? WHERE id = ?",
                (status, utc_now(), story_id),
            )
            self.store.log_event(
                connection, entity_type="story", entity_id=story_id,
                action=action, actor="orquestrador", source="multipauta-v0.2",
                before={"processing_status": row["processing_status"]},
                after={"processing_status": status, **(detail or {})},
            )

    def _triage_multipauta(
        self, connection: Any, run_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        selected = 0
        for position, config in enumerate(data["stories"], start=1):
            topic_key = config["topic_key"]
            items = connection.execute(
                """SELECT * FROM source_items WHERE run_id = ? AND topic_key = ?
                   AND state = 'normalized' ORDER BY id""",
                (run_id, topic_key),
            ).fetchall()
            relevant = [item for item in items if item["relevance"]]
            if not relevant:
                raise ValueError(f"A pauta {topic_key} nao possui item ficticio selecionavel.")
            for item in items:
                connection.execute(
                    "UPDATE source_items SET state = ? WHERE id = ?",
                    ("selected" if item["relevance"] else "discarded", item["id"]),
                )
            slug = re.sub(r"[^a-z0-9]+", "-", topic_key.casefold()).strip("-")
            story_id = f"story-{data['_safe_run_id']}-{slug}"
            now = utc_now()
            connection.execute(
                """INSERT OR IGNORE INTO stories
                   (id, run_id, topic_key, question, state, current_revision_number,
                    processing_status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'selected', 0, 'in_progress', ?, ?)""",
                (story_id, run_id, topic_key, config["question"], now, now),
            )
            for item in relevant:
                connection.execute(
                    "INSERT OR IGNORE INTO story_sources(story_id, source_item_id) VALUES (?, ?)",
                    (story_id, item["id"]),
                )
            self.store.log_event(
                connection, entity_type="story", entity_id=story_id,
                action="story_selected", actor="editor_triagem_simulado", source="triage-v2",
                after={"state": "selected", "question": config["question"], "position": position},
            )
            selected += 1

        unassigned = connection.execute(
            "SELECT id FROM source_items WHERE run_id = ? AND state = 'normalized'",
            (run_id,),
        ).fetchall()
        for item in unassigned:
            connection.execute(
                "UPDATE source_items SET state = 'discarded' WHERE id = ?", (item["id"],)
            )
            self.store.log_event(
                connection, entity_type="source_item", entity_id=item["id"],
                action="triage_discarded", actor="editor_triagem_simulado", source="triage-v2",
                before={"state": "normalized"},
                after={"state": "discarded", "reason": "item sem pauta ficticia selecionavel"},
            )
        edition_id = f"edition-{data['_safe_run_id']}-v0.2"
        now = utc_now()
        preview_path = f"editions/{edition_id}/preview.html"
        connection.execute(
            """INSERT OR IGNORE INTO editions
               (id, run_id, status, preview_path, composition_status,
                composition_fingerprint, approved_by, approved_at, created_at)
               VALUES (?, ?, 'awaiting_human_approval', ?, 'preparing', NULL, NULL, NULL, ?)""",
            (edition_id, run_id, preview_path, now),
        )
        for position, config in enumerate(data["stories"], start=1):
            slug = re.sub(r"[^a-z0-9]+", "-", config["topic_key"].casefold()).strip("-")
            story_id = f"story-{data['_safe_run_id']}-{slug}"
            connection.execute(
                """INSERT OR IGNORE INTO edition_stories
                   (edition_id, story_id, position, required, active)
                   VALUES (?, ?, ?, 1, 1)""",
                (edition_id, story_id, position),
            )
        self.store.log_event(
            connection, entity_type="edition", entity_id=edition_id,
            action="edition_composition_started", actor="montador_simulado", source="triage-v2",
            after={"composition_status": "preparing", "member_count": selected},
            artifact_ref=preview_path,
        )
        return {"selected_stories": selected, "edition_id": edition_id}

    def _story_config(self, story_id: str, data: dict[str, Any]) -> dict[str, Any]:
        story = self.store.get_story(story_id)
        if story is None:
            raise ValueError(f"Pauta inexistente: {story_id}.")
        return next(
            (row for row in data["stories"] if row["topic_key"] == story["topic_key"]),
            {},
        )

    def _ensure_run(self, run_id: str, label: str) -> None:
        with self.store.transaction() as connection:
            exists = connection.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
            if exists:
                return
            now = utc_now()
            connection.execute(
                "INSERT INTO runs(id, scenario_label, status, created_at, updated_at) "
                "VALUES (?, ?, 'running', ?, ?)",
                (run_id, label, now, now),
            )
            self.store.log_event(
                connection,
                entity_type="run",
                entity_id=run_id,
                action="simulation_created",
                actor="orquestrador",
                source="fixture",
                after={"status": "running", "label": label},
            )

    def _set_run_status(self, run_id: str, status: str) -> None:
        with self.store.transaction() as connection:
            row = connection.execute("SELECT status FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None or row["status"] == status:
                return
            connection.execute(
                "UPDATE runs SET status = ?, updated_at = ? WHERE id = ?",
                (status, utc_now(), run_id),
            )
            self.store.log_event(
                connection,
                entity_type="run",
                entity_id=run_id,
                action="run_status_changed",
                actor="orquestrador",
                source="state_machine",
                before={"status": row["status"]},
                after={"status": status},
            )

    def _execute_step(
        self,
        run_id: str,
        story_id: str | None,
        stage: str,
        operation: Callable[[Any, int], dict[str, Any] | None],
        *,
        isolate_story_failure: bool = False,
    ) -> dict[str, Any]:
        idempotency_key = f"{run_id}:{story_id or 'run'}:{stage}"
        with closing(self.store.connect()) as connection:
            successful = connection.execute(
                """SELECT output_json FROM execution_attempts
                   WHERE idempotency_key = ? AND status = 'completed'
                   ORDER BY attempt_number DESC LIMIT 1""",
                (idempotency_key,),
            ).fetchone()
            if successful:
                return json.loads(successful["output_json"])
            attempts = connection.execute(
                "SELECT COUNT(*) AS total FROM execution_attempts WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()["total"]
            last_failure = connection.execute(
                """SELECT status FROM execution_attempts WHERE idempotency_key = ?
                   ORDER BY attempt_number DESC LIMIT 1""",
                (idempotency_key,),
            ).fetchone()
        if last_failure and last_failure["status"] == "failed_intervention":
            raise InterventionRequired(
                f"A etapa '{stage}' atingiu o limite de {self.max_attempts} tentativas; "
                "é necessária intervenção humana."
            )
        if attempts >= self.max_attempts:
            self._record_intervention(
                run_id, story_id, stage, idempotency_key, attempts,
                isolate_story_failure=isolate_story_failure,
            )
            raise InterventionRequired(
                f"A etapa '{stage}' atingiu o limite de {self.max_attempts} tentativas; "
                "é necessária intervenção humana."
            )

        attempt_number = attempts + 1
        attempt_id = f"attempt-{stable_hash(idempotency_key)[:16]}-{attempt_number}"
        started_at = utc_now()
        try:
            with self.store.transaction() as connection:
                connection.execute(
                    """INSERT INTO execution_attempts
                       (id, run_id, story_id, stage, idempotency_key, attempt_number,
                        status, started_at, finished_at, error_summary, output_json)
                       VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?, NULL, '{}')""",
                    (
                        attempt_id, run_id, story_id, stage, idempotency_key,
                        attempt_number, started_at, started_at,
                    ),
                )
                output = operation(connection, attempt_number) or {}
                finished_at = utc_now()
                connection.execute(
                    """UPDATE execution_attempts SET finished_at = ?, output_json = ?
                       WHERE id = ?""",
                    (finished_at, json_dumps(output), attempt_id),
                )
                self.store.log_event(
                    connection,
                    entity_type="execution_attempt",
                    entity_id=attempt_id,
                    action="step_completed",
                    actor="adaptador_simulado",
                    source=stage,
                    before={"status": "running"},
                    after={"status": "completed", "output": output},
                )
                return output
        except RecoverableStepError as error:
            status = "failed_intervention" if attempt_number >= self.max_attempts else "failed_recoverable"
            finished_at = utc_now()
            with self.store.transaction() as connection:
                connection.execute(
                    """INSERT INTO execution_attempts
                       (id, run_id, story_id, stage, idempotency_key, attempt_number,
                        status, started_at, finished_at, error_summary, output_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}')""",
                    (
                        attempt_id, run_id, story_id, stage, idempotency_key,
                        attempt_number, status, started_at, finished_at, str(error),
                    ),
                )
                self.store.log_event(
                    connection,
                    entity_type="execution_attempt",
                    entity_id=attempt_id,
                    action=status,
                    actor="adaptador_simulado",
                    source=stage,
                    before={"status": "running"},
                    after={"status": status, "error": str(error)},
                )
                if isolate_story_failure and story_id:
                    processing_status = (
                        "intervention_required" if status == "failed_intervention"
                        else "recoverable_failure"
                    )
                    connection.execute(
                        "UPDATE stories SET processing_status = ?, updated_at = ? WHERE id = ?",
                        (processing_status, finished_at, story_id),
                    )
                else:
                    run_status = "failed_intervention" if status == "failed_intervention" else "recoverable_failure"
                    connection.execute(
                        "UPDATE runs SET status = ?, updated_at = ? WHERE id = ?",
                        (run_status, finished_at, run_id),
                    )
            if status == "failed_intervention":
                raise InterventionRequired(
                    f"A etapa '{stage}' atingiu o limite de {self.max_attempts} tentativas; "
                    "é necessária intervenção humana."
                ) from error
            raise
        except Exception as error:
            finished_at = utc_now()
            summary = f"{type(error).__name__}: {error}"[:500]
            with self.store.transaction() as connection:
                connection.execute(
                    """INSERT INTO execution_attempts
                       (id, run_id, story_id, stage, idempotency_key, attempt_number,
                        status, started_at, finished_at, error_summary, output_json)
                       VALUES (?, ?, ?, ?, ?, ?, 'failed_intervention', ?, ?, ?, '{}')""",
                    (
                        attempt_id, run_id, story_id, stage, idempotency_key,
                        attempt_number, started_at, finished_at, summary,
                    ),
                )
                if isolate_story_failure and story_id:
                    connection.execute(
                        "UPDATE stories SET processing_status = 'intervention_required', updated_at = ? WHERE id = ?",
                        (finished_at, story_id),
                    )
                else:
                    connection.execute(
                        "UPDATE runs SET status = 'failed_intervention', updated_at = ? WHERE id = ?",
                        (finished_at, run_id),
                    )
                self.store.log_event(
                    connection,
                    entity_type="execution_attempt",
                    entity_id=attempt_id,
                    action="failed_intervention",
                    actor="adaptador_simulado",
                    source=stage,
                    before={"status": "running"},
                    after={"status": "failed_intervention", "error": summary},
                )
            raise

    def _record_intervention(
        self, run_id: str, story_id: str | None, stage: str, key: str, attempts: int,
        *, isolate_story_failure: bool = False,
    ) -> None:
        now = utc_now()
        with self.store.transaction() as connection:
            if isolate_story_failure and story_id:
                connection.execute(
                    "UPDATE stories SET processing_status = 'intervention_required', updated_at = ? WHERE id = ?",
                    (now, story_id),
                )
            else:
                connection.execute(
                    "UPDATE runs SET status = 'failed_intervention', updated_at = ? WHERE id = ?",
                    (now, run_id),
                )
            self.store.log_event(
                connection,
                entity_type="execution_attempt",
                entity_id=key,
                action="retry_limit_reached",
                actor="orquestrador",
                source=stage,
                after={"attempts": attempts, "limit": self.max_attempts},
            )

    def _ingest(self, connection: Any, run_id: str, data: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        for source in data["sources"]:
            connection.execute(
                """INSERT OR IGNORE INTO sources(id, label, reference, kind, simulated)
                   VALUES (?, ?, ?, ?, 1)""",
                (source["id"], source["label"], source["reference"], source["kind"]),
            )
        added = 0
        duplicates = 0
        for item in data["items"]:
            existing = connection.execute(
                "SELECT 1 FROM source_items WHERE id = ?", (item["id"],)
            ).fetchone()
            if existing:
                continue
            canonical = canonicalize_identifier(item.get("source_identifier"))
            content_fingerprint = stable_hash(
                normalize_text(item["title"]) + "\0" + normalize_text(item["summary"])
            )
            duplicate = None
            if canonical:
                duplicate = connection.execute(
                    """SELECT id FROM source_items
                       WHERE run_id = ? AND state != 'duplicate'
                         AND canonical_identifier = ? ORDER BY created_at, id LIMIT 1""",
                    (run_id, canonical),
                ).fetchone()
            if duplicate is None:
                duplicate = connection.execute(
                    """SELECT id FROM source_items
                       WHERE run_id = ? AND state != 'duplicate'
                         AND normalized_hash = ? ORDER BY created_at, id LIMIT 1""",
                    (run_id, content_fingerprint),
                ).fetchone()
            state = "duplicate" if duplicate else "normalized"
            duplicate_of = duplicate["id"] if duplicate else None
            dedupe_key = canonical or content_fingerprint
            normalized_hash = content_fingerprint
            connection.execute(
                """INSERT INTO source_items
                   (id, run_id, source_id, source_identifier, canonical_identifier,
                    title, published_at, summary, normalized_hash, dedupe_key,
                    topic_key, relevance, state, duplicate_of, raw_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item["id"], run_id, item["source_id"], item.get("source_identifier"),
                    canonical, item["title"], item["published_at"], item["summary"],
                    normalized_hash, dedupe_key, item["topic_key"],
                    1 if item["relevance"] else 0, state, duplicate_of,
                    json_dumps(item), now,
                ),
            )
            self.store.log_event(
                connection,
                entity_type="source_item",
                entity_id=item["id"],
                action="item_imported" if not duplicate else "duplicate_detected",
                actor="adaptador_simulado",
                source="fixture",
                after={"state": state, "duplicate_of": duplicate_of, "dedupe_key": dedupe_key},
            )
            added += 1
            duplicates += int(bool(duplicate))
        return {"new_items": added, "duplicates": duplicates, "total_fixture_items": len(data["items"])}

    def _triage(
        self, connection: Any, run_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        questions = {story["topic_key"]: story["question"] for story in data["stories"]}
        topics = connection.execute(
            """SELECT DISTINCT topic_key FROM source_items
               WHERE run_id = ? AND state = 'normalized' ORDER BY topic_key""",
            (run_id,),
        ).fetchall()
        selected = 0
        discarded = 0
        for topic in topics:
            topic_key = topic["topic_key"]
            items = connection.execute(
                """SELECT * FROM source_items WHERE run_id = ? AND topic_key = ?
                   AND state = 'normalized' ORDER BY id""",
                (run_id, topic_key),
            ).fetchall()
            relevant = any(bool(item["relevance"]) for item in items)
            target_state = "selected" if relevant else "discarded"
            for item in items:
                connection.execute(
                    "UPDATE source_items SET state = ? WHERE id = ?",
                    (target_state if item["relevance"] else "discarded", item["id"]),
                )
            if not relevant:
                discarded += len(items)
                for item in items:
                    self.store.log_event(
                        connection,
                        entity_type="source_item",
                        entity_id=item["id"],
                        action="triage_discarded",
                        actor="editor_triagem_simulado",
                        source="triage",
                        before={"state": "normalized"},
                        after={"state": "discarded", "reason": "irrelevante na fixture"},
                    )
                continue
            question = questions.get(topic_key, f"O que as fontes fictícias dizem sobre {topic_key}?")
            story_id = f"story-{re.sub(r'[^a-z0-9]+', '-', topic_key.casefold()).strip('-')}"
            existing = connection.execute(
                "SELECT 1 FROM stories WHERE id = ?", (story_id,)
            ).fetchone()
            if not existing:
                now = utc_now()
                connection.execute(
                    """INSERT INTO stories
                       (id, run_id, topic_key, question, state, current_revision_number,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, 'selected', 0, ?, ?)""",
                    (story_id, run_id, topic_key, question, now, now),
                )
                self.store.log_event(
                    connection,
                    entity_type="story",
                    entity_id=story_id,
                    action="story_selected",
                    actor="editor_triagem_simulado",
                    source="triage",
                    after={"state": "selected", "question": question},
                )
            for item in items:
                if item["relevance"]:
                    connection.execute(
                        "INSERT OR IGNORE INTO story_sources(story_id, source_item_id) VALUES (?, ?)",
                        (story_id, item["id"]),
                    )
            selected += 1
        return {"selected_stories": selected, "discarded_items": discarded}

    @_serialized_operation
    def run_multipauta_story(self, run_id: str, story_id: str) -> SimulationResult:
        """Resume one persisted story without restarting other story pipelines."""
        data = self._load_multipauta_fixture(run_id)
        edition = self.store.get_edition_by_run(run_id)
        story = self.store.get_story(story_id)
        if edition is None or story is None or story["run_id"] != run_id:
            raise ValueError("Informe uma pauta existente dentro da execucao multipauta.")
        member = next(
            (row for row in self.store.edition_members(edition["id"])
             if row["story_id"] == story_id), None,
        )
        if member is None:
            raise ValueError("A pauta nao pertence a edicao multipauta.")
        if not member["active"]:
            raise ValueError("A pauta foi excluida explicitamente desta edicao.")
        if (edition["status"] == "approved_internally"
                or edition["composition_status"] == "approved_internally"):
            if self._revalidate_approved_multipauta_edition(edition["id"]):
                refreshed = self.store.get_edition(edition["id"])
                return SimulationResult(
                    run_id, refreshed["composition_status"],
                    "A aprovacao anterior foi invalidada. Resolva eventuais pendencias e "
                    "revise novamente a previa antes de aprovar.",
                    edition["id"],
                )
            return SimulationResult(
                run_id, "approved_internally",
                "A edicao multipauta ja foi aprovada internamente; a retomada nao alterou o estado.",
                edition["id"],
            )
        self._run_multipauta_story(run_id, story_id, data)
        story = self.store.get_story(story_id)
        if story and story["state"] in {
            "media_checked", "awaiting_human_approval", "approved_internally"
        }:
            self._set_story_processing_status(
                story_id, "ready_for_edition", "story_pipeline_completed"
            )
        self._compose_multipauta_edition(run_id, edition["id"], data)
        edition = self.store.get_edition(edition["id"])
        return SimulationResult(
            run_id, edition["composition_status"],
            f"Pauta {story_id} retomada; estado da edicao: {edition['composition_status']}.",
            edition["id"],
        )

    def _run_multipauta_story(self, run_id: str, story_id: str, data: dict[str, Any]) -> None:
        story = self.store.get_story(story_id)
        if story is None or story["state"] in {"awaiting_human_approval", "approved_internally"}:
            return
        if story["state"] == "blocked_by_review" and story["current_revision_number"] >= 2:
            self._record_multipauta_review_intervention(story_id)
            return
        if story["state"] == "selected":
            self._execute_step(
                run_id, story_id, "research-v2",
                lambda connection, attempt: self._research(connection, story_id, data, attempt),
                isolate_story_failure=True,
            )
        story = self.store.get_story(story_id)
        if story["state"] == "researched":
            self._execute_step(
                run_id, story_id, "draft-v1-v2",
                lambda connection, attempt: self._draft(connection, story_id, data),
                isolate_story_failure=True,
            )
        story = self.store.get_story(story_id)
        if story["state"] == "drafted":
            self._execute_step(
                run_id, story_id, "review-v1-v2",
                lambda connection, attempt: self._review(
                    connection, story_id, version=1, data=data
                ),
                isolate_story_failure=True,
            )
        story = self.store.get_story(story_id)
        if story["state"] == "blocked_by_review":
            self._execute_step(
                run_id, story_id, "correction-v2-v2",
                lambda connection, attempt: self._correct(connection, story_id, data),
                isolate_story_failure=True,
            )
        story = self.store.get_story(story_id)
        if story["state"] == "corrected":
            self._execute_step(
                run_id, story_id, "review-v2-v2",
                lambda connection, attempt: self._review(
                    connection, story_id, version=2, data=data
                ),
                isolate_story_failure=True,
            )
        story = self.store.get_story(story_id)
        if story["state"] == "blocked_by_review" and story["current_revision_number"] >= 2:
            self._record_multipauta_review_intervention(story_id)
            return
        if story["state"] == "reviewed":
            self._execute_step(
                run_id, story_id, "media-rights-v2",
                lambda connection, attempt: self._check_media(connection, story_id, data),
                isolate_story_failure=True,
            )

    def _record_multipauta_review_intervention(self, story_id: str) -> None:
        with self.store.transaction() as connection:
            exists = connection.execute(
                """SELECT 1 FROM audit_events WHERE entity_type = 'story' AND entity_id = ?
                   AND action = 'review_intervention_required'""", (story_id,)
            ).fetchone()
            if exists:
                return
            story = connection.execute(
                "SELECT state, current_revision_number FROM stories WHERE id = ?", (story_id,)
            ).fetchone()
            connection.execute(
                "UPDATE stories SET processing_status = 'intervention_required', updated_at = ? WHERE id = ?",
                (utc_now(), story_id),
            )
            self.store.log_event(
                connection, entity_type="story", entity_id=story_id,
                action="review_intervention_required", actor="orquestrador", source="review-v2-v2",
                after={"state": story["state"], "revision": story["current_revision_number"],
                       "reason": "A revisao corrigida foi reprovada nesta pauta ficticia."},
            )

    def _composition_fingerprint(self, connection: Any, edition_id: str) -> str:
        memberships = connection.execute(
            """SELECT es.position, es.story_id, es.active, es.required,
                      s.current_revision_number, ar.id AS revision_id,
                      ar.content, ar.status AS revision_status, rr.approved AS review_approved
               FROM edition_stories es JOIN stories s ON s.id = es.story_id
               LEFT JOIN article_revisions ar ON ar.story_id = s.id
                    AND ar.version = s.current_revision_number
               LEFT JOIN review_results rr ON rr.revision_id = ar.id
               WHERE es.edition_id = ? ORDER BY es.position""",
            (edition_id,),
        ).fetchall()
        payload = []
        for member in memberships:
            story_sources = connection.execute(
                """SELECT si.id, si.title, si.source_identifier, s.label, s.reference
                   FROM story_sources ss JOIN source_items si ON si.id = ss.source_item_id
                   JOIN sources s ON s.id = si.source_id
                   WHERE ss.story_id = ? ORDER BY si.id""",
                (member["story_id"],),
            ).fetchall()
            media = connection.execute(
                """SELECT md.asset_id, md.required, md.decision, md.reason,
                          ma.permission_status, ma.usage_mode
                   FROM media_decisions md JOIN media_assets ma ON ma.id = md.asset_id
                   WHERE md.story_id = ? ORDER BY md.asset_id""",
                (member["story_id"],),
            ).fetchall()
            payload.append({
                "membership": {
                    "position": member["position"], "story_id": member["story_id"],
                    "active": member["active"], "required": member["required"],
                },
                "revision": {
                    "number": member["current_revision_number"],
                    "id": member["revision_id"],
                    "content_hash": stable_hash(member["content"] or ""),
                    "status": member["revision_status"],
                    "review_approved": member["review_approved"],
                },
                "sources": [dict(row) for row in story_sources],
                "media": [dict(row) for row in media],
            })
        return stable_hash(json_dumps(payload))

    def _revalidate_approved_multipauta_edition(self, edition_id: str) -> bool:
        """Invalidate a prior human approval if its saved composition is no longer current."""
        with self.store.transaction() as connection:
            edition = connection.execute(
                "SELECT * FROM editions WHERE id = ?", (edition_id,)
            ).fetchone()
            if edition is None:
                return False
            members = connection.execute(
                """SELECT es.position, es.story_id, es.required, s.state,
                          s.current_revision_number
                   FROM edition_stories es JOIN stories s ON s.id = es.story_id
                   WHERE es.edition_id = ? AND es.active = 1 ORDER BY es.position""",
                (edition_id,),
            ).fetchall()
            media_changes = [
                self._revalidate_included_media(
                    connection, member["story_id"], source="approved-edition-revalidation"
                )
                for member in members
            ]
            media_changed = any(media_changes)
            fingerprint = self._composition_fingerprint(connection, edition_id)
            preview = self.store.safe_artifact_path(edition["preview_path"])

            all_currently_approved = bool(members) and all(
                member["state"] == "approved_internally" for member in members
            )
            review_is_current = True
            media_is_eligible = True
            for member in members:
                latest = connection.execute(
                    """SELECT ar.status, rr.approved FROM article_revisions ar
                       LEFT JOIN review_results rr ON rr.revision_id = ar.id
                       WHERE ar.story_id = ? AND ar.version = ?
                       ORDER BY rr.pass_number DESC LIMIT 1""",
                    (member["story_id"], member["current_revision_number"]),
                ).fetchone()
                if latest is None or latest["status"] != "approved" or latest["approved"] != 1:
                    review_is_current = False
                blocked_required_media = connection.execute(
                    """SELECT 1 FROM media_decisions
                       WHERE story_id = ? AND required = 1 AND decision = 'blocked' LIMIT 1""",
                    (member["story_id"],),
                ).fetchone()
                if blocked_required_media is not None:
                    media_is_eligible = False

            composition_is_current = (
                edition["status"] == "approved_internally"
                and edition["composition_status"] == "approved_internally"
                and edition["approved_by"]
                and edition["approved_at"]
                and edition["composition_fingerprint"] == fingerprint
                and preview.is_file()
                and all_currently_approved
                and review_is_current
                and media_is_eligible
                and not media_changed
            )
            if composition_is_current:
                return False

            ready_for_new_approval = (
                bool(members) and review_is_current and media_is_eligible
                and all(
                    member["state"] in {"approved_internally", "awaiting_human_approval"}
                    for member in members
                )
            )
            run = connection.execute(
                "SELECT scenario_label, status FROM runs WHERE id = ?",
                (edition["run_id"],),
            ).fetchone()
            if run is None:
                raise ValueError("A execucao vinculada a edicao nao foi encontrada.")

            if ready_for_new_approval:
                details = []
                for member in members:
                    detail = self.store.story_detail(member["story_id"], connection)
                    if detail is None:
                        raise ValueError(f"Pauta nao encontrada: {member['story_id']}.")
                    details.append((member["position"], detail))
                from .render import render_edition_preview
                self._write_preview(
                    preview,
                    render_edition_preview(edition_id, details, run["scenario_label"]),
                )

            next_composition_status = (
                "ready_for_approval" if ready_for_new_approval else "waiting_on_blockers"
            )
            connection.execute(
                """UPDATE editions SET status = 'awaiting_human_approval',
                   composition_status = ?, composition_fingerprint = ?,
                   approved_by = NULL, approved_at = NULL WHERE id = ?""",
                (
                    next_composition_status,
                    fingerprint if ready_for_new_approval else None,
                    edition_id,
                ),
            )
            if ready_for_new_approval:
                for member in members:
                    if member["state"] == "approved_internally":
                        connection.execute(
                            "UPDATE stories SET state = 'awaiting_human_approval', updated_at = ? "
                            "WHERE id = ?",
                            (utc_now(), member["story_id"]),
                        )
                        self.store.log_event(
                            connection,
                            entity_type="story",
                            entity_id=member["story_id"],
                            action="internal_approval_invalidated",
                            actor="politica_midia" if media_changed else "orquestrador",
                            source="approved-edition-revalidation",
                            before={"state": "approved_internally"},
                            after={"state": "awaiting_human_approval",
                                   "edition_id": edition_id},
                        )

            next_run_status = "awaiting_approval" if ready_for_new_approval else "running"
            if run["status"] != next_run_status:
                connection.execute(
                    "UPDATE runs SET status = ?, updated_at = ? WHERE id = ?",
                    (next_run_status, utc_now(), edition["run_id"]),
                )
                self.store.log_event(
                    connection,
                    entity_type="run",
                    entity_id=edition["run_id"],
                    action="run_status_changed",
                    actor="orquestrador",
                    source="approved-edition-revalidation",
                    before={"status": run["status"]},
                    after={"status": next_run_status},
                )

            reason = (
                "Permissao ou modalidade de uso de midia mudou."
                if media_changed
                else "A revisao, as fontes, a composicao ou o arquivo de previa mudou."
            )
            self.store.log_event(
                connection,
                entity_type="edition",
                entity_id=edition_id,
                action="internal_approval_invalidated",
                actor="politica_midia" if media_changed else "orquestrador",
                source="approved-edition-revalidation",
                before={
                    "status": edition["status"],
                    "composition_status": edition["composition_status"],
                    "approved_by": edition["approved_by"],
                    "approved_at": edition["approved_at"],
                    "composition_fingerprint": edition["composition_fingerprint"],
                },
                after={
                    "status": "awaiting_human_approval",
                    "composition_status": next_composition_status,
                    "approved_by": None,
                    "approved_at": None,
                    "composition_fingerprint": (
                        fingerprint if ready_for_new_approval else None
                    ),
                    "reason": reason,
                    "media_changed": media_changed,
                    "preview_refreshed": ready_for_new_approval,
                },
                artifact_ref=edition["preview_path"] if ready_for_new_approval else None,
            )
            return True

    @_serialized_operation
    def revalidate_edition_preview_for_access(self, edition_id: str) -> bool:
        """Refresh eligible multipauta previews before serving them over the local panel."""
        edition = self.store.get_edition(edition_id)
        if edition is None or edition["composition_status"] == "legacy_v1":
            return False
        if (edition["status"] == "approved_internally"
                or edition["composition_status"] == "approved_internally"):
            return self._revalidate_approved_multipauta_edition(edition_id)
        if edition["composition_status"] != "ready_for_approval":
            return False

        previous_fingerprint = edition["composition_fingerprint"]
        previous_preview = self.store.safe_artifact_path(edition["preview_path"])
        preview_existed = previous_preview.is_file()
        data = self._load_multipauta_fixture(edition["run_id"])
        self._compose_multipauta_edition(edition["run_id"], edition_id, data)
        refreshed = self.store.get_edition(edition_id)
        return bool(
            refreshed
            and (
                refreshed["composition_fingerprint"] != previous_fingerprint
                or (not preview_existed and previous_preview.is_file())
            )
        )

    def _compose_multipauta_edition(
        self, run_id: str, edition_id: str, data: dict[str, Any]
    ) -> None:
        with self.store.transaction() as connection:
            edition = connection.execute(
                "SELECT * FROM editions WHERE id = ?", (edition_id,)
            ).fetchone()
            members = connection.execute(
                """SELECT es.*, s.state FROM edition_stories es
                   JOIN stories s ON s.id = es.story_id
                   WHERE es.edition_id = ? AND es.active = 1 ORDER BY es.position""",
                (edition_id,),
            ).fetchall()
            blockers = [
                row for row in members
                if row["required"] and row["state"] not in {
                    "media_checked", "awaiting_human_approval", "approved_internally"
                }
            ]
            if len(members) < 2:
                blockers = blockers or list(members)
            if blockers:
                if edition["composition_status"] != "waiting_on_blockers":
                    connection.execute(
                        "UPDATE editions SET composition_status = 'waiting_on_blockers' WHERE id = ?",
                        (edition_id,),
                    )
                    self.store.log_event(
                        connection, entity_type="edition", entity_id=edition_id,
                        action="edition_waiting_on_story_blockers", actor="montador_simulado",
                        source="compose-v2",
                        after={"composition_status": "waiting_on_blockers",
                               "blockers": [row["story_id"] for row in blockers]},
                    )
                return

            for member in members:
                self._revalidate_included_media(
                    connection, member["story_id"], source="compose-v2"
                )
            fingerprint = self._composition_fingerprint(connection, edition_id)
            preview = self.store.safe_artifact_path(edition["preview_path"])
            if (edition["composition_status"] == "ready_for_approval"
                    and edition["composition_fingerprint"] == fingerprint
                    and preview.is_file()):
                return
            details = []
            for member in members:
                detail = self.store.story_detail(member["story_id"], connection)
                if detail is None:
                    raise ValueError(f"Pauta nao encontrada: {member['story_id']}.")
                details.append((member["position"], detail))
            from .render import render_edition_preview
            self._write_preview(
                preview,
                render_edition_preview(edition_id, details, data["scenario_label"]),
            )
            connection.execute(
                """UPDATE editions SET status = 'awaiting_human_approval',
                   composition_status = 'ready_for_approval', composition_fingerprint = ?
                   WHERE id = ?""",
                (fingerprint, edition_id),
            )
            for member in members:
                current = connection.execute(
                    "SELECT state FROM stories WHERE id = ?", (member["story_id"],)
                ).fetchone()["state"]
                if current == "media_checked":
                    self.store.transition_story(
                        member["story_id"], "awaiting_human_approval", connection=connection
                    )
                connection.execute(
                    "UPDATE stories SET processing_status = 'ready_for_edition' WHERE id = ?",
                    (member["story_id"],),
                )
            connection.execute(
                "UPDATE runs SET status = 'awaiting_approval', updated_at = ? WHERE id = ?",
                (utc_now(), run_id),
            )
            self.store.log_event(
                connection, entity_type="edition", entity_id=edition_id,
                action="multi_article_preview_assembled", actor="montador_simulado",
                source="compose-v2",
                after={"composition_status": "ready_for_approval",
                       "article_count": len(details), "fingerprint": fingerprint},
                artifact_ref=edition["preview_path"],
            )

    @_serialized_operation
    def exclude_story_from_edition(
        self, edition_id: str, story_id: str, actor: str, reason: str, confirmation: str
    ) -> None:
        actor = actor.strip()
        reason = reason.strip()
        if not actor:
            raise InvalidApproval("Informe quem esta registrando a exclusao interna.")
        if len(reason) < 8:
            raise InvalidApproval("Registre um motivo de exclusao com pelo menos 8 caracteres.")
        if confirmation != EXCLUSION_PHRASE:
            raise InvalidApproval(f"Para confirmar, digite exatamente: {EXCLUSION_PHRASE}")
        with self.store.transaction() as connection:
            edition = connection.execute(
                "SELECT * FROM editions WHERE id = ?", (edition_id,)
            ).fetchone()
            if edition is None:
                raise InvalidApproval("Edicao multipauta nao encontrada.")
            if edition["composition_status"] not in {
                "preparing", "waiting_on_blockers", "ready_for_approval"
            }:
                raise InvalidApproval("A edicao nao aceita alteracoes de pauta neste estado.")
            member = connection.execute(
                "SELECT * FROM edition_stories WHERE edition_id = ? AND story_id = ?",
                (edition_id, story_id),
            ).fetchone()
            if member is None or not member["active"]:
                raise InvalidApproval("A pauta nao e integrante ativa desta edicao.")
            if member["required"]:
                active_required = connection.execute(
                    """SELECT COUNT(*) FROM edition_stories
                       WHERE edition_id = ? AND active = 1 AND required = 1""",
                    (edition_id,),
                ).fetchone()[0]
                if active_required <= 2:
                    raise InvalidApproval("A exclusao deixaria menos de duas materias obrigatorias.")
            now = utc_now()
            connection.execute(
                """UPDATE edition_stories SET active = 0, exclusion_reason = ?,
                   excluded_by = ?, excluded_at = ? WHERE edition_id = ? AND story_id = ?""",
                (reason, actor, now, edition_id, story_id),
            )
            connection.execute(
                """UPDATE editions SET composition_status = 'preparing',
                   composition_fingerprint = NULL WHERE id = ?""",
                (edition_id,),
            )
            self.store.log_event(
                connection, entity_type="edition_story", entity_id=f"{edition_id}:{story_id}",
                action="story_excluded_from_edition", actor=actor, source="human_confirmation",
                before={"active": True, "story_id": story_id},
                after={"active": False, "reason": reason, "excluded_at": now},
            )
        data = self._load_multipauta_fixture(edition["run_id"])
        self._compose_multipauta_edition(edition["run_id"], edition_id, data)

    def _run_story(self, run_id: str, story_id: str, data: dict[str, Any]) -> None:
        story = self.store.get_story(story_id)
        if story is None or story["state"] in {"awaiting_human_approval", "approved_internally"}:
            return

        if story["state"] == "selected":
            try:
                self._execute_step(
                    run_id,
                    story_id,
                    "research",
                    lambda connection, attempt: self._research(
                        connection, story_id, data, attempt
                    ),
                )
            except (RecoverableStepError, InterventionRequired):
                raise
        story = self.store.get_story(story_id)
        if story["state"] == "researched":
            self._execute_step(
                run_id, story_id, "draft-v1",
                lambda connection, attempt: self._draft(connection, story_id, data),
            )
        story = self.store.get_story(story_id)
        if story["state"] == "drafted":
            self._execute_step(
                run_id, story_id, "review-v1",
                lambda connection, attempt: self._review(connection, story_id, version=1),
            )
        story = self.store.get_story(story_id)
        if story["state"] == "blocked_by_review":
            self._execute_step(
                run_id, story_id, "correction-v2",
                lambda connection, attempt: self._correct(connection, story_id),
            )
        story = self.store.get_story(story_id)
        if story["state"] == "corrected":
            self._execute_step(
                run_id, story_id, "review-v2",
                lambda connection, attempt: self._review(connection, story_id, version=2),
            )
        story = self.store.get_story(story_id)
        if story["state"] == "reviewed":
            self._execute_step(
                run_id, story_id, "media-rights",
                lambda connection, attempt: self._check_media(connection, story_id, data),
            )
        story = self.store.get_story(story_id)
        if story["state"] == "media_checked":
            self._execute_step(
                run_id, story_id, "assemble-preview",
                lambda connection, attempt: self._assemble_preview(connection, run_id, story_id, data),
            )
        story = self.store.get_story(story_id)
        if (
            story is not None
            and story["state"] == "blocked_by_review"
            and story["current_revision_number"] >= 2
        ):
            self._record_review_intervention(run_id, story_id, story["current_revision_number"])
            raise InterventionRequired(
                "A versão corrigida foi reprovada novamente; a pauta exige intervenção humana."
            )

    def _record_review_intervention(
        self, run_id: str, story_id: str, version: int
    ) -> None:
        now = utc_now()
        with self.store.transaction() as connection:
            run = connection.execute(
                "SELECT status FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if run and run["status"] != "failed_intervention":
                connection.execute(
                    "UPDATE runs SET status = 'failed_intervention', updated_at = ? WHERE id = ?",
                    (now, run_id),
                )
                self.store.log_event(
                    connection,
                    entity_type="run",
                    entity_id=run_id,
                    action="run_status_changed",
                    actor="orquestrador",
                    source="review-v2",
                    before={"status": run["status"]},
                    after={"status": "failed_intervention"},
                )
            self.store.log_event(
                connection,
                entity_type="story",
                entity_id=story_id,
                action="review_correction_limit_reached",
                actor="orquestrador",
                source="review-v2",
                after={
                    "state": "blocked_by_review",
                    "revision": version,
                    "status": "failed_intervention",
                    "reason": "A v0.1 encerra após a reprovação da segunda versão.",
                },
            )

    def _research(
        self, connection: Any, story_id: str, data: dict[str, Any], attempt_number: int
    ) -> dict[str, Any]:
        if data.get("_multipauta"):
            config = self._story_config(story_id, data)
            story_data = config["research"]
            injected_failures = int(config.get("research_failures_to_inject", 0))
        else:
            story_data = data["research"]
            injected_failures = self.research_failures_to_inject
        if attempt_number <= injected_failures:
            raise RecoverableStepError("interrupção temporária de teste antes de gravar a apuração")
        source_ids = [
            row["source_item_id"] for row in connection.execute(
                "SELECT source_item_id FROM story_sources WHERE story_id = ? ORDER BY source_item_id",
                (story_id,),
            ).fetchall()
        ]
        payload = {
            "story_id": story_id,
            "source_item_ids": source_ids,
            "claims": story_data["claims"],
            "uncertainties": story_data["uncertainties"],
            "simulated": True,
        }
        research_id = f"research-{story_id}-v1"
        connection.execute(
            """INSERT OR IGNORE INTO research_packages
               (id, story_id, version, content_json, created_at)
               VALUES (?, ?, 1, ?, ?)""",
            (research_id, story_id, json_dumps(payload), utc_now()),
        )
        self.store.transition_story(story_id, "researched", connection=connection)
        return {"research_package_id": research_id, "source_count": len(source_ids)}

    def _draft(self, connection: Any, story_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if connection.execute(
            "SELECT 1 FROM article_revisions WHERE story_id = ? AND version = 1",
            (story_id,),
        ).fetchone():
            return {"revision_id": f"revision-{story_id}-1", "created": False}
        story = connection.execute("SELECT question FROM stories WHERE id = ?", (story_id,)).fetchone()
        if data.get("_multipauta"):
            content = self._story_config(story_id, data)["draft_v1"]
        else:
            content = (
            "Esta reportagem é inteiramente fictícia e existe apenas para testar o Motor Editorial.\n\n"
            f"Pergunta da pauta: {story['question']}\n\n"
            "O comunicado inventado descreve um modo cooperativo local [news-moonlit-official].\n\n"
            "No primeiro rascunho, o texto afirma sem referência que o jogo teria desempenho idêntico "
            "em todos os aparelhos. Essa afirmação foi incluída de propósito para exercitar a revisão.\n\n"
            "Um relatório de teste inventado descreve limites observados apenas naquela compilação "
            "[news-moonlit-lab]."
            )
        revision_id = f"revision-{story_id}-1"
        connection.execute(
            """INSERT INTO article_revisions
               (id, story_id, version, content, author_role, status, created_at)
               VALUES (?, ?, 1, ?, 'redator_simulado', 'draft', ?)""",
            (revision_id, story_id, content, utc_now()),
        )
        connection.execute(
            "UPDATE stories SET current_revision_number = 1 WHERE id = ?", (story_id,)
        )
        self.store.transition_story(story_id, "drafted", connection=connection)
        self.store.log_event(
            connection,
            entity_type="article_revision",
            entity_id=revision_id,
            action="revision_created",
            actor="redator_simulado",
            source="draft-v1",
            after={"version": 1, "status": "draft"},
        )
        return {"revision_id": revision_id, "version": 1}

    def _review(
        self, connection: Any, story_id: str, version: int,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        revision = connection.execute(
            "SELECT * FROM article_revisions WHERE story_id = ? AND version = ?",
            (story_id, version),
        ).fetchone()
        if revision is None:
            raise ValueError(f"Versão {version} da matéria não encontrada.")
        if version == 1:
            content = normalize_text(revision["content"])
            findings = []
            if "desempenho idêntico em todos os aparelhos" in content:
                findings.append(
                {
                    "problem": "Afirmação sem referência",
                    "detail": "A frase sobre desempenho idêntico em todos os aparelhos não está sustentada pelo pacote de apuração.",
                    "destination": "correction",
                }
                )
            approved = not findings
        else:
            content = revision["content"]
            cited_ids = set(re.findall(r"\[([a-z0-9-]+)\]", content))
            source_ids = {
                row["source_item_id"] for row in connection.execute(
                    "SELECT source_item_id FROM story_sources WHERE story_id = ?", (story_id,)
                ).fetchall()
            }
            unsupported_phrase = "desempenho idêntico em todos os aparelhos"
            findings = []
            if unsupported_phrase in normalize_text(content):
                findings.append({
                    "problem": "Afirmação sem referência",
                    "detail": "A afirmação não sustentada permanece na versão corrigida.",
                    "destination": "correction",
                })
            if not cited_ids or not cited_ids.issubset(source_ids):
                findings.append({
                    "problem": "Referência inválida",
                    "detail": "A versão precisa apontar para itens presentes na apuração.",
                    "destination": "correction",
                })
            approved = not findings
        pass_number = 1
        review_id = f"review-{revision['id']}-{pass_number}"
        connection.execute(
            """INSERT OR IGNORE INTO review_results
               (id, story_id, revision_id, pass_number, approved, findings_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                review_id, story_id, revision["id"], pass_number,
                1 if approved else 0, json_dumps(findings), utc_now(),
            ),
        )
        connection.execute(
            "UPDATE article_revisions SET status = ? WHERE id = ?",
            ("approved" if approved else "rejected", revision["id"]),
        )
        target = "reviewed" if approved else "blocked_by_review"
        self.store.transition_story(story_id, target, connection=connection)
        self.store.log_event(
            connection,
            entity_type="review_result",
            entity_id=review_id,
            action="review_passed" if approved else "review_returned",
            actor="revisor_simulado",
            source=f"review-v{version}",
            after={"revision_id": revision["id"], "approved": approved, "findings": findings},
        )
        return {"review_id": review_id, "revision_id": revision["id"], "approved": approved, "findings": findings}

    def _correct(
        self, connection: Any, story_id: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        existing = connection.execute(
            "SELECT id FROM article_revisions WHERE story_id = ? AND version = 2",
            (story_id,),
        ).fetchone()
        if existing:
            return {"revision_id": existing["id"], "version": 2, "created": False}
        story = connection.execute(
            "SELECT question FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        if data and data.get("_multipauta"):
            content = self._story_config(story_id, data)["draft_v2"]
        else:
            content = (
            "Esta reportagem é inteiramente fictícia e existe apenas para testar o Motor Editorial.\n\n"
            f"Pergunta da pauta: {story['question']}\n\n"
            "O comunicado inventado descreve um modo cooperativo local [news-moonlit-official].\n\n"
            "Um relatório de teste inventado descreve limites observados naquela compilação específica; "
            "o resultado não deve ser generalizado para todos os aparelhos [news-moonlit-lab].\n\n"
            "As fontes e acontecimentos desta demonstração são fictícios."
            )
        if self.force_v2_review_failure and not (data and data.get("_multipauta")):
            content += (
                "\n\nAfirmação de teste sem referência: desempenho idêntico em todos os aparelhos."
            )
        revision_id = f"revision-{story_id}-2"
        connection.execute(
            """INSERT INTO article_revisions
               (id, story_id, version, content, author_role, status, created_at)
               VALUES (?, ?, 2, ?, 'redator_simulado', 'draft', ?)""",
            (revision_id, story_id, content, utc_now()),
        )
        connection.execute(
            "UPDATE stories SET current_revision_number = 2 WHERE id = ?", (story_id,)
        )
        self.store.transition_story(story_id, "corrected", connection=connection)
        self.store.log_event(
            connection,
            entity_type="article_revision",
            entity_id=revision_id,
            action="revision_corrected",
            actor="redator_simulado",
            source="correction-v2",
            before={"version": 1, "status": "rejected"},
            after={"version": 2, "status": "draft"},
        )
        return {"revision_id": revision_id, "version": 2}

    def _check_media(self, connection: Any, story_id: str, data: dict[str, Any]) -> dict[str, Any]:
        for asset in data["assets"]:
            connection.execute(
                """INSERT OR IGNORE INTO media_assets
                   (id, title, permission_status, usage_mode, media_type, label, simulated)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (
                    asset["id"], asset["title"], asset["permission_status"],
                    asset["usage_mode"], asset["media_type"], asset["label"],
                ),
            )
        included = 0
        placeholders = 0
        omitted_optional = 0
        requested_assets = (
            self._story_config(story_id, data).get("story_assets", [])
            if data.get("_multipauta") else data["story_assets"]
        )
        for requested in requested_assets:
            asset = connection.execute(
                "SELECT * FROM media_assets WHERE id = ?", (requested["asset_id"],)
            ).fetchone()
            if asset is None:
                raise ValueError(f"Ativo de fixture não encontrado: {requested['asset_id']}.")
            required = bool(requested.get("required", True))
            authorized_for_preview = (
                asset["permission_status"] == "permitido"
                and asset["usage_mode"] == "editorial_preview"
            )
            if authorized_for_preview:
                decision = "include"
                reason = "A permissão e a modalidade autorizam o uso editorial nesta prévia fictícia."
                included += 1
            elif required:
                decision = "placeholder"
                reason = (
                    f"Permissão '{asset['permission_status']}' e modalidade "
                    f"'{asset['usage_mode']}' não autorizam editorial_preview; "
                    "o ativo obrigatório foi substituído por placeholder."
                )
                placeholders += 1
            else:
                decision = "blocked"
                reason = (
                    f"Ativo opcional omitido: permissão '{asset['permission_status']}' "
                    f"e modalidade '{asset['usage_mode']}' não autorizam "
                    "editorial_preview."
                )
                omitted_optional += 1
            decision_id = f"media-decision-{story_id}-{asset['id']}"
            connection.execute(
                """INSERT OR IGNORE INTO media_decisions
                   (id, story_id, asset_id, required, decision, reason, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    decision_id, story_id, asset["id"], int(required), decision,
                    reason, utc_now(),
                ),
            )
            self.store.log_event(
                connection,
                entity_type="media_decision",
                entity_id=decision_id,
                action="media_checked",
                actor="politica_midia",
                source="fixture",
                after={
                    "permission_status": asset["permission_status"],
                    "usage_mode": asset["usage_mode"],
                    "required": required,
                    "decision": decision,
                    "reason": reason,
                },
            )
        self.store.transition_story(story_id, "media_checked", connection=connection)
        return {
            "included_assets": included,
            "placeholders": placeholders,
            "omitted_optional_assets": omitted_optional,
        }

    def _revalidate_included_media(
        self, connection: Any, story_id: str, *, source: str
    ) -> bool:
        decisions = connection.execute(
            """SELECT md.id, md.asset_id, md.decision, md.required, md.reason,
                      ma.title, ma.permission_status, ma.usage_mode
               FROM media_decisions md JOIN media_assets ma ON ma.id = md.asset_id
               WHERE md.story_id = ? ORDER BY ma.id""",
            (story_id,),
        ).fetchall()
        changed = False
        for row in decisions:
            if row["decision"] != "include":
                continue
            if (
                row["permission_status"] == "permitido"
                and row["usage_mode"] == "editorial_preview"
            ):
                continue
            new_decision = "placeholder" if row["required"] else "blocked"
            reason = (
                f"Ativo não incorporado: permissão '{row['permission_status']}' e/ou "
                f"modalidade '{row['usage_mode']}' não autoriza editorial_preview. "
                + (
                    "Substituído por placeholder."
                    if row["required"]
                    else "Ativo opcional omitido."
                )
            )
            connection.execute(
                "UPDATE media_decisions SET decision = ?, reason = ? WHERE id = ?",
                (new_decision, reason, row["id"]),
            )
            self.store.log_event(
                connection,
                entity_type="story",
                entity_id=story_id,
                action="media_permission_revalidated",
                actor="politica_midia",
                source=source,
                before={"decision": row["decision"]},
                after={
                    "media_decision_id": row["id"],
                    "asset_id": row["asset_id"],
                    "decision": new_decision,
                    "permission_status": row["permission_status"],
                    "usage_mode": row["usage_mode"],
                    "reason": reason,
                },
            )
            changed = True
        return changed

    @staticmethod
    def _write_preview(target: Path, html_text: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="\n", dir=target.parent,
                prefix="preview-", suffix=".tmp", delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(html_text)
                temp_file.flush()
            temp_path.replace(target)
            temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _assemble_preview(
        self, connection: Any, run_id: str, story_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        existing = connection.execute(
            "SELECT * FROM editions WHERE run_id = ?", (run_id,)
        ).fetchone()
        if existing:
            return {"edition_id": existing["id"], "preview_path": existing["preview_path"], "created": False}
        edition_id = "edition-demo-motor-v0.1"
        self._revalidate_included_media(connection, story_id, source="assemble-preview")
        detail = self.store.story_detail(story_id, connection)
        if detail is None:
            raise ValueError("Não foi possível montar a prévia: pauta não encontrada.")
        html_text = render_preview(edition_id, detail, data["scenario_label"])
        relative_path = f"editions/{edition_id}/preview.html"
        target = self.store.safe_artifact_path(relative_path)
        self._write_preview(target, html_text)

        now = utc_now()
        connection.execute(
            """INSERT INTO editions
               (id, run_id, status, preview_path, approved_by, approved_at, created_at)
               VALUES (?, ?, 'awaiting_human_approval', ?, NULL, NULL, ?)""",
            (edition_id, run_id, relative_path, now),
        )
        connection.execute(
            "INSERT INTO edition_stories(edition_id, story_id, position) VALUES (?, ?, 1)",
            (edition_id, story_id),
        )
        self.store.transition_story(
            story_id, "awaiting_human_approval", connection=connection
        )
        self.store.log_event(
            connection,
            entity_type="edition",
            entity_id=edition_id,
            action="internal_preview_assembled",
            actor="montador_simulado",
            source="assemble-preview",
            after={"status": "awaiting_human_approval", "preview_path": relative_path},
            artifact_ref=relative_path,
        )
        return {"edition_id": edition_id, "preview_path": relative_path}

    def _approve_multipauta_internally(
        self, edition_id: str, actor: str, confirmation: str
    ) -> None:
        approval_error: str | None = None
        with self.store.transaction() as connection:
            edition = connection.execute(
                "SELECT * FROM editions WHERE id = ?", (edition_id,)
            ).fetchone()
            if edition is None:
                raise InvalidApproval("Edicao multipauta nao encontrada.")
            if edition["composition_status"] != "ready_for_approval":
                raise InvalidApproval("A edicao ainda possui pautas bloqueadas ou nao esta pronta.")
            preview = self.store.safe_artifact_path(edition["preview_path"])
            if not preview.is_file():
                raise InvalidApproval("A previa HTML nao esta disponivel para revisao.")
            members = connection.execute(
                """SELECT es.position, es.story_id, es.required, s.*
                   FROM edition_stories es JOIN stories s ON s.id = es.story_id
                   WHERE es.edition_id = ? AND es.active = 1 ORDER BY es.position""",
                (edition_id,),
            ).fetchall()
            if len([row for row in members if row["required"]]) < 2:
                raise InvalidApproval("A aprovacao exige ao menos duas materias obrigatorias ativas.")
            for story in members:
                if story["state"] != "awaiting_human_approval":
                    raise InvalidApproval("Ha uma pauta ativa que ainda nao chegou a aprovacao humana.")
                latest = connection.execute(
                    """SELECT ar.id, ar.status, rr.approved FROM article_revisions ar
                       LEFT JOIN review_results rr ON rr.revision_id = ar.id
                       WHERE ar.story_id = ? AND ar.version = ?
                       ORDER BY rr.pass_number DESC LIMIT 1""",
                    (story["story_id"], story["current_revision_number"]),
                ).fetchone()
                if latest is None or latest["status"] != "approved" or latest["approved"] != 1:
                    raise InvalidApproval("A versao vigente de cada materia precisa de revisao aprovada.")

            media_changes = [
                self._revalidate_included_media(
                    connection, story["story_id"], source="human-approval-v2"
                )
                for story in members
            ]
            media_changed = any(media_changes)
            current_fingerprint = self._composition_fingerprint(connection, edition_id)
            if media_changed or current_fingerprint != edition["composition_fingerprint"]:
                run = connection.execute(
                    "SELECT scenario_label FROM runs WHERE id = ?", (edition["run_id"],)
                ).fetchone()
                details = []
                for story in members:
                    detail = self.store.story_detail(story["story_id"], connection)
                    if detail is None:
                        raise InvalidApproval("Nao foi possivel revalidar uma materia da previa.")
                    details.append((story["position"], detail))
                from .render import render_edition_preview
                self._write_preview(
                    preview,
                    render_edition_preview(edition_id, details, run["scenario_label"]),
                )
                connection.execute(
                    "UPDATE editions SET composition_fingerprint = ? WHERE id = ?",
                    (current_fingerprint, edition_id),
                )
                self.store.log_event(
                    connection, entity_type="edition", entity_id=edition_id,
                    action="multi_article_preview_refreshed", actor="politica_midia",
                    source="human-approval-v2",
                    before={"composition_fingerprint": edition["composition_fingerprint"]},
                    after={"composition_fingerprint": current_fingerprint,
                           "media_changed": media_changed,
                           "reason": "Revisao, fonte ou estado de direitos mudou; nova aprovacao requerida."},
                    artifact_ref=edition["preview_path"],
                )
                approval_error = (
                    "A previa multipauta foi atualizada porque revisoes, fontes ou direitos mudaram. "
                    "Revise a nova previa antes de aprovar."
                )
            else:
                now = utc_now()
                connection.execute(
                    """UPDATE editions SET status = 'approved_internally',
                       composition_status = 'approved_internally', approved_by = ?, approved_at = ?
                       WHERE id = ?""",
                    (actor, now, edition_id),
                )
                for story in members:
                    self.store.transition_story(
                        story["story_id"], "approved_internally", actor=actor,
                        connection=connection, human_confirmed=True,
                    )
                connection.execute(
                    "UPDATE runs SET status = 'approved_internally', updated_at = ? WHERE id = ?",
                    (now, edition["run_id"]),
                )
                self.store.log_event(
                    connection, entity_type="edition", entity_id=edition_id,
                    action="approved_internally", actor=actor, source="human_confirmation",
                    before={"composition_status": "ready_for_approval"},
                    after={"composition_status": "approved_internally", "approved_at": now,
                           "active_article_count": len(members)},
                    artifact_ref=edition["preview_path"],
                )
        if approval_error:
            raise InvalidApproval(approval_error)

    @_serialized_operation
    def approve_internally(self, edition_id: str, actor: str, confirmation: str) -> None:
        actor = actor.strip()
        if not actor:
            raise InvalidApproval("Informe quem está registrando a aprovação interna.")
        if confirmation != APPROVAL_PHRASE:
            raise InvalidApproval(
                f"Para confirmar, digite exatamente: {APPROVAL_PHRASE}"
            )
        edition = self.store.get_edition(edition_id)
        if edition and edition["composition_status"] != "legacy_v1":
            if (edition["status"] == "approved_internally"
                    or edition["composition_status"] == "approved_internally"):
                if self._revalidate_approved_multipauta_edition(edition_id):
                    raise InvalidApproval(
                        "A aprovacao anterior foi invalidada. Resolva eventuais pendencias e "
                        "revise novamente a previa antes de aprovar."
                    )
                raise InvalidApproval("A edicao ja foi aprovada internamente.")
            self._approve_multipauta_internally(edition_id, actor, confirmation)
            return
        approval_error: str | None = None
        with self.store.transaction() as connection:
            edition = connection.execute(
                "SELECT * FROM editions WHERE id = ?", (edition_id,)
            ).fetchone()
            if edition is None:
                raise InvalidApproval("Edição de demonstração não encontrada.")
            if edition["status"] != "awaiting_human_approval":
                raise InvalidApproval("A edição não está aguardando aprovação humana.")
            preview = self.store.safe_artifact_path(edition["preview_path"])
            if not preview.is_file():
                raise InvalidApproval("A prévia HTML não está disponível para revisão.")
            stories = connection.execute(
                """SELECT s.* FROM edition_stories es JOIN stories s ON s.id = es.story_id
                   WHERE es.edition_id = ? ORDER BY es.position""",
                (edition_id,),
            ).fetchall()
            if not stories:
                raise InvalidApproval("A edição não contém matérias para revisão.")
            for story in stories:
                if story["state"] != "awaiting_human_approval":
                    raise InvalidApproval("Há uma pauta que ainda não chegou à aprovação humana.")
                latest = connection.execute(
                    """SELECT ar.id, rr.approved FROM article_revisions ar
                       LEFT JOIN review_results rr ON rr.revision_id = ar.id
                       WHERE ar.story_id = ? AND ar.version = ?
                       ORDER BY rr.pass_number DESC LIMIT 1""",
                    (story["id"], story["current_revision_number"]),
                ).fetchone()
                if latest is None or latest["approved"] != 1:
                    raise InvalidApproval("A versão atual da matéria não foi aprovada na revisão.")
            media_changed = False
            for story in stories:
                if self._revalidate_included_media(
                    connection, story["id"], source="human-approval"
                ):
                    media_changed = True
            if media_changed:
                run = connection.execute(
                    "SELECT scenario_label FROM runs WHERE id = ?",
                    (edition["run_id"],),
                ).fetchone()
                for story in stories:
                    detail = self.store.story_detail(story["id"], connection)
                    if detail is None:
                        raise InvalidApproval("Não foi possível revalidar a prévia da edição.")
                    self._write_preview(
                        preview,
                        render_preview(edition_id, detail, run["scenario_label"]),
                    )
                self.store.log_event(
                    connection,
                    entity_type="edition",
                    entity_id=edition_id,
                    action="preview_refreshed_after_media_change",
                    actor="politica_midia",
                    source="human-approval",
                    before={"status": "awaiting_human_approval"},
                    after={
                        "status": "awaiting_human_approval",
                        "reason": "A permissão ou modalidade de uma mídia mudou; nova revisão humana necessária.",
                    },
                    artifact_ref=edition["preview_path"],
                )
                approval_error = (
                    "A permissão ou modalidade de uma mídia mudou. A prévia foi atualizada "
                    "sem o ativo; revise a nova prévia antes de aprovar."
                )
            else:
                now = utc_now()
                connection.execute(
                    """UPDATE editions SET status = 'approved_internally',
                              approved_by = ?, approved_at = ? WHERE id = ?""",
                    (actor, now, edition_id),
                )
                for story in stories:
                    self.store.transition_story(
                        story["id"], "approved_internally", actor=actor,
                        connection=connection, human_confirmed=True,
                    )
                connection.execute(
                    "UPDATE runs SET status = 'approved_internally', updated_at = ? WHERE id = ?",
                    (now, edition["run_id"]),
                )
                self.store.log_event(
                    connection,
                    entity_type="edition",
                    entity_id=edition_id,
                    action="approved_internally",
                    actor=actor,
                    source="human_confirmation",
                    before={"status": "awaiting_human_approval"},
                    after={"status": "approved_internally", "approved_at": now},
                    artifact_ref=edition["preview_path"],
                )
        if approval_error:
            raise InvalidApproval(approval_error)
