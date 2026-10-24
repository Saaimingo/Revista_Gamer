"""Small local SQLite index of synthetic layout-reference descriptions."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from .contracts import ContractError, validate_layout_reference, sha256_json


class LayoutReferenceIndex:
    """Index functional descriptions only; never stores image or scan bytes."""

    def __init__(self, database_path: Path):
        self.database_path = database_path.expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS layout_references (
                    reference_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS layout_index_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _search_terms(payload: Mapping[str, Any]) -> set[str]:
        """Expose functional tags and searchable metadata facets without indexing images."""
        terms = {
            tag.casefold()
            for tag in payload.get("tags", [])
            if isinstance(tag, str) and tag.strip()
        }
        for field, prefix in (
            ("composition_function", "function"),
            ("era", "era"),
            ("orientation", "orientation"),
            ("source_publication", "publication"),
            ("source_year", "year"),
            ("source_page", "source-page"),
            ("position", "position"),
            ("rights_scope", "rights"),
            ("access_scope", "access"),
        ):
            value = payload.get(field)
            if value is not None and str(value).strip():
                normalized = str(value).strip().casefold()
                terms.add(f"{prefix}:{normalized}")
                terms.add(normalized)
        for affordance in payload.get("digital_affordances", []):
            if isinstance(affordance, str) and affordance.strip():
                normalized = affordance.strip().casefold()
                terms.add(f"affordance:{normalized}")
                terms.add(normalized)
        for media_role in payload.get("media_roles", []):
            if isinstance(media_role, str) and media_role.strip():
                normalized = media_role.strip().casefold()
                terms.add(f"media:{normalized}")
                terms.add(normalized)
        for field in (
            "title", "description", "editorial_purpose", "problem_solved",
            "strengths", "limitations", "digital_adaptation",
        ):
            value = payload.get(field)
            if isinstance(value, str):
                tokens = re.findall(r"[\w-]+", value.casefold())
                if field == "limitations":
                    terms.update(f"limit:{token}" for token in tokens if len(token) >= 3)
                else:
                    terms.update(token for token in tokens if len(token) >= 3)
        return terms

    def add_references(self, references: Iterable[Mapping[str, Any]]) -> None:
        rows: list[tuple[str, int, str, str, str]] = []
        for reference in references:
            validated = validate_layout_reference(reference)
            payload = validated["payload"]
            if payload.get("source_type") != "synthetic_fixture":
                raise ContractError("O índice Fase 0 só aceita referências sintéticas.")
            rows.append((
                payload["reference_id"],
                validated["revision"],
                validated["content_sha256"],
                json.dumps(sorted(self._search_terms(payload)), ensure_ascii=False, separators=(",", ":")),
                json.dumps(validated, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            ))
        with self._connect() as connection:
            connection.executemany(
                """INSERT INTO layout_references
                   (reference_id, revision, content_sha256, tags_json, payload_json)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(reference_id) DO UPDATE SET
                     revision=excluded.revision,
                     content_sha256=excluded.content_sha256,
                     tags_json=excluded.tags_json,
                     payload_json=excluded.payload_json""",
                rows,
            )
            connection.execute(
                """INSERT INTO layout_index_meta(key, value) VALUES ('schema_version', 'LayoutReferenceIndex.v0')
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value"""
            )

    def references(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM layout_references ORDER BY reference_id"
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def fingerprint(self) -> str:
        references = self.references()
        return sha256_json([
            {"reference_id": row["payload"]["reference_id"],
             "content_sha256": row["content_sha256"]}
            for row in references
        ])

    def search(self, tags: Iterable[str], *, limit: int = 3) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit precisa ser positivo.")
        wanted = {tag.strip().casefold() for tag in tags if isinstance(tag, str) and tag.strip()}
        if not wanted:
            return []
        ranked: list[tuple[int, str, dict[str, Any]]] = []
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT tags_json, payload_json FROM layout_references"
            ).fetchall()
        for row in rows:
            reference = json.loads(row["payload_json"])
            payload = reference["payload"]
            reference_tags = {tag.casefold() for tag in json.loads(row["tags_json"])}
            score = len(wanted.intersection(reference_tags))
            if score:
                ranked.append((score, payload["reference_id"], reference))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        return [row[2] for row in ranked[:limit]]
