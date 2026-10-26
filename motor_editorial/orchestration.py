"""Durable task queue, dispatcher, scheduler, and deterministic agent fixtures."""

from __future__ import annotations

import json
import re
import threading
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Protocol, Sequence

from .db import Store, json_dumps, stable_hash, utc_now
from .radar_policy import (
    load_timezone,
    next_daily_window_utc,
    normalize_domain_quotas,
    parse_local_time,
)


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
    def _normalized_dependencies(dependencies: Sequence[str]) -> tuple[str, ...]:
        if isinstance(dependencies, (str, bytes)):
            raise ValueError("dependencies precisa ser uma sequência de task_id.")
        values = tuple(dependencies)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("dependencies contém task_id inválido.")
        if len(set(values)) != len(values):
            raise ValueError("dependencies contém task_id repetido.")
        return tuple(sorted(values))

    @staticmethod
    def _link_dependency_in_connection(
        connection: Any,
        *,
        task_id: str,
        depends_on_task_id: str,
    ) -> bool:
        if task_id == depends_on_task_id:
            raise ValueError("Uma tarefa não pode depender de si mesma.")
        child = connection.execute(
            "SELECT state, attempts FROM agent_tasks WHERE id = ?", (task_id,)
        ).fetchone()
        parent = connection.execute(
            "SELECT state FROM agent_tasks WHERE id = ?", (depends_on_task_id,)
        ).fetchone()
        if child is None or parent is None:
            raise ValueError("Dependência referencia tarefa ausente.")
        if child["state"] not in {"queued", "retry_wait"}:
            raise ValueError("Dependências só podem ser adicionadas antes do despacho da tarefa.")
        exists = connection.execute(
            "SELECT 1 FROM agent_task_dependencies WHERE task_id = ? AND depends_on_task_id = ?",
            (task_id, depends_on_task_id),
        ).fetchone()
        if exists is not None:
            return False
        cycle = connection.execute(
            """WITH RECURSIVE dependency_chain(task_id) AS (
                   SELECT depends_on_task_id FROM agent_task_dependencies WHERE task_id = ?
                   UNION
                   SELECT edge.depends_on_task_id
                   FROM agent_task_dependencies AS edge
                   JOIN dependency_chain AS chain ON edge.task_id = chain.task_id
               )
               SELECT 1 FROM dependency_chain WHERE task_id = ? LIMIT 1""",
            (depends_on_task_id, task_id),
        ).fetchone()
        if cycle is not None:
            raise ValueError("Dependência criaria ciclo no grafo de tarefas.")
        connection.execute(
            """INSERT INTO agent_task_dependencies (task_id, depends_on_task_id, created_at)
               VALUES (?, ?, ?)""",
            (task_id, depends_on_task_id, utc_now()),
        )
        AgentQueue._event(connection, task_id, "dependency_added", child["attempts"], {
            "depends_on_task_id": depends_on_task_id,
        })
        return True

    @staticmethod
    def _dependency_ids_in_connection(connection: Any, task_id: str) -> tuple[str, ...]:
        rows = connection.execute(
            "SELECT depends_on_task_id FROM agent_task_dependencies WHERE task_id = ? ORDER BY depends_on_task_id",
            (task_id,),
        ).fetchall()
        return tuple(row["depends_on_task_id"] for row in rows)

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
        dependencies: Sequence[str] = (),
    ) -> tuple[str, bool]:
        _assert_no_credentials(payload)
        dependency_ids = AgentQueue._normalized_dependencies(dependencies)
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
            if AgentQueue._dependency_ids_in_connection(connection, existing["id"]) != dependency_ids:
                raise ValueError("Chave idempotente já usada com dependências diferentes.")
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
        for dependency_id in dependency_ids:
            AgentQueue._link_dependency_in_connection(
                connection, task_id=task_id, depends_on_task_id=dependency_id,
            )
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
        dependencies: Sequence[str] = (),
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
                dependencies=dependencies,
            )
            return task_id

    def add_dependency(self, task_id: str, depends_on_task_id: str) -> bool:
        """Add a prerequisite to a queued task, with existence and cycle checks."""
        if not isinstance(task_id, str) or not task_id.strip() or not isinstance(depends_on_task_id, str) or not depends_on_task_id.strip():
            raise ValueError("task_id e depends_on_task_id são obrigatórios.")
        with self.store.transaction() as connection:
            return self._link_dependency_in_connection(
                connection, task_id=task_id, depends_on_task_id=depends_on_task_id,
            )

    def dependencies(self, task_id: str) -> tuple[str, ...]:
        with closing(self.store.connect()) as connection:
            exists = connection.execute("SELECT 1 FROM agent_tasks WHERE id = ?", (task_id,)).fetchone()
            if exists is None:
                return ()
            return self._dependency_ids_in_connection(connection, task_id)

    @staticmethod
    def _block_failed_dependencies(connection: Any, now: str) -> None:
        while True:
            rows = connection.execute(
                """SELECT child.id, child.attempts, edge.depends_on_task_id, parent.state AS parent_state
                   FROM agent_tasks AS child
                   JOIN agent_task_dependencies AS edge ON edge.task_id = child.id
                   JOIN agent_tasks AS parent ON parent.id = edge.depends_on_task_id
                   WHERE child.state IN ('queued', 'retry_wait')
                     AND parent.state IN ('failed', 'blocked', 'uncertain', 'cancelled')
                   ORDER BY child.id, edge.depends_on_task_id"""
            ).fetchall()
            if not rows:
                return
            seen: set[str] = set()
            for row in rows:
                if row["id"] in seen:
                    continue
                seen.add(row["id"])
                changed = connection.execute(
                    """UPDATE agent_tasks SET state = 'blocked', completed_at = ?,
                           error_code = 'dependency_not_satisfied',
                           error_summary = 'Tarefa prerequisito terminou sem sucesso.'
                       WHERE id = ? AND state IN ('queued', 'retry_wait')""",
                    (now, row["id"]),
                ).rowcount
                if changed:
                    AgentQueue._event(connection, row["id"], "dependency_blocked", row["attempts"], {
                        "depends_on_task_id": row["depends_on_task_id"],
                        "dependency_state": row["parent_state"],
                    })

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
            self._block_failed_dependencies(connection, now_iso)
            if task_id:
                row = connection.execute(
                    """SELECT task.* FROM agent_tasks AS task
                       WHERE task.id = ? AND task.state IN ('queued', 'retry_wait')
                         AND task.available_at <= ?
                         AND NOT EXISTS (
                             SELECT 1 FROM agent_task_dependencies AS edge
                             JOIN agent_tasks AS prerequisite ON prerequisite.id = edge.depends_on_task_id
                             WHERE edge.task_id = task.id AND prerequisite.state <> 'succeeded'
                         )""",
                    (task_id, now_iso),
                ).fetchone()
            else:
                row = connection.execute(
                    """SELECT task.* FROM agent_tasks AS task
                       WHERE task.state IN ('queued', 'retry_wait') AND task.available_at <= ?
                         AND NOT EXISTS (
                             SELECT 1 FROM agent_task_dependencies AS edge
                             JOIN agent_tasks AS prerequisite ON prerequisite.id = edge.depends_on_task_id
                             WHERE edge.task_id = task.id AND prerequisite.state <> 'succeeded'
                         )
                       ORDER BY task.available_at, task.created_at, task.id LIMIT 1""",
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

    def recover_completed_external_output(
        self,
        task_id: str,
        result: Mapping[str, Any],
        *,
        response_sha256: str,
        now: datetime | str | None = None,
    ) -> bool:
        """Adopt an already completed SIWC response after a local result-envelope bug.

        This narrow transition never dispatches or repeats the provider call. The
        caller must verify the persisted response bytes, role schema, evidence
        references, and result envelope before invoking it.
        """
        expected_error_code = "siwc_result_envelope_invalid"
        if not isinstance(response_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", response_sha256):
            raise ValueError("response_sha256 precisa ser SHA-256 hexadecimal minúsculo.")
        artifact_ref = result.get("artifact_ref") if isinstance(result, Mapping) else None
        if (not isinstance(artifact_ref, Mapping)
                or artifact_ref.get("sha256") != response_sha256
                or result.get("output_hash") != response_sha256):
            raise ValueError("Resultado recuperado precisa apontar ao hash exato da resposta externa.")
        _assert_no_credentials(result, "recovered_result")
        encoded = json_dumps(dict(result))
        if len(encoded.encode("utf-8")) > 1_000_000:
            raise ValueError("Resultado recuperado excede o limite local de 1 MB.")
        now_iso = _lease_iso(now)
        with self.store.transaction() as connection:
            row = connection.execute("SELECT * FROM agent_tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                return False
            if (row["state"] != "blocked" or row["error_code"] != expected_error_code
                    or not row["external_request_started"] or row["attempts"] != 1
                    or row["max_attempts"] != 1 or row["result_json"] is not None):
                return False
            updated = connection.execute(
                """UPDATE agent_tasks SET state = 'succeeded', result_json = ?, completed_at = ?,
                       error_code = NULL, error_summary = NULL
                   WHERE id = ? AND state = 'blocked' AND error_code = ?
                     AND external_request_started = 1 AND attempts = 1 AND result_json IS NULL""",
                (encoded, now_iso, task_id, expected_error_code),
            )
            if updated.rowcount != 1:
                return False
            self._event(connection, task_id, "external_output_recovered", row["attempts"], {
                "original_error_code": expected_error_code,
                "response_sha256": response_sha256,
                "result_sha256": stable_hash(encoded),
                "recovery": "validated_persisted_response_no_provider_retry",
            })
            return True

    def reconcile_completed_research_handoff(
        self,
        task_id: str,
        result: Mapping[str, Any],
        *,
        response_sha256: str,
    ) -> bool:
        """Attach one validated Motor request to an already completed writer result.

        This transition is for a local mediation bug discovered after a completed
        external response. It preserves the task attempt and response hash and
        changes only the previously missing research handoff.
        """
        if not isinstance(response_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", response_sha256):
            raise ValueError("response_sha256 precisa ser SHA-256 hexadecimal minúsculo.")
        _assert_no_credentials(result, "reconciled_result")
        encoded = json_dumps(dict(result))
        if len(encoded.encode("utf-8")) > 1_000_000:
            raise ValueError("Resultado reconciliado excede o limite local de 1 MB.")
        artifact_ref = result.get("artifact_ref") if isinstance(result, Mapping) else None
        request = result.get("requested_research") if isinstance(result, Mapping) else None
        if (
            not isinstance(artifact_ref, Mapping)
            or artifact_ref.get("sha256") != response_sha256
            or result.get("output_hash") != response_sha256
            or not isinstance(request, Mapping)
            or request.get("parent_task_id") != task_id
            or not isinstance(request.get("request_id"), str)
        ):
            raise ValueError("Handoff reconciliado precisa apontar à resposta e à tarefa de origem exatas.")
        with self.store.transaction() as connection:
            row = connection.execute("SELECT * FROM agent_tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                return False
            old_result = json.loads(row["result_json"]) if row["result_json"] else None
            payload = json.loads(row["payload_json"])
            envelope = payload.get("agent_task_envelope") if isinstance(payload, Mapping) else None
            policy = envelope.get("research_mediation_policy") if isinstance(envelope, Mapping) else None
            if (
                row["task_type"] != "agent.role.persona_writer"
                or row["state"] != "succeeded"
                or not row["external_request_started"]
                or not isinstance(old_result, Mapping)
                or old_result.get("requested_research") is not None
                or not isinstance(envelope, Mapping)
                or request.get("story_id") != envelope.get("story_id")
                or request.get("requester_role_id") != envelope.get("role_id")
                or request.get("requester_persona_id") != envelope.get("persona_id")
                or not isinstance(policy, Mapping)
                or request.get("story_revision_id") != policy.get("story_revision_id")
            ):
                return False
            old_artifact = old_result.get("artifact_ref")
            if not isinstance(old_artifact, Mapping) or old_artifact.get("sha256") != response_sha256:
                return False
            expected_result = dict(old_result)
            expected_result["requested_research"] = dict(request)
            if dict(result) != expected_result:
                return False
            updated = connection.execute(
                "UPDATE agent_tasks SET result_json = ? WHERE id = ? AND state = 'succeeded' AND external_request_started = 1",
                (encoded, task_id),
            )
            if updated.rowcount != 1:
                return False
            self._event(connection, task_id, "completed_research_handoff_reconciled", row["attempts"], {
                "response_sha256": response_sha256,
                "request_id": request["request_id"],
                "result_sha256": stable_hash(encoded),
                "provider_calls_repeated": 0,
            })
            return True

    def reopen_pre_external_contract_failure(self, task_id: str) -> bool:
        """Allow one corrected dispatch when a task was blocked before any provider call."""
        expected_error_code = "agent_contract_invalid"
        with self.store.transaction() as connection:
            row = connection.execute("SELECT * FROM agent_tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                return False
            if (row["task_type"] != "agent.role.persona_writer" or row["state"] != "blocked"
                    or row["error_code"] != expected_error_code or row["external_request_started"]
                    or row["attempts"] != 1 or row["max_attempts"] != 1 or row["result_json"] is not None):
                return False
            updated = connection.execute(
                """UPDATE agent_tasks SET state = 'queued', max_attempts = 2,
                       completed_at = NULL, error_code = NULL, error_summary = NULL
                   WHERE id = ? AND state = 'blocked' AND error_code = ?
                     AND external_request_started = 0 AND attempts = 1
                     AND max_attempts = 1 AND result_json IS NULL""",
                (task_id, expected_error_code),
            )
            if updated.rowcount != 1:
                return False
            self._event(connection, task_id, "pre_external_contract_reopened", row["attempts"], {
                "original_error_code": expected_error_code,
                "external_request_started": False,
                "next_attempt": 2,
                "provider_calls_repeated": 0,
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

    def create_daily_window_set(
        self,
        *,
        schedule_group_id: str,
        task_type: str,
        payload: Mapping[str, Any],
        profile: AgentProfile,
        executor_id: str,
        local_times: Sequence[str],
        domain_quotas: Mapping[str, int],
        timezone_name: str = "America/Sao_Paulo",
        misfire_policy: str = "skip",
        misfire_grace_seconds: int = 300,
        start_at: datetime | str | None = None,
    ) -> list[str]:
        """Create 3–6 disabled local daily Radar windows on the existing queue."""
        if not isinstance(schedule_group_id, str) or not schedule_group_id.strip() or len(schedule_group_id) > 128:
            raise ValueError("Identificador do grupo de agendas é obrigatório e deve ter até 128 caracteres.")
        if not isinstance(task_type, str) or not task_type.startswith("radar."):
            raise ValueError("Janelas diárias são reservadas a tarefas radar.*.")
        if not isinstance(executor_id, str) or not executor_id.strip():
            raise ValueError("Executor da agenda é obrigatório.")
        if len(local_times) < 3 or len(local_times) > 6:
            raise ValueError("Configure de 3 a 6 janelas locais por dia.")
        normalized_times = [value.strip() if isinstance(value, str) else value for value in local_times]
        for local_time in normalized_times:
            parse_local_time(local_time)
        if len(set(normalized_times)) != len(normalized_times):
            raise ValueError("Horários locais duplicados no grupo de agendas.")
        load_timezone(timezone_name)
        if misfire_policy not in {"skip", "run_once"}:
            raise ValueError("Política de atraso deve ser skip ou run_once.")
        if (
            isinstance(misfire_grace_seconds, bool)
            or not isinstance(misfire_grace_seconds, int)
            or not 0 <= misfire_grace_seconds <= 86_400
        ):
            raise ValueError("Tolerância de atraso deve ficar entre 0 e 86400 segundos.")
        quotas = normalize_domain_quotas(domain_quotas)
        if "radar_collection_policy" in payload:
            raise ValueError("radar_collection_policy é reservado à configuração da agenda.")
        base_payload = dict(payload)
        _assert_no_credentials(base_payload)
        group_id = schedule_group_id.strip()
        _assert_no_credentials(group_id, "schedule_group_id")
        now_instant = _as_utc(start_at)
        now_value = _iso(now_instant)
        schedule_ids: list[str] = []
        with self.store.transaction() as connection:
            if connection.execute(
                "SELECT 1 FROM agent_schedules WHERE schedule_group_id=? LIMIT 1",
                (group_id,),
            ).fetchone() is not None:
                raise ValueError("Identificador de grupo de agendas já está em uso.")
            for local_time in sorted(normalized_times):
                schedule_id = f"{group_id}:{local_time.replace(':', '')}"
                next_run = _iso(next_daily_window_utc(
                    local_time, timezone_name, now_instant, include_equal=True
                ))
                task_payload = {
                    **base_payload,
                    "radar_collection_policy": {
                        "schedule_group_id": group_id,
                        "window_local_time": local_time,
                        "timezone": timezone_name,
                        "domain_quotas": quotas,
                        "quota_period": "local_day",
                        "dry_run": True,
                    },
                }
                connection.execute(
                    """INSERT INTO agent_schedules
                       (id, task_type, payload_json, profile_id, profile_version,
                        profile_hash, executor_id, interval_seconds, timezone,
                        misfire_policy, enabled, next_run_at, created_at, updated_at,
                        schedule_group_id, schedule_kind, local_time,
                        misfire_grace_seconds, domain_quotas_json, dry_run)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 86400, ?, ?, 0, ?, ?, ?, ?,
                               'daily_window', ?, ?, ?, 1)""",
                    (schedule_id, task_type, json_dumps(task_payload), profile.profile_id,
                     profile.version, profile.content_hash, executor_id, timezone_name,
                     misfire_policy, next_run, now_value, now_value, group_id, local_time,
                     misfire_grace_seconds, json_dumps(quotas)),
                )
                connection.execute(
                    """INSERT INTO audit_events
                       (occurred_at, entity_type, entity_id, action, actor, source,
                        before_json, after_json)
                       VALUES (?, 'agent_schedule', ?, 'created', 'operator', 'scheduler',
                               NULL, ?)""",
                    (now_value, schedule_id, json_dumps({
                        "enabled": False, "schedule_group_id": group_id,
                        "schedule_kind": "daily_window", "local_time": local_time,
                        "timezone": timezone_name, "misfire_policy": misfire_policy,
                        "misfire_grace_seconds": misfire_grace_seconds,
                        "domain_quotas": quotas, "dry_run": True,
                        "executor_id": executor_id,
                    })),
                )
                schedule_ids.append(schedule_id)
        return schedule_ids

    def set_schedule_enabled(
        self, schedule_id: str, enabled: bool, *, now: datetime | str | None = None
    ) -> None:
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM agent_schedules WHERE id = ?", (schedule_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Agenda inexistente.")
            if row["schedule_kind"] == "daily_window":
                raise ValueError("Janelas diárias devem ser pausadas ou retomadas pelo grupo completo.")
            now_instant = _as_utc(now)
            now_value = _iso(now_instant)
            next_run = now_value
            connection.execute(
                """UPDATE agent_schedules SET enabled = ?, next_run_at = ?, updated_at = ?
                   WHERE id = ?""",
                (int(enabled), next_run, now_value, schedule_id),
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

    def set_schedule_group_enabled(
        self, schedule_group_id: str, enabled: bool, *, now: datetime | str | None = None
    ) -> list[str]:
        with self.store.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM agent_schedules WHERE schedule_group_id=? ORDER BY local_time, id",
                (schedule_group_id,),
            ).fetchall()
            if not rows:
                raise ValueError("Grupo de agendas inexistente.")
            now_instant = _as_utc(now)
            now_value = _iso(now_instant)
            updated_ids: list[str] = []
            for row in rows:
                next_run = now_value
                if enabled and row["schedule_kind"] == "daily_window":
                    next_run = _iso(next_daily_window_utc(
                        row["local_time"], row["timezone"], now_instant, include_equal=True
                    ))
                connection.execute(
                    """UPDATE agent_schedules SET enabled=?, next_run_at=?, updated_at=?
                       WHERE id=?""",
                    (int(enabled), next_run, now_value, row["id"]),
                )
                connection.execute(
                    """INSERT INTO audit_events
                       (occurred_at, entity_type, entity_id, action, actor, source,
                        before_json, after_json)
                       VALUES (?, 'agent_schedule', ?, ?, 'operator', 'scheduler', ?, ?)""",
                    (now_value, row["id"], "enabled" if enabled else "disabled",
                     json_dumps({"enabled": bool(row["enabled"]), "schedule_group_id": schedule_group_id}),
                     json_dumps({"enabled": bool(enabled), "schedule_group_id": schedule_group_id,
                                 "next_run_at": next_run})),
                )
                updated_ids.append(row["id"])
            return updated_ids

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
                "schedule_group_id": row["schedule_group_id"],
                "schedule_kind": row["schedule_kind"], "local_time": row["local_time"],
                "misfire_grace_seconds": row["misfire_grace_seconds"],
                "domain_quotas": json.loads(row["domain_quotas_json"]),
                "dry_run": bool(row["dry_run"]),
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
                if schedule["schedule_kind"] == "daily_window":
                    lateness = max(0.0, (instant - due).total_seconds())
                    missed = lateness > int(schedule["misfire_grace_seconds"])
                    next_run = next_daily_window_utc(
                        schedule["local_time"], schedule["timezone"], instant,
                        include_equal=False,
                    )
                    if missed and schedule["misfire_policy"] == "skip":
                        connection.execute(
                            """UPDATE agent_schedules SET next_run_at=?, updated_at=?
                               WHERE id=?""",
                            (_iso(next_run), now_iso, schedule["id"]),
                        )
                        connection.execute(
                            """INSERT INTO audit_events
                               (occurred_at, entity_type, entity_id, action, actor, source, after_json)
                               VALUES (?, 'agent_schedule', ?, 'missed_run_skipped',
                                       'scheduler', 'scheduler', ?)""",
                            (now_iso, schedule["id"], json_dumps({
                                "missed_policy": "skip", "due_at": _iso(due),
                                "next_run_at": _iso(next_run),
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
                        """UPDATE agent_schedules SET next_run_at=?, last_enqueued_at=?,
                           updated_at=? WHERE id=?""",
                        (_iso(next_run), now_iso, now_iso, schedule["id"]),
                    )
                    continue
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

    @property
    def queue(self) -> AgentQueue:
        """Shared durable queue for executor adapters that validate task lineage."""
        return self._queue

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
        persona_instruction_resolver: Callable[[Any], str | None] | None = None,
        deterministic_task_routes: Mapping[str, str] | None = None,
        result_router: Callable[[AgentTask], None] | None = None,
    ):
        self.queue = queue
        self.executors = dict(executors)
        self.profiles = dict(profiles)
        self.lease_seconds = lease_seconds
        self.role_catalog = role_catalog
        self.persona_instruction_resolver = persona_instruction_resolver
        self.deterministic_task_routes = dict(deterministic_task_routes or {})
        self.result_router = result_router

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

        if self.role_catalog is not None and not task.task_type.startswith("agent.role."):
            expected_executor = self.deterministic_task_routes.get(task.task_type)
            if expected_executor is None or expected_executor != task.executor_id:
                return report_failure(TaskFailure(
                    "task_route_unregistered",
                    "Tipo determinístico sem rota local explícita no registro do dispatcher.",
                    blocked=True,
                ))

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
        if self.role_catalog is not None and task.task_type.startswith("agent.role."):
            try:
                from .agent_contracts import envelope_from_payload

                task_envelope = envelope_from_payload(task.payload)
                if task_envelope.task_id != task.task_id:
                    raise ValueError("task_id do envelope diverge da fila")
                if task.task_type != f"agent.role.{task_envelope.role_id}":
                    raise ValueError("tipo da fila diverge do role_id")
                persona_instructions = None
                if (
                    task_envelope.role_id == "persona_writer"
                    and self.persona_instruction_resolver is not None
                ):
                    try:
                        persona_instructions = self.persona_instruction_resolver(task_envelope)
                    except Exception as error:
                        raise ValueError("resolvedor de instruções de persona indisponível") from error
                invocation_context = self.role_catalog.prepare_invocation(
                    task_envelope,
                    input_payload=task.payload.get("input"),
                    research_packet=task.payload.get("research_packet"),
                    persona_instructions=persona_instructions,
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
            if self.result_router is not None:
                completed_task = self.queue.get(task.task_id)
                if completed_task is not None:
                    try:
                        self.result_router(completed_task)
                    except Exception:
                        return DispatchOutcome(task.task_id, "succeeded", "workflow_route_pending")
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
