"""Deterministic, offline editorial demonstration pipeline."""

from __future__ import annotations

import json
import re
import tempfile
from contextlib import closing
from dataclasses import dataclass
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
MAX_ATTEMPTS = 3


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
            self._record_intervention(run_id, story_id, stage, idempotency_key, attempts)
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
        self, run_id: str, story_id: str | None, stage: str, key: str, attempts: int
    ) -> None:
        now = utc_now()
        with self.store.transaction() as connection:
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
        if attempt_number <= self.research_failures_to_inject:
            raise RecoverableStepError("interrupção temporária de teste antes de gravar a apuração")
        story_data = data["research"]
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

    def _review(self, connection: Any, story_id: str, version: int) -> dict[str, Any]:
        revision = connection.execute(
            "SELECT * FROM article_revisions WHERE story_id = ? AND version = ?",
            (story_id, version),
        ).fetchone()
        if revision is None:
            raise ValueError(f"Versão {version} da matéria não encontrada.")
        if version == 1:
            approved = False
            findings = [
                {
                    "problem": "Afirmação sem referência",
                    "detail": "A frase sobre desempenho idêntico em todos os aparelhos não está sustentada pelo pacote de apuração.",
                    "destination": "correction",
                }
            ]
        else:
            content = revision["content"]
            cited_ids = set(re.findall(r"\[(news-[a-z0-9-]+)\]", content))
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

    def _correct(self, connection: Any, story_id: str) -> dict[str, Any]:
        existing = connection.execute(
            "SELECT id FROM article_revisions WHERE story_id = ? AND version = 2",
            (story_id,),
        ).fetchone()
        if existing:
            return {"revision_id": existing["id"], "version": 2, "created": False}
        story = connection.execute(
            "SELECT question FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        content = (
            "Esta reportagem é inteiramente fictícia e existe apenas para testar o Motor Editorial.\n\n"
            f"Pergunta da pauta: {story['question']}\n\n"
            "O comunicado inventado descreve um modo cooperativo local [news-moonlit-official].\n\n"
            "Um relatório de teste inventado descreve limites observados naquela compilação específica; "
            "o resultado não deve ser generalizado para todos os aparelhos [news-moonlit-lab].\n\n"
            "As fontes e acontecimentos desta demonstração são fictícios."
        )
        if self.force_v2_review_failure:
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
        for requested in data["story_assets"]:
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

    def approve_internally(self, edition_id: str, actor: str, confirmation: str) -> None:
        actor = actor.strip()
        if not actor:
            raise InvalidApproval("Informe quem está registrando a aprovação interna.")
        if confirmation != APPROVAL_PHRASE:
            raise InvalidApproval(
                f"Para confirmar, digite exatamente: {APPROVAL_PHRASE}"
            )
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
