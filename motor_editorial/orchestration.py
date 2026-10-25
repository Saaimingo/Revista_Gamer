"""Durable task queue, dispatcher, scheduler, and deterministic agent fixtures."""

from __future__ import annotations

import json
import re
import threading
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Protocol

from .db import Store, json_dumps, stable_hash, utc_now


@dataclass(frozen=True)
class AgentProfile:
    profile_id: str
    version: str
    instructions: str

    @property
    def content_hash(self) -> str:
        return stable_hash(json_dumps({
            "profile_id": self.profile_id,
            "version": self.version,
            "instructions": self.instructions,
        }))


# This is a technical fixture only. It is not a public chronicler persona.
VALIDATION_PROFILE = AgentProfile(
    profile_id="internal-validation-chronicler",
    version="1.0.0",
    instructions=(
        "Perfil interno de validação técnica. Não representa persona pública, "
        "não escreve conteúdo editorial e não inventa fontes. Use somente dados fictícios."
    ),
)


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    task_type: str
    payload: dict[str, Any]
    profile_id: str
    profile_version: str
    profile_hash: str
    executor_id: str
    state: str
    idempotency_key: str
    attempts: int
    max_attempts: int
    created_at: str
    available_at: str
    external_request_started: bool
    lease_owner: str | None = field(default=None, repr=False, compare=False)
    lease_generation: int = 0
    schedule_id: str | None = None
    result: dict[str, Any] | None = None

    @classmethod
    def from_row(cls, row: Any) -> "AgentTask":
        return cls(
            task_id=row["id"],
            task_type=row["task_type"],
            payload=json.loads(row["payload_json"]),
            profile_id=row["profile_id"],
            profile_version=row["profile_version"],
            profile_hash=row["profile_hash"],
            executor_id=row["executor_id"],
            state=row["state"],
            idempotency_key=row["idempotency_key"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            created_at=row["created_at"],
            available_at=row["available_at"],
            external_request_started=bool(row["external_request_started"]),
            lease_owner=row["lease_owner"],
            lease_generation=row["lease_generation"],
            schedule_id=row["schedule_id"],
            result=json.loads(row["result_json"]) if row["result_json"] else None,
        )


class TaskFailure(Exception):
    """A classified failure safe to persist without provider response bodies."""

    def __init__(
        self,
        code: str,
        summary: str,
        *,
        retryable: bool = False,
        uncertain: bool = False,
        blocked: bool = False,
        retry_after_seconds: int = 30,
    ) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary
        self.retryable = retryable
        self.uncertain = uncertain
        self.blocked = blocked
        self.retry_after_seconds = max(1, retry_after_seconds)


class LeaseOwnershipLost(RuntimeError):
    """Raised when a worker attempts to act outside its current lease fence."""


def _as_utc(value: datetime | str | None = None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("Horários da fila precisam conter fuso horário.")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime | str | None = None) -> str:
    return _as_utc(value).isoformat(timespec="seconds")


def _lease_iso(value: datetime | str | None = None) -> str:
    """Use sub-second precision so short leases can be heartbeated safely."""
    return _as_utc(value).isoformat(timespec="microseconds")


_SENSITIVE_FIELD_NAMES = {
    "access_token", "refresh_token", "id_token", "token", "api_key", "apikey",
    "client_secret", "password", "cookie", "authorization", "code_verifier",
    "authorization_code", "credentials",
}
_SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~-]{16,}"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{8,}"),
)


