"""SQLite persistence, referential integrity, and guarded transitions."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .domain import InvalidApproval, InvalidTransition, STORY_TRANSITIONS


SCHEMA_VERSION = 7


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def canonicalize_identifier(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    parts = urlsplit(value)
    if not parts.scheme:
        return normalize_text(value)
    scheme = parts.scheme.casefold()
    host = parts.netloc.casefold()
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit((scheme, host, path, query, ""))


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Store:
    """A small local SQLite store. Each operation opens a short-lived connection."""

    def __init__(self, db_path: Path, artifact_dir: Path):
        self.db_path = Path(db_path)
        self.artifact_dir = Path(artifact_dir).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.transaction() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Banco da versão {version} é mais novo que este aplicativo "
                    f"(v{SCHEMA_VERSION})."
                )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    reference TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    simulated INTEGER NOT NULL CHECK (simulated IN (0, 1))
                );

                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    scenario_label TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN (
                        'running', 'recoverable_failure', 'failed_intervention',
                        'awaiting_approval', 'approved_internally'
                    )),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_items (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    source_id TEXT NOT NULL REFERENCES sources(id),
                    source_identifier TEXT,
                    canonical_identifier TEXT,
                    title TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    normalized_hash TEXT NOT NULL,
                    dedupe_key TEXT NOT NULL,
                    topic_key TEXT NOT NULL,
                    relevance INTEGER NOT NULL CHECK (relevance IN (0, 1)),
                    state TEXT NOT NULL CHECK (state IN (
                        'normalized', 'duplicate', 'selected', 'discarded'
                    )),
                    duplicate_of TEXT REFERENCES source_items(id),
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_source_items_dedupe
                    ON source_items(run_id, dedupe_key, state);
                CREATE INDEX IF NOT EXISTS ix_source_items_topic
                    ON source_items(run_id, topic_key, state);

                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    topic_key TEXT NOT NULL,
                    question TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN (
                        'selected', 'researched', 'drafted', 'blocked_by_review',
                        'corrected', 'reviewed', 'media_checked',
                        'awaiting_human_approval', 'approved_internally'
                    )),
                    current_revision_number INTEGER NOT NULL DEFAULT 0,
                    processing_status TEXT NOT NULL DEFAULT 'in_progress',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(run_id, topic_key)
                );

                CREATE TABLE IF NOT EXISTS story_sources (
                    story_id TEXT NOT NULL REFERENCES stories(id),
                    source_item_id TEXT NOT NULL REFERENCES source_items(id),
                    PRIMARY KEY (story_id, source_item_id)
                );

                CREATE TABLE IF NOT EXISTS research_packages (
                    id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL REFERENCES stories(id),
                    version INTEGER NOT NULL,
                    content_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(story_id, version)
                );

                CREATE TABLE IF NOT EXISTS article_revisions (
                    id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL REFERENCES stories(id),
                    version INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    author_role TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN (
                        'draft', 'rejected', 'corrected', 'approved'
                    )),
                    created_at TEXT NOT NULL,
                    UNIQUE(story_id, version)
                );

                CREATE TABLE IF NOT EXISTS review_results (
                    id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL REFERENCES stories(id),
                    revision_id TEXT NOT NULL REFERENCES article_revisions(id),
                    pass_number INTEGER NOT NULL,
                    approved INTEGER NOT NULL CHECK (approved IN (0, 1)),
                    findings_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(revision_id, pass_number)
                );

                CREATE TABLE IF NOT EXISTS media_assets (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    permission_status TEXT NOT NULL CHECK (permission_status IN (
                        'permitido', 'pendente', 'bloqueado'
                    )),
                    usage_mode TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    simulated INTEGER NOT NULL CHECK (simulated IN (0, 1))
                );

                CREATE TABLE IF NOT EXISTS media_decisions (
                    id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL REFERENCES stories(id),
                    asset_id TEXT NOT NULL REFERENCES media_assets(id),
                    required INTEGER NOT NULL CHECK (required IN (0, 1)),
                    decision TEXT NOT NULL CHECK (decision IN (
                        'include', 'placeholder', 'blocked'
                    )),
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(story_id, asset_id)
                );

                CREATE TABLE IF NOT EXISTS editions (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    status TEXT NOT NULL CHECK (status IN (
                        'awaiting_human_approval', 'approved_internally'
                    )),
                    preview_path TEXT NOT NULL,
                    composition_status TEXT NOT NULL DEFAULT 'legacy_v1' CHECK (composition_status IN (
                        'legacy_v1', 'preparing', 'waiting_on_blockers',
                        'ready_for_approval', 'approved_internally'
                    )),
                    composition_fingerprint TEXT,
                    approved_by TEXT,
                    approved_at TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(run_id)
                );

                CREATE TABLE IF NOT EXISTS edition_stories (
                    edition_id TEXT NOT NULL REFERENCES editions(id),
                    story_id TEXT NOT NULL REFERENCES stories(id),
                    position INTEGER NOT NULL,
                    required INTEGER NOT NULL DEFAULT 1 CHECK (required IN (0, 1)),
                    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                    exclusion_reason TEXT,
                    excluded_by TEXT,
                    excluded_at TEXT,
                    PRIMARY KEY (edition_id, story_id),
                    UNIQUE(edition_id, position)
                );

                CREATE TABLE IF NOT EXISTS execution_attempts (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    story_id TEXT REFERENCES stories(id),
                    stage TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK (status IN (
                        'completed', 'failed_recoverable', 'failed_intervention'
                    )),
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    error_summary TEXT,
                    output_json TEXT NOT NULL,
                    UNIQUE(idempotency_key, attempt_number)
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    source TEXT NOT NULL,
                    before_json TEXT,
                    after_json TEXT,
                    artifact_ref TEXT
                );

                CREATE INDEX IF NOT EXISTS ix_audit_entity
                    ON audit_events(entity_type, entity_id, sequence);
                CREATE INDEX IF NOT EXISTS ix_attempt_key
                    ON execution_attempts(idempotency_key, attempt_number);

                CREATE TABLE IF NOT EXISTS agent_tasks (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    profile_version TEXT NOT NULL,
                    profile_hash TEXT NOT NULL,
                    executor_id TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN (
                        'queued', 'running', 'retry_wait', 'succeeded',
                        'failed', 'blocked', 'uncertain', 'cancelled'
                    )),
                    idempotency_key TEXT NOT NULL UNIQUE,
                    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
                    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 1),
                    created_at TEXT NOT NULL,
                    available_at TEXT NOT NULL,
                    lease_until TEXT,
                    lease_owner TEXT,
                    lease_generation INTEGER NOT NULL DEFAULT 0
                        CHECK (lease_generation >= 0),
                    started_at TEXT,
                    completed_at TEXT,
                    external_request_started INTEGER NOT NULL DEFAULT 0
                        CHECK (external_request_started IN (0, 1)),
                    error_code TEXT,
                    error_summary TEXT,
                    result_json TEXT,
                    schedule_id TEXT,
                    FOREIGN KEY (schedule_id) REFERENCES agent_schedules(id)
                );
                CREATE INDEX IF NOT EXISTS ix_agent_tasks_ready
                    ON agent_tasks(state, available_at, created_at);
                CREATE INDEX IF NOT EXISTS ix_agent_tasks_lease
                    ON agent_tasks(state, lease_until);

                CREATE TABLE IF NOT EXISTS agent_task_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES agent_tasks(id),
                    occurred_at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    detail_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_agent_task_events_task
                    ON agent_task_events(task_id, sequence);

                CREATE TABLE IF NOT EXISTS agent_task_dependencies (
                    task_id TEXT NOT NULL REFERENCES agent_tasks(id),
                    depends_on_task_id TEXT NOT NULL REFERENCES agent_tasks(id),
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (task_id, depends_on_task_id),
                    CHECK (task_id <> depends_on_task_id)
                );
                CREATE INDEX IF NOT EXISTS ix_agent_task_dependencies_parent
                    ON agent_task_dependencies(depends_on_task_id, task_id);

                CREATE TABLE IF NOT EXISTS agent_schedules (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    profile_version TEXT NOT NULL,
                    profile_hash TEXT NOT NULL,
                    executor_id TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL CHECK (interval_seconds >= 1),
                    timezone TEXT NOT NULL DEFAULT 'UTC',
                    misfire_policy TEXT NOT NULL CHECK (misfire_policy IN (
                        'skip', 'run_once'
                    )),
                    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
                    next_run_at TEXT NOT NULL,
                    last_enqueued_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    schedule_group_id TEXT,
                    schedule_kind TEXT NOT NULL DEFAULT 'interval'
                        CHECK (schedule_kind IN ('interval', 'daily_window')),
                    local_time TEXT,
                    misfire_grace_seconds INTEGER NOT NULL DEFAULT 300
                        CHECK (misfire_grace_seconds >= 0),
                    domain_quotas_json TEXT NOT NULL DEFAULT '{}',
                    dry_run INTEGER NOT NULL DEFAULT 1 CHECK (dry_run IN (0, 1))
                );
                """
            )
            if version < SCHEMA_VERSION:
                task_columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(agent_tasks)"
                    ).fetchall()
                }
                if "lease_owner" not in task_columns:
                    connection.execute(
                        "ALTER TABLE agent_tasks ADD COLUMN lease_owner TEXT"
                    )
                if "lease_generation" not in task_columns:
                    connection.execute(
                        """ALTER TABLE agent_tasks ADD COLUMN lease_generation INTEGER
                           NOT NULL DEFAULT 0 CHECK (lease_generation >= 0)"""
                    )
                columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(media_decisions)"
                    ).fetchall()
                }
                if "required" not in columns:
                    connection.execute(
                        """ALTER TABLE media_decisions
                           ADD COLUMN required INTEGER NOT NULL DEFAULT 1
                           CHECK (required IN (0, 1))"""
                    )
                edition_columns = {
                    row["name"] for row in connection.execute(
                        "PRAGMA table_info(editions)"
                    ).fetchall()
                }
                if "composition_status" not in edition_columns:
                    connection.execute(
                        """ALTER TABLE editions ADD COLUMN composition_status TEXT NOT NULL
                           DEFAULT 'legacy_v1' CHECK (composition_status IN (
                               'legacy_v1', 'preparing', 'waiting_on_blockers',
                               'ready_for_approval', 'approved_internally'
                           ))"""
                    )
                if "composition_fingerprint" not in edition_columns:
                    connection.execute(
                        "ALTER TABLE editions ADD COLUMN composition_fingerprint TEXT"
                    )
                story_columns = {
                    row["name"] for row in connection.execute(
                        "PRAGMA table_info(stories)"
                    ).fetchall()
                }
                if "processing_status" not in story_columns:
                    connection.execute(
                        "ALTER TABLE stories ADD COLUMN processing_status TEXT NOT NULL DEFAULT 'in_progress'"
                    )
                membership_columns = {
                    row["name"] for row in connection.execute(
                        "PRAGMA table_info(edition_stories)"
                    ).fetchall()
                }
                if "required" not in membership_columns:
                    connection.execute(
                        """ALTER TABLE edition_stories ADD COLUMN required INTEGER NOT NULL
                           DEFAULT 1 CHECK (required IN (0, 1))"""
                    )
                if "active" not in membership_columns:
                    connection.execute(
                        """ALTER TABLE edition_stories ADD COLUMN active INTEGER NOT NULL
                           DEFAULT 1 CHECK (active IN (0, 1))"""
                    )
                for column in ("exclusion_reason", "excluded_by", "excluded_at"):
                    if column not in membership_columns:
                        connection.execute(
                            f"ALTER TABLE edition_stories ADD COLUMN {column} TEXT"
                        )
                schedule_columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(agent_schedules)"
                    ).fetchall()
                }
                schedule_additions = {
                    "schedule_group_id": "TEXT",
                    "schedule_kind": "TEXT NOT NULL DEFAULT 'interval' CHECK (schedule_kind IN ('interval', 'daily_window'))",
                    "local_time": "TEXT",
                    "misfire_grace_seconds": "INTEGER NOT NULL DEFAULT 300 CHECK (misfire_grace_seconds >= 0)",
                    "domain_quotas_json": "TEXT NOT NULL DEFAULT '{}'",
                    "dry_run": "INTEGER NOT NULL DEFAULT 1 CHECK (dry_run IN (0, 1))",
                }
                for column, declaration in schedule_additions.items():
                    if column not in schedule_columns:
                        connection.execute(
                            f"ALTER TABLE agent_schedules ADD COLUMN {column} {declaration}"
                        )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS ix_agent_schedules_group "
                "ON agent_schedules(schedule_group_id, id)"
            )
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @staticmethod
    def log_event(
        connection: sqlite3.Connection,
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str,
        source: str,
        before: Any = None,
        after: Any = None,
        artifact_ref: str | None = None,
    ) -> None:
        connection.execute(
            """INSERT INTO audit_events
               (occurred_at, entity_type, entity_id, action, actor, source,
                before_json, after_json, artifact_ref)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                utc_now(), entity_type, entity_id, action, actor, source,
                json_dumps(before) if before is not None else None,
                json_dumps(after) if after is not None else None,
                artifact_ref,
            ),
        )

    def transition_story(
        self,
        story_id: str,
        target: str,
        *,
        actor: str = "orquestrador",
        connection: sqlite3.Connection | None = None,
        human_confirmed: bool = False,
    ) -> None:
        if connection is None:
            with self.transaction() as transaction:
                self.transition_story(
                    story_id, target, actor=actor, connection=transaction,
                    human_confirmed=human_confirmed,
                )
            return

        story = connection.execute(
            "SELECT * FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        if story is None:
            raise InvalidTransition(f"Pauta inexistente: {story_id}.")
        current = story["state"]
        if target not in STORY_TRANSITIONS.get(current, set()):
            raise InvalidTransition(
                f"Transição recusada: {current} -> {target}. "
                "O fluxo exige que as etapas anteriores sejam concluídas."
            )

        revision = connection.execute(
            """SELECT * FROM article_revisions
               WHERE story_id = ? AND version = ?""",
            (story_id, story["current_revision_number"]),
        ).fetchone()
        if target in {"drafted", "corrected", "reviewed", "blocked_by_review"}:
            if revision is None:
                raise InvalidTransition("A pauta não tem a versão exigida para esta etapa.")
        if target == "corrected" and revision["status"] != "draft":
            raise InvalidTransition("A correção precisa criar uma nova versão em rascunho.")
        if target in {"reviewed", "blocked_by_review"}:
            review = connection.execute(
                """SELECT * FROM review_results WHERE revision_id = ?
                   ORDER BY pass_number DESC LIMIT 1""",
                (revision["id"],),
            ).fetchone()
            if review is None:
                raise InvalidTransition("A versão atual ainda não passou por revisão.")
            if bool(review["approved"]) != (target == "reviewed"):
                raise InvalidTransition(
                    "O resultado da revisão não permite essa transição."
                )
        if target == "researched":
            research = connection.execute(
                "SELECT 1 FROM research_packages WHERE story_id = ? LIMIT 1",
                (story_id,),
            ).fetchone()
            if research is None:
                raise InvalidTransition("A apuração precisa ser persistida primeiro.")
        if target == "media_checked":
            decisions = connection.execute(
                """SELECT md.decision, md.required,
                          ma.permission_status, ma.usage_mode
                   FROM media_decisions md
                   JOIN media_assets ma ON ma.id = md.asset_id
                   WHERE md.story_id = ?""",
                (story_id,),
            ).fetchall()
            if not decisions or any(
                (row["decision"] == "blocked" and row["required"])
                or (
                    row["decision"] == "include"
                    and (
                        row["permission_status"] != "permitido"
                        or row["usage_mode"] != "editorial_preview"
                    )
                )
                for row in decisions
            ):
                raise InvalidTransition(
                    "A política de mídia exige autorização para editorial_preview."
                )
        if target == "awaiting_human_approval":
            edition = connection.execute(
                "SELECT * FROM editions WHERE run_id = ?", (story["run_id"],)
            ).fetchone()
            if edition is None or edition["status"] != "awaiting_human_approval":
                raise InvalidTransition("A prévia interna precisa existir antes da aprovação.")
            preview_path = self.safe_artifact_path(edition["preview_path"])
            if not preview_path.is_file():
                raise InvalidTransition("A prévia HTML não foi encontrada no disco.")
        if target == "approved_internally":
            if not human_confirmed:
                raise InvalidApproval("A aprovação exige confirmação humana explícita.")
            edition = connection.execute(
                "SELECT status FROM editions WHERE run_id = ?", (story["run_id"],)
            ).fetchone()
            if edition is None or edition["status"] != "approved_internally":
                raise InvalidApproval("A edição ainda não foi aprovada internamente.")

        before = {"state": current}
        after = {"state": target}
        connection.execute(
            "UPDATE stories SET state = ?, updated_at = ? WHERE id = ?",
            (target, utc_now(), story_id),
        )
        self.log_event(
            connection,
            entity_type="story",
            entity_id=story_id,
            action="state_transition",
            actor=actor,
            source="state_machine",
            before=before,
            after=after,
        )

    def safe_artifact_path(self, relative_path: str) -> Path:
        candidate = (self.artifact_dir / relative_path).resolve()
        if candidate != self.artifact_dir and self.artifact_dir not in candidate.parents:
            raise ValueError("Referência de artefato fora da pasta autorizada.")
        return candidate

    def counts(self) -> dict[str, int]:
        with closing(self.connect()) as connection:
            return {
                "items": connection.execute("SELECT COUNT(*) FROM source_items").fetchone()[0],
                "duplicates": connection.execute(
                    "SELECT COUNT(*) FROM source_items WHERE state = 'duplicate'"
                ).fetchone()[0],
                "stories": connection.execute("SELECT COUNT(*) FROM stories").fetchone()[0],
                "revisions": connection.execute(
                    "SELECT COUNT(*) FROM article_revisions"
                ).fetchone()[0],
                "editions": connection.execute("SELECT COUNT(*) FROM editions").fetchone()[0],
                "events": connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0],
                "attempts": connection.execute(
                    "SELECT COUNT(*) FROM execution_attempts"
                ).fetchone()[0],
            }

    def get_run(self, run_id: str) -> sqlite3.Row | None:
        with closing(self.connect()) as connection:
            return connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()

    def get_edition(self, edition_id: str) -> sqlite3.Row | None:
        with closing(self.connect()) as connection:
            return connection.execute(
                "SELECT * FROM editions WHERE id = ?", (edition_id,)
            ).fetchone()

    def get_edition_by_run(self, run_id: str) -> sqlite3.Row | None:
        with closing(self.connect()) as connection:
            return connection.execute(
                "SELECT * FROM editions WHERE run_id = ?", (run_id,)
            ).fetchone()

    def edition_members(self, edition_id: str, *, active_only: bool = False) -> list[sqlite3.Row]:
        with closing(self.connect()) as connection:
            where = "WHERE es.edition_id = ?" + (" AND es.active = 1" if active_only else "")
            return connection.execute(
                """SELECT es.*, s.topic_key, s.question, s.state, s.current_revision_number
                   FROM edition_stories es JOIN stories s ON s.id = es.story_id """
                + where + " ORDER BY es.position",
                (edition_id,),
            ).fetchall()

    def get_story(self, story_id: str) -> sqlite3.Row | None:
        with closing(self.connect()) as connection:
            return connection.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()

    def list_stories(self) -> list[sqlite3.Row]:
        with closing(self.connect()) as connection:
            return connection.execute(
                "SELECT * FROM stories ORDER BY created_at, id"
            ).fetchall()

    def list_editions(self) -> list[sqlite3.Row]:
        with closing(self.connect()) as connection:
            return connection.execute(
                "SELECT * FROM editions ORDER BY created_at, id"
            ).fetchall()

    def list_events(self, entity_id: str | None = None) -> list[sqlite3.Row]:
        with closing(self.connect()) as connection:
            if entity_id is None:
                return connection.execute(
                    "SELECT * FROM audit_events ORDER BY sequence DESC LIMIT 100"
                ).fetchall()
            return connection.execute(
                """SELECT * FROM audit_events WHERE entity_id = ?
                   ORDER BY sequence""",
                (entity_id,),
            ).fetchall()

    def story_detail(
        self, story_id: str, connection: sqlite3.Connection | None = None
    ) -> dict[str, Any] | None:
        if connection is None:
            with closing(self.connect()) as read_connection:
                return self.story_detail(story_id, read_connection)
        story = connection.execute(
            "SELECT * FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        if story is None:
            return None
        sources = connection.execute(
            """SELECT si.*, s.label AS source_label, s.reference AS source_reference
               FROM story_sources ss
               JOIN source_items si ON si.id = ss.source_item_id
               JOIN sources s ON s.id = si.source_id
               WHERE ss.story_id = ? ORDER BY si.id""",
            (story_id,),
        ).fetchall()
        revisions = connection.execute(
            """SELECT ar.*, rr.approved AS review_approved,
                      rr.findings_json, rr.created_at AS reviewed_at
               FROM article_revisions ar
               LEFT JOIN review_results rr ON rr.revision_id = ar.id
               WHERE ar.story_id = ? ORDER BY ar.version, rr.pass_number""",
            (story_id,),
        ).fetchall()
        media = connection.execute(
            """SELECT md.*, ma.title, ma.permission_status, ma.label, ma.usage_mode
               FROM media_decisions md JOIN media_assets ma ON ma.id = md.asset_id
               WHERE md.story_id = ? ORDER BY ma.id""",
            (story_id,),
        ).fetchall()
        events = connection.execute(
            "SELECT * FROM audit_events WHERE entity_id = ? ORDER BY sequence",
            (story_id,),
        ).fetchall()
        research = connection.execute(
            """SELECT * FROM research_packages WHERE story_id = ?
               ORDER BY version""",
            (story_id,),
        ).fetchall()
        return {
            "story": story,
            "sources": sources,
            "revisions": revisions,
            "media": media,
            "events": events,
            "research": research,
        }

    def dashboard(self) -> dict[str, Any]:
        with closing(self.connect()) as connection:
            run = connection.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            items = connection.execute(
                """SELECT state, COUNT(*) AS total FROM source_items
                   GROUP BY state ORDER BY state"""
            ).fetchall()
            stories = connection.execute(
                """SELECT st.*,
                          EXISTS(SELECT 1 FROM edition_stories es
                                 JOIN editions ed ON ed.id = es.edition_id
                                 WHERE es.story_id = st.id
                                   AND ed.composition_status != 'legacy_v1') AS multipauta_member
                   FROM stories st ORDER BY st.created_at, st.id"""
            ).fetchall()
            editions = connection.execute(
                "SELECT * FROM editions ORDER BY created_at, id"
            ).fetchall()
            memberships = connection.execute(
                """SELECT es.*, s.question, s.state, s.current_revision_number
                   FROM edition_stories es JOIN stories s ON s.id = es.story_id
                   ORDER BY es.edition_id, es.position"""
            ).fetchall()
            attempts = connection.execute(
                "SELECT * FROM execution_attempts ORDER BY started_at DESC, id DESC LIMIT 20"
            ).fetchall()
            events = connection.execute(
                "SELECT * FROM audit_events ORDER BY sequence DESC LIMIT 30"
            ).fetchall()
            return {
                "run": run,
                "items": items,
                "stories": stories,
                "editions": editions,
                "edition_memberships": memberships,
                "attempts": attempts,
                "events": events,
            }