def _assert_no_credentials(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in _SENSITIVE_FIELD_NAMES:
                raise ValueError(f"Campo de credencial proibido em {path}.{key}.")
            _assert_no_credentials(nested, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _assert_no_credentials(nested, f"{path}[{index}]")
    elif isinstance(value, str) and any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
        raise ValueError(f"Valor com formato de credencial proibido em {path}.")


class AgentQueue:
    """Queue records share the Motor database and its SQLite transaction policy."""

    def __init__(self, store: Store):
        self.store = store

    @staticmethod
    def _event(
        connection: Any,
        task_id: str,
        action: str,
        attempt_number: int,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        connection.execute(
            """INSERT INTO agent_task_events
               (task_id, occurred_at, action, attempt_number, detail_json)
               VALUES (?, ?, ?, ?, ?)""",
            (task_id, utc_now(), action, attempt_number,
             json_dumps(dict(detail or {}))),
        )

    @staticmethod
    def _enqueue_in_connection(
        connection: Any,
        *,
        task_type: str,
        payload: Mapping[str, Any],
        profile_id: str,
        profile_version: str,
        profile_hash: str,
        executor_id: str,
        idempotency_key: str,
        max_attempts: int,
        task_id: str | None = None,
        available_at: datetime | str | None = None,
        schedule_id: str | None = None,
    ) -> tuple[str, bool]:
        _assert_no_credentials(payload)
        payload_json = json_dumps(dict(payload))
        if len(payload_json.encode("utf-8")) > 1_000_000:
            raise ValueError("Payload excede o limite local de 1 MB.")
        existing = connection.execute(
            "SELECT * FROM agent_tasks WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            expected = (
                task_type, payload_json, profile_id, profile_version,
                profile_hash, executor_id, max_attempts, schedule_id,
            )
            actual = (
                existing["task_type"], existing["payload_json"],
                existing["profile_id"], existing["profile_version"],
                existing["profile_hash"], existing["executor_id"],
                existing["max_attempts"], existing["schedule_id"],
            )
            if actual != expected:
                raise ValueError("Chave idempotente já usada com conteúdo diferente.")
            if task_id is not None and existing["id"] != task_id:
                raise ValueError("Chave idempotente já vinculada a outro task_id.")
            return existing["id"], False

        task_id = task_id or str(uuid.uuid4())
        now = utc_now()
        connection.execute(
            """INSERT INTO agent_tasks
               (id, task_type, payload_json, profile_id, profile_version,
                profile_hash, executor_id, state, idempotency_key, attempts,
                max_attempts, created_at, available_at, schedule_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?, 0, ?, ?, ?, ?)""",
            (task_id, task_type, payload_json, profile_id, profile_version,
             profile_hash, executor_id, idempotency_key, max_attempts, now,
             _iso(available_at), schedule_id),
        )
        AgentQueue._event(connection, task_id, "enqueued", 0, {
            "task_type": task_type, "executor_id": executor_id,
            "profile_id": profile_id, "profile_version": profile_version,
        })
        return task_id, True

    def enqueue(
        self,
        *,
        task_type: str,
        payload: Mapping[str, Any],
        profile: AgentProfile,
        executor_id: str,
        idempotency_key: str,
        max_attempts: int = 3,
        task_id: str | None = None,
        available_at: datetime | str | None = None,
    ) -> str:
        if not task_type.strip() or not executor_id.strip() or not idempotency_key.strip() or (task_id is not None and not task_id.strip()):
            raise ValueError("Tipo, executor e chave idempotente são obrigatórios.")
        if max_attempts < 1:
            raise ValueError("O limite de tentativas deve ser positivo.")
        with self.store.transaction() as connection:
            task_id, _ = self._enqueue_in_connection(
                connection, task_type=task_type, payload=payload,
                profile_id=profile.profile_id, profile_version=profile.version,
                profile_hash=profile.content_hash, executor_id=executor_id,
                idempotency_key=idempotency_key, max_attempts=max_attempts,
                task_id=task_id,
                available_at=available_at,
            )
            return task_id

    def _recover_expired(self, connection: Any, now: str) -> None:
        expired = connection.execute(
            """SELECT * FROM agent_tasks
               WHERE state = 'running' AND lease_until IS NOT NULL AND lease_until <= ?""",
            (now,),
        ).fetchall()
        for row in expired:
            if row["external_request_started"]:
                state = "uncertain"
                action = "lease_expired_uncertain"
                summary = "Lease expirou após início da chamada externa; revisão humana necessária."
            elif row["attempts"] >= row["max_attempts"]:
                state = "failed"
                action = "lease_expired_attempt_limit"
                summary = "Lease expirou e o limite de tentativas foi atingido."
            else:
                state = "queued"
                action = "lease_expired_requeued"
                summary = "Lease expirou antes de chamada externa; tarefa retomável."
            connection.execute(
                """UPDATE agent_tasks SET state = ?, available_at = ?, lease_until = NULL,
                   lease_owner = NULL, error_code = ?, error_summary = ?
                   WHERE id = ? AND state = 'running' AND lease_generation = ?""",
                (state, now, action, summary, row["id"], row["lease_generation"]),
            )
            self._event(connection, row["id"], action, row["attempts"], {
                "state": state, "lease_generation": row["lease_generation"],
            })

    @staticmethod
    def _owns_lease(row: Any, lease_owner: str | None, lease_generation: int,
                    now: str) -> bool:
        return bool(
            row is not None
            and row["state"] == "running"
            and lease_owner
            and row["lease_owner"] == lease_owner
            and row["lease_generation"] == lease_generation
            and row["lease_until"] is not None
            and row["lease_until"] > now
        )

    def claim_next(
        self,
        *,
        task_id: str | None = None,
        lease_seconds: int = 120,
        now: datetime | str | None = None,
    ) -> AgentTask | None:
        if lease_seconds < 1:
            raise ValueError("O lease precisa ser positivo.")
        instant = _as_utc(now)
        now_iso = _lease_iso(instant)
        lease_until = _lease_iso(instant + timedelta(seconds=lease_seconds))
        with self.store.transaction() as connection:
            self._recover_expired(connection, now_iso)
            if task_id:
                row = connection.execute(
                    """SELECT * FROM agent_tasks
                       WHERE id = ? AND state IN ('queued', 'retry_wait')
                         AND available_at <= ?""",
                    (task_id, now_iso),
                ).fetchone()
            else:
                row = connection.execute(
                    """SELECT * FROM agent_tasks
                       WHERE state IN ('queued', 'retry_wait') AND available_at <= ?
                       ORDER BY available_at, created_at, id LIMIT 1""",
                    (now_iso,),
                ).fetchone()
            if row is None:
                return None
            attempts = row["attempts"] + 1
            lease_owner = str(uuid.uuid4())
            lease_generation = row["lease_generation"] + 1
            connection.execute(
                """UPDATE agent_tasks SET state = 'running', attempts = ?,
                   started_at = ?, lease_until = ?, lease_owner = ?,
                   lease_generation = ?, external_request_started = 0,
                   error_code = NULL, error_summary = NULL
                   WHERE id = ? AND state IN ('queued', 'retry_wait')""",
                (attempts, _iso(instant), lease_until, lease_owner,
                 lease_generation, row["id"]),
            )
            self._event(connection, row["id"], "claimed", attempts, {
                "lease_until": lease_until,
                "lease_generation": lease_generation,
            })
            refreshed = connection.execute(
                "SELECT * FROM agent_tasks WHERE id = ?", (row["id"],)
            ).fetchone()
            return AgentTask.from_row(refreshed)

    def renew_lease(
        self,
        task_id: str,
        lease_owner: str,
        lease_generation: int,
        *,
        lease_seconds: int,
        now: datetime | str | None = None,
    ) -> bool:
        if lease_seconds < 1:
            raise ValueError("O lease precisa ser positivo.")
        instant = _as_utc(now)
        now_iso = _lease_iso(instant)
        lease_until = _lease_iso(instant + timedelta(seconds=lease_seconds))
        with self.store.transaction() as connection:
            self._recover_expired(connection, now_iso)
            row = connection.execute(
                "SELECT * FROM agent_tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if not self._owns_lease(row, lease_owner, lease_generation, now_iso):
                return False
            updated = connection.execute(
                """UPDATE agent_tasks SET lease_until = ?
                   WHERE id = ? AND state = 'running' AND lease_owner = ?
                     AND lease_generation = ? AND lease_until > ?""",
                (lease_until, task_id, lease_owner, lease_generation, now_iso),
            )
            if updated.rowcount != 1:
                return False
            self._event(connection, task_id, "lease_renewed", row["attempts"], {
                "lease_until": lease_until,
                "lease_generation": lease_generation,
            })
            return True

    def mark_external_started(
        self,
        task_id: str,
        lease_owner: str,
        lease_generation: int,
        *,
        now: datetime | str | None = None,
    ) -> bool:
        now_iso = _lease_iso(now)
        with self.store.transaction() as connection:
            self._recover_expired(connection, now_iso)
            row = connection.execute(
                "SELECT * FROM agent_tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if not self._owns_lease(row, lease_owner, lease_generation, now_iso):
                return False
            updated = connection.execute(
                """UPDATE agent_tasks SET external_request_started = 1
                   WHERE id = ? AND state = 'running' AND lease_owner = ?
                     AND lease_generation = ? AND lease_until > ?""",
                (task_id, lease_owner, lease_generation, now_iso),
            )
            if updated.rowcount != 1:
                return False
            self._event(connection, task_id, "external_request_started", row["attempts"], {
                "lease_generation": lease_generation,
            })
            return True

    def complete(
        self,
        task_id: str,
        lease_owner: str,
        lease_generation: int,
        result: Mapping[str, Any],
        *,
        now: datetime | str | None = None,
    ) -> bool:
        _assert_no_credentials(result, "result")
        encoded = json_dumps(dict(result))
        if len(encoded.encode("utf-8")) > 1_000_000:
            raise ValueError("Resultado excede o limite local de 1 MB.")
        now_iso = _lease_iso(now)
        with self.store.transaction() as connection:
            self._recover_expired(connection, now_iso)
            row = connection.execute(
                "SELECT * FROM agent_tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if not self._owns_lease(row, lease_owner, lease_generation, now_iso):
                return False
            updated = connection.execute(
                """UPDATE agent_tasks SET state = 'succeeded', result_json = ?,
                   completed_at = ?, lease_until = NULL, lease_owner = NULL
                   WHERE id = ? AND state = 'running' AND lease_owner = ?
                     AND lease_generation = ? AND lease_until > ?""",
                (encoded, _iso(now), task_id, lease_owner, lease_generation, now_iso),
            )
            if updated.rowcount != 1:
                return False
            self._event(connection, task_id, "succeeded", row["attempts"], {
                "result_sha256": stable_hash(encoded),
                "lease_generation": lease_generation,
            })
            return True

    def fail(
        self,
        task_id: str,
        lease_owner: str,
        lease_generation: int,
        failure: TaskFailure,
        *,
        now: datetime | str | None = None,
    ) -> str | None:
        now_iso = _lease_iso(now)
        with self.store.transaction() as connection:
            self._recover_expired(connection, now_iso)
            row = connection.execute(
                "SELECT * FROM agent_tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if not self._owns_lease(row, lease_owner, lease_generation, now_iso):
                return None
            if failure.blocked:
                state = "blocked"
                available_at = row["available_at"]
            elif failure.uncertain:
                state = "uncertain"
                available_at = row["available_at"]
            elif failure.retryable and row["attempts"] < row["max_attempts"]:
                state = "retry_wait"
                available_at = _iso(
                    _as_utc(now)
                    + timedelta(seconds=failure.retry_after_seconds)
                )
            else:
                state = "failed"
                available_at = row["available_at"]
            updated = connection.execute(
                """UPDATE agent_tasks SET state = ?, available_at = ?, lease_until = NULL,
                   lease_owner = NULL, error_code = ?, error_summary = ?
                   WHERE id = ? AND state = 'running' AND lease_owner = ?
                     AND lease_generation = ? AND lease_until > ?""",
                (state, available_at, failure.code, failure.summary, task_id,
                 lease_owner, lease_generation, now_iso),
            )
            if updated.rowcount != 1:
                return None
            self._event(connection, task_id, state, row["attempts"], {
                "error_code": failure.code,
                "retryable": failure.retryable,
                "uncertain": failure.uncertain,
                "lease_generation": lease_generation,
            })
            return state

    def reconcile_expired(self, task_id: str, *, now: datetime | str | None = None) -> str:
        now_iso = _lease_iso(now)
        with self.store.transaction() as connection:
            self._recover_expired(connection, now_iso)
            row = connection.execute(
                "SELECT state FROM agent_tasks WHERE id = ?", (task_id,)
            ).fetchone()
            return row["state"] if row else "missing"

    def get(self, task_id: str) -> AgentTask | None:
        with closing(self.store.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM agent_tasks WHERE id = ?", (task_id,)
            ).fetchone()
            return AgentTask.from_row(row) if row else None

    def list_tasks(self, limit: int = 100) -> list[AgentTask]:
        with closing(self.store.connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM agent_tasks ORDER BY created_at DESC, id LIMIT ?",
                (max(1, min(1000, limit)),),
            ).fetchall()
            return [AgentTask.from_row(row) for row in rows]

    def events(self, task_id: str) -> list[dict[str, Any]]:
        with closing(self.store.connect()) as connection:
            rows = connection.execute(
                """SELECT sequence, occurred_at, action, attempt_number, detail_json
                   FROM agent_task_events WHERE task_id = ? ORDER BY sequence""",
                (task_id,),
            ).fetchall()
            return [{
                "sequence": row["sequence"], "occurred_at": row["occurred_at"],
                "action": row["action"], "attempt_number": row["attempt_number"],
                "detail": json.loads(row["detail_json"]),
            } for row in rows]

    def create_schedule(
        self,
        *,
        schedule_id: str,
        task_type: str,
        payload: Mapping[str, Any],
        profile: AgentProfile,
        executor_id: str,
        interval_seconds: int,
        timezone_name: str = "UTC",
        misfire_policy: str = "skip",
        enabled: bool = False,
        start_at: datetime | str | None = None,
    ) -> None:
        if interval_seconds < 1:
            raise ValueError("O intervalo deve ser de pelo menos 1 segundo.")
        if misfire_policy not in {"skip", "run_once"}:
            raise ValueError("Política de atraso deve ser skip ou run_once.")
        if not timezone_name or any(
            not part or not part.replace("_", "").replace("-", "").isalnum()
            for part in timezone_name.split("/")
        ):
            raise ValueError("Identificador de fuso horário inválido.")
        if not schedule_id.strip() or not task_type.strip() or not executor_id.strip():
            raise ValueError("Identificador, tipo e executor são obrigatórios.")
        now = utc_now()
        next_run = _iso(start_at) if start_at is not None else _iso()
        with self.store.transaction() as connection:
            connection.execute(
                """INSERT INTO agent_schedules
                   (id, task_type, payload_json, profile_id, profile_version,
                    profile_hash, executor_id, interval_seconds, timezone,
                    misfire_policy, enabled, next_run_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (schedule_id, task_type, json_dumps(dict(payload)), profile.profile_id,
                 profile.version, profile.content_hash, executor_id, interval_seconds,
                 timezone_name, misfire_policy, int(enabled), next_run, now, now),
            )
            # Schedules are configured but never activated by default.
            connection.execute(
                """INSERT INTO audit_events
                   (occurred_at, entity_type, entity_id, action, actor, source,
                    before_json, after_json)
                   VALUES (?, 'agent_schedule', ?, 'created', 'operator', 'scheduler',
                           NULL, ?)""",
                (now, schedule_id, json_dumps({
                    "enabled": bool(enabled), "interval_seconds": interval_seconds,
                    "timezone": timezone_name, "misfire_policy": misfire_policy,
                    "executor_id": executor_id,
                })),
            )

    def set_schedule_enabled(
        self, schedule_id: str, enabled: bool, *, now: datetime | str | None = None
    ) -> None:
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM agent_schedules WHERE id = ?", (schedule_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Agenda inexistente.")
            now_value = _iso(now)
            connection.execute(
                """UPDATE agent_schedules SET enabled = ?, next_run_at = ?, updated_at = ?
                   WHERE id = ?""",
                (int(enabled), now_value, now_value, schedule_id),
            )
            connection.execute(
                """INSERT INTO audit_events
                   (occurred_at, entity_type, entity_id, action, actor, source,
                    before_json, after_json)
                   VALUES (?, 'agent_schedule', ?, ?, 'operator', 'scheduler', ?, ?)""",
                (now_value, schedule_id, "enabled" if enabled else "disabled",
                 json_dumps({"enabled": bool(row["enabled"])}),
                 json_dumps({"enabled": bool(enabled)})),
            )

    def list_schedules(self) -> list[dict[str, Any]]:
        with closing(self.store.connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM agent_schedules ORDER BY id"
            ).fetchall()
            return [{
                "id": row["id"], "task_type": row["task_type"],
                "executor_id": row["executor_id"], "interval_seconds": row["interval_seconds"],
                "timezone": row["timezone"], "misfire_policy": row["misfire_policy"],
                "enabled": bool(row["enabled"]), "next_run_at": row["next_run_at"],
                "last_enqueued_at": row["last_enqueued_at"],
            } for row in rows]

    def scheduler_tick(self, now: datetime | str | None = None) -> list[str]:
        instant = _as_utc(now)
        now_iso = _iso(instant)
        created_task_ids: list[str] = []
        with self.store.transaction() as connection:
            due_schedules = connection.execute(
                """SELECT * FROM agent_schedules
                   WHERE enabled = 1 AND next_run_at <= ? ORDER BY next_run_at, id""",
                (now_iso,),
            ).fetchall()
            for schedule in due_schedules:
                due = _as_utc(schedule["next_run_at"])
                interval = schedule["interval_seconds"]
                lateness = (instant - due).total_seconds()
                missed = lateness > interval
                intervals_elapsed = max(0, int(lateness // interval))
                next_run = due + timedelta(seconds=(intervals_elapsed + 1) * interval)
                if missed and schedule["misfire_policy"] == "skip":
                    connection.execute(
                        """UPDATE agent_schedules SET next_run_at = ?, updated_at = ?
                           WHERE id = ?""",
                        (_iso(next_run), now_iso, schedule["id"]),
                    )
                    connection.execute(
                        """INSERT INTO audit_events
                           (occurred_at, entity_type, entity_id, action, actor, source, after_json)
                           VALUES (?, 'agent_schedule', ?, 'missed_run_skipped',
                                   'scheduler', 'scheduler', ?)""",
                        (now_iso, schedule["id"], json_dumps({
                            "missed_policy": "skip", "next_run_at": _iso(next_run),
                        })),
                    )
                    continue

                slot_key = _iso(due)
                task_id, was_created = self._enqueue_in_connection(
                    connection, task_type=schedule["task_type"],
                    payload=json.loads(schedule["payload_json"]),
                    profile_id=schedule["profile_id"],
                    profile_version=schedule["profile_version"],
                    profile_hash=schedule["profile_hash"],
                    executor_id=schedule["executor_id"],
                    idempotency_key=f"schedule:{schedule['id']}:{slot_key}",
                    max_attempts=3, available_at=now_iso,
                    schedule_id=schedule["id"],
                )
                if was_created:
                    created_task_ids.append(task_id)
                connection.execute(
                    """UPDATE agent_schedules SET next_run_at = ?, last_enqueued_at = ?,
                       updated_at = ? WHERE id = ?""",
                    (_iso(next_run), now_iso, now_iso, schedule["id"]),
                )
            return created_task_ids


@dataclass(frozen=True)
class DispatchOutcome:
    task_id: str | None
    state: str
    error_code: str | None = None


class TaskExecutionContext:
    def __init__(self, queue: AgentQueue, task: AgentTask, lease_seconds: int):
        if not task.lease_owner:
            raise ValueError("Contexto exige uma tarefa reclamada com proprietário.")
        self._queue = queue
        self.task_id = task.task_id
        self._lease_owner = task.lease_owner
        self._lease_generation = task.lease_generation
        self._lease_seconds = max(1, lease_seconds)
        self.external_request_started = False
        self.agent_role_profile: Any | None = None
        self.agent_task_envelope: Any | None = None
        self.agent_invocation_context: Any | None = None
        self._heartbeat_stop = threading.Event()
        self._ownership_lost = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    def start_heartbeat(self) -> None:
        interval = max(0.05, min(self._lease_seconds / 3, 30.0))

        def heartbeat() -> None:
            while not self._heartbeat_stop.wait(interval):
                try:
                    renewed = self._queue.renew_lease(
                        self.task_id,
                        self._lease_owner,
                        self._lease_generation,
                        lease_seconds=self._lease_seconds,
                    )
                except Exception:
                    # Fail closed. The dispatcher will reconcile from durable state.
                    self._ownership_lost.set()
                    return
                if not renewed:
                    self._ownership_lost.set()
                    return

        self._heartbeat_thread = threading.Thread(
            target=heartbeat, name=f"task-lease-{self.task_id[:8]}", daemon=True
        )
        self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        self._heartbeat_stop.set()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=5)

    def assert_lease_owned(self) -> None:
        if self._ownership_lost.is_set():
            raise LeaseOwnershipLost("Worker perdeu a propriedade da tarefa.")

    def mark_external_started(self) -> None:
        self.assert_lease_owned()
        if not self._queue.mark_external_started(
            self.task_id, self._lease_owner, self._lease_generation
        ):
            self._ownership_lost.set()
            raise LeaseOwnershipLost("Worker perdeu a propriedade antes da chamada externa.")
        self.external_request_started = True


class TaskExecutor(Protocol):
    executor_id: str

    def execute(
        self,
        task: AgentTask,
        profile: AgentProfile,
        context: TaskExecutionContext,
    ) -> Mapping[str, Any]: ...


class TaskDispatcher:
    def __init__(
        self,
        queue: AgentQueue,
        *,
        executors: Mapping[str, TaskExecutor],
        profiles: Mapping[tuple[str, str], AgentProfile],
        lease_seconds: int = 120,
        role_catalog: Any | None = None,
    ):
        self.queue = queue
        self.executors = dict(executors)
        self.profiles = dict(profiles)
        self.lease_seconds = lease_seconds
        self.role_catalog = role_catalog

    def dispatch_one(
        self,
        task_id: str | None = None,
        *,
        now: datetime | str | None = None,
    ) -> DispatchOutcome:
        task = self.queue.claim_next(
            task_id=task_id, lease_seconds=self.lease_seconds, now=now
        )
        if task is None:
            return DispatchOutcome(task_id, "idle")

        def report_failure(failure: TaskFailure) -> DispatchOutcome:
            state = self.queue.fail(
                task.task_id, task.lease_owner, task.lease_generation, failure
            )
            if state is None:
                return DispatchOutcome(
                    task.task_id, self.queue.reconcile_expired(task.task_id), "lease_lost"
                )
            return DispatchOutcome(task.task_id, state, failure.code)

        executor = self.executors.get(task.executor_id)
        profile = self.profiles.get((task.profile_id, task.profile_version))
        if executor is None:
            failure = TaskFailure(
                "executor_unavailable", "Executor configurado não está disponível.", blocked=True
            )
            return report_failure(failure)
        if profile is None or profile.content_hash != task.profile_hash:
            failure = TaskFailure(
                "profile_unavailable", "Perfil versionado da tarefa não está disponível ou mudou.",
                blocked=True,
            )
            return report_failure(failure)
        invocation_context = None
        task_envelope = None
        if self.role_catalog is not None:
            try:
                from .agent_contracts import envelope_from_payload

                task_envelope = envelope_from_payload(task.payload)
                if task_envelope.task_id != task.task_id:
                    raise ValueError("task_id do envelope diverge da fila")
                if task.task_type != f"agent.role.{task_envelope.role_id}":
                    raise ValueError("tipo da fila diverge do role_id")
                invocation_context = self.role_catalog.prepare_invocation(
                    task_envelope,
                    input_payload=task.payload.get("input"),
                    research_packet=task.payload.get("research_packet"),
                )
            except (ValueError, TypeError) as error:
                return report_failure(TaskFailure(
                    "agent_contract_invalid",
                    f"Contrato funcional bloqueado ({type(error).__name__}).",
                    blocked=True,
                ))
        context = TaskExecutionContext(self.queue, task, self.lease_seconds)
        if invocation_context is not None:
            context.agent_role_profile = invocation_context.role_profile
            context.agent_task_envelope = task_envelope
            context.agent_invocation_context = invocation_context
        try:
            context.start_heartbeat()
            try:
                result = executor.execute(task, profile, context)
            finally:
                context.stop_heartbeat()
            context.assert_lease_owned()
            if not isinstance(result, Mapping):
                raise TaskFailure("invalid_result", "Executor não retornou um objeto estruturado.")
            if invocation_context is not None:
                try:
                    result = self.role_catalog.validate_result(
                        task_envelope, result, invocation_context.role_profile
                    ).to_dict()
                except (ValueError, TypeError) as error:
                    raise TaskFailure(
                        "invalid_agent_result",
                        f"AgentResultEnvelope inválido ({type(error).__name__}).",
                        blocked=True,
                    ) from error
            completed = self.queue.complete(
                task.task_id, task.lease_owner, task.lease_generation, result
            )
            if not completed:
                return DispatchOutcome(
                    task.task_id, self.queue.reconcile_expired(task.task_id), "lease_lost"
                )
            return DispatchOutcome(task.task_id, "succeeded")
        except LeaseOwnershipLost:
            return DispatchOutcome(
                task.task_id, self.queue.reconcile_expired(task.task_id), "lease_lost"
            )
        except TaskFailure as failure:
            return report_failure(failure)
        except Exception as error:  # Persist class only: exception text could contain credentials.
            failure = TaskFailure(
                "executor_exception", f"Falha não classificada do executor ({type(error).__name__}).",
                uncertain=context.external_request_started,
            )
            return report_failure(failure)
        finally:
            context.stop_heartbeat()


class SimulatedExecutor:
    executor_id = "simulated"

    def execute(
        self,
        task: AgentTask,
        profile: AgentProfile,
        context: TaskExecutionContext,
    ) -> Mapping[str, Any]:
        if profile.profile_id != VALIDATION_PROFILE.profile_id:
            raise TaskFailure("profile_not_supported", "Executor simulado aceita somente o perfil de validação.")
        role = task.payload.get("role")
        if role == "researcher":
            return {
                "role": "researcher", "fictional": True,
                "notes": ["fixture sintética; nenhuma fonte ou acontecimento real"],
            }
        if role == "writer":
            revision = int(task.payload.get("revision", 1))
            marker = " REV-A" if revision >= 2 else ""
            return {
                "role": "writer", "revision": revision,
                "draft": f"Rascunho técnico fictício de validação.{marker}",
            }
        if role == "reviewer":
            draft = str(task.payload.get("draft", ""))
            approved = "REV-A" in draft
            return {
                "role": "reviewer", "approved": approved,
                "findings": [] if approved else ["marcador sintético REV-A ausente"],
            }
        raise TaskFailure("unsupported_simulation", "Papel de agente simulado desconhecido.")


def run_simulated_chain(queue: AgentQueue) -> dict[str, Any]:
    """Run a fictional researcher → writer → reviewer → correction → reviewer chain."""
    dispatcher = TaskDispatcher(
        queue,
        executors={"simulated": SimulatedExecutor()},
        profiles={(VALIDATION_PROFILE.profile_id, VALIDATION_PROFILE.version): VALIDATION_PROFILE},
    )
    chain_id = str(uuid.uuid4())
    chain: list[AgentTask] = []

    def run_task(task_type: str, role: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        task_id = queue.enqueue(
            task_type=task_type, payload={"role": role, **payload},
            profile=VALIDATION_PROFILE, executor_id="simulated",
            idempotency_key=f"validation-chain:{chain_id}:{len(chain) + 1}",
        )
        outcome = dispatcher.dispatch_one(task_id)
        task = queue.get(task_id)
        if outcome.state != "succeeded" or task is None or task.result is None:
            raise RuntimeError(f"A cadeia simulada parou em {task_type}: {outcome.state}.")
        chain.append(task)
        return task.result

    research = run_task("validation.research", "researcher", {"topic": "fixture"})
    draft_v1 = run_task("validation.draft", "writer", {
        "revision": 1, "research": research,
    })
    review_v1 = run_task("validation.review", "reviewer", {"draft": draft_v1["draft"]})
    if review_v1["approved"]:
        raise RuntimeError("A fixture deveria produzir uma rejeição inicial para testar retomada.")
    draft_v2 = run_task("validation.correct", "writer", {
        "revision": 2, "research": research, "findings": review_v1["findings"],
    })
    review_v2 = run_task("validation.review", "reviewer", {"draft": draft_v2["draft"]})
    if not review_v2["approved"]:
        raise RuntimeError("A revisão final da fixture deveria aprovar a correção.")
    return {
        "chain_id": chain_id,
        "task_ids": [task.task_id for task in chain],
        "profile": {
            "id": VALIDATION_PROFILE.profile_id,
            "version": VALIDATION_PROFILE.version,
            "sha256": VALIDATION_PROFILE.content_hash,
        },
        "steps": [task.result for task in chain],
        "status": "succeeded",
        "external_calls": 0,
    }


class SchedulerWorker:
    """Polling worker. Schedule definitions default disabled and remain persisted."""

    def __init__(
        self,
        queue: AgentQueue,
        dispatcher: TaskDispatcher,
        *,
        poll_seconds: float = 2.0,
        on_tick: Callable[[list[str], DispatchOutcome], None] | None = None,
    ):
        if poll_seconds <= 0:
            raise ValueError("O intervalo de sondagem deve ser positivo.")
        self.queue = queue
        self.dispatcher = dispatcher
        self.poll_seconds = poll_seconds
        self.on_tick = on_tick

    def run(self, stop_event: threading.Event | None = None, max_cycles: int | None = None) -> None:
        stop = stop_event or threading.Event()
        cycles = 0
        while not stop.is_set() and (max_cycles is None or cycles < max_cycles):
            created = self.queue.scheduler_tick()
            outcome = self.dispatcher.dispatch_one()
            if self.on_tick:
                self.on_tick(created, outcome)
            cycles += 1
            if outcome.state == "idle" and not created:
                stop.wait(self.poll_seconds)
