"""End-to-end checks for the offline editorial simulation."""

from __future__ import annotations

import re
import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from unittest.mock import patch

from motor_editorial.db import SCHEMA_VERSION, Store
from motor_editorial.domain import InvalidApproval, InvalidTransition
from motor_editorial.web import create_server
from motor_editorial.workflow import APPROVAL_PHRASE, Motor


class MotorWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = Store(self.root / "motor.sqlite3", self.root / "artifacts")
        self.motor = Motor(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_to_preview(self):
        result = self.motor.run_demo()
        self.assertEqual(result.status, "recoverable_failure")
        resumed = self.motor.run_demo()
        self.assertEqual(resumed.status, "awaiting_approval")
        self.assertIsNotNone(resumed.edition_id)
        return resumed

    def motor_with_fixture(self, edit_fixture, **motor_options):
        fixture_path = self.root / "custom-demo.json"
        data = json.loads(
            (Path(__file__).parents[1] / "fixtures" / "demo.json").read_text(
                encoding="utf-8"
            )
        )
        edit_fixture(data)
        fixture_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return Motor(
            self.store,
            fixture_path,
            research_failures_to_inject=0,
            **motor_options,
        )

    def test_full_demo_is_offline_and_enforces_editorial_and_media_gates(self) -> None:
        # The deterministic pipeline must not open a network socket.
        with patch("socket.socket", side_effect=AssertionError("socket access is forbidden")):
            result = self.motor.run_demo()
            self.assertEqual(result.status, "recoverable_failure")
            result = self.motor.run_demo()
        self.assertEqual(result.status, "awaiting_approval")
        self.assertEqual(result.edition_id, "edition-demo-motor-v0.1")

        counts = self.store.counts()
        self.assertEqual(counts["items"], 4)
        self.assertEqual(counts["duplicates"], 1)
        self.assertEqual(counts["stories"], 1)
        self.assertEqual(counts["revisions"], 2)
        self.assertEqual(counts["editions"], 1)

        detail = self.store.story_detail(self.store.list_stories()[0]["id"])
        self.assertEqual(detail["story"]["state"], "awaiting_human_approval")
        self.assertEqual([row["version"] for row in detail["revisions"]], [1, 2])
        self.assertEqual([row["review_approved"] for row in detail["revisions"]], [0, 1])
        self.assertIn("sem referência", detail["revisions"][0]["findings_json"])
        self.assertTrue(detail["research"])

        media_decisions = {row["permission_status"]: row for row in detail["media"]}
        self.assertEqual(media_decisions["permitido"]["decision"], "include")
        self.assertEqual(media_decisions["pendente"]["decision"], "placeholder")

        preview_path = self.store.safe_artifact_path(
            self.store.get_edition(result.edition_id)["preview_path"]
        )
        preview = preview_path.read_text(encoding="utf-8")
        self.assertIn("SIMULAÇÃO — NÃO PUBLICAR", preview)
        self.assertIn("Placeholder interno", preview)
        self.assertIn("Ativo fictício com permissão pendente", preview)
        self.assertIn("ARTE ORIGINAL DE TESTE", preview)
        self.assertNotIn('data-asset-id="asset-pending-demo"', preview)

        # A new Store instance sees the same persisted execution state.
        reopened = Store(self.root / "motor.sqlite3", self.root / "artifacts")
        self.assertEqual(reopened.counts(), counts)
        self.assertEqual(reopened.get_run("demo-motor-v0.1")["status"], "awaiting_approval")

    def test_repeat_after_preview_is_idempotent_and_invalid_jumps_are_rejected(self) -> None:
        result = self.run_to_preview()
        counts_before = self.store.counts()
        repeated = self.motor.run_demo()
        self.assertEqual(repeated.status, "awaiting_approval")
        self.assertEqual(repeated.edition_id, result.edition_id)
        self.assertEqual(self.store.counts(), counts_before)

        story = self.store.list_stories()[0]
        with self.assertRaises(InvalidTransition):
            self.store.transition_story(story["id"], "drafted")
        with self.assertRaises(InvalidApproval):
            self.motor.approve_internally("missing-edition", "Diretor", APPROVAL_PHRASE)

    def test_approval_requires_currently_reviewed_revision_and_explicit_confirmation(self) -> None:
        result = self.run_to_preview()
        edition_id = result.edition_id
        with self.assertRaises(InvalidApproval):
            self.motor.approve_internally(edition_id, "Diretor", "sim")
        with self.assertRaises(InvalidApproval):
            self.motor.approve_internally(edition_id, "  ", APPROVAL_PHRASE)
        self.assertEqual(self.store.get_edition(edition_id)["status"], "awaiting_human_approval")

        # A newer, unreviewed version invalidates approval of the old review.
        story = self.store.list_stories()[0]
        with self.store.transaction() as connection:
            connection.execute(
                "INSERT INTO article_revisions "
                "(id, story_id, version, content, author_role, status, created_at) "
                "VALUES ('revision-test-v3', ?, 3, 'versão de teste', 'teste', 'draft', '2026-10-01')",
                (story["id"],),
            )
            connection.execute(
                "UPDATE stories SET current_revision_number = 3 WHERE id = ?", (story["id"],)
            )
        with self.assertRaises(InvalidApproval):
            self.motor.approve_internally(edition_id, "Diretor", APPROVAL_PHRASE)
        with self.store.transaction() as connection:
            connection.execute(
                "UPDATE stories SET current_revision_number = 2 WHERE id = ?", (story["id"],)
            )

        self.motor.approve_internally(edition_id, "Diretor", APPROVAL_PHRASE)
        self.assertEqual(self.store.get_edition(edition_id)["status"], "approved_internally")
        self.assertEqual(self.store.get_run("demo-motor-v0.1")["status"], "approved_internally")
        self.assertEqual(self.store.get_story(story["id"])["state"], "approved_internally")
        events = self.store.list_events(edition_id)
        self.assertEqual(events[-1]["action"], "approved_internally")
        self.assertEqual(events[-1]["actor"], "Diretor")

    def test_retry_limit_stops_without_infinite_retries(self) -> None:
        motor = Motor(self.store, research_failures_to_inject=100, max_attempts=3)
        self.assertEqual(motor.run_demo().status, "recoverable_failure")
        self.assertEqual(motor.run_demo().status, "recoverable_failure")
        self.assertEqual(motor.run_demo().status, "failed_intervention")
        attempts_before = self.store.counts()["attempts"]
        self.assertEqual(motor.run_demo().status, "failed_intervention")
        self.assertEqual(self.store.counts()["attempts"], attempts_before)
        with closing(self.store.connect()) as connection:
            research_attempts = connection.execute(
                "SELECT COUNT(*) FROM execution_attempts WHERE stage = 'research'"
            ).fetchone()[0]
        self.assertEqual(research_attempts, 3)

    def test_permitted_asset_for_wrong_usage_mode_is_replaced_before_preview(self) -> None:
        def change_usage(data):
            next(asset for asset in data["assets"] if asset["id"] == "asset-original-demo")[
                "usage_mode"
            ] = "commercial_advertising"

        motor = self.motor_with_fixture(change_usage)
        result = motor.run_demo()
        self.assertEqual(result.status, "awaiting_approval")
        story = self.store.list_stories()[0]
        decisions = {
            row["asset_id"]: row for row in self.store.story_detail(story["id"])["media"]
        }
        decision = decisions["asset-original-demo"]
        self.assertEqual(decision["permission_status"], "permitido")
        self.assertEqual(decision["usage_mode"], "commercial_advertising")
        self.assertEqual(decision["decision"], "placeholder")
        self.assertIn("modalidade", decision["reason"])

        preview_path = self.store.safe_artifact_path(
            self.store.get_edition(result.edition_id)["preview_path"]
        )
        preview = preview_path.read_text(encoding="utf-8")
        self.assertNotIn('data-asset-id="asset-original-demo"', preview)
        self.assertNotIn("ARTE ORIGINAL DE TESTE", preview)
        self.assertIn("commercial_advertising", preview)

        with self.store.transaction() as connection:
            connection.execute(
                "UPDATE stories SET state = 'reviewed' WHERE id = ?", (story["id"],)
            )
            connection.execute(
                "UPDATE media_decisions SET decision = 'include' "
                "WHERE story_id = ? AND asset_id = 'asset-original-demo'",
                (story["id"],),
            )
        with self.assertRaises(InvalidTransition):
            self.store.transition_story(story["id"], "media_checked")

    def test_optional_pending_asset_is_omitted_without_blocking_story(self) -> None:
        def make_optional(data):
            next(
                asset for asset in data["story_assets"]
                if asset["asset_id"] == "asset-pending-demo"
            )["required"] = False

        motor = self.motor_with_fixture(make_optional)
        result = motor.run_demo()
        self.assertEqual(result.status, "awaiting_approval")
        story = self.store.list_stories()[0]
        decisions = {
            row["asset_id"]: row for row in self.store.story_detail(story["id"])["media"]
        }
        pending = decisions["asset-pending-demo"]
        self.assertEqual(pending["required"], 0)
        self.assertEqual(pending["decision"], "blocked")
        self.assertIn("opcional omitido", pending["reason"])

        preview_path = self.store.safe_artifact_path(
            self.store.get_edition(result.edition_id)["preview_path"]
        )
        preview = preview_path.read_text(encoding="utf-8")
        self.assertNotIn("Placeholder interno", preview)
        self.assertIn("omitido:", preview)
        self.assertIn("Ativo fictício com permissão pendente", preview)

    def test_revoked_permission_refreshes_preview_and_requires_a_new_approval_action(self) -> None:
        result = self.run_to_preview()
        with self.store.transaction() as connection:
            connection.execute(
                "UPDATE media_assets SET permission_status = 'bloqueado' "
                "WHERE id = 'asset-original-demo'"
            )

        with self.assertRaisesRegex(InvalidApproval, "permissão ou modalidade.*mudou"):
            self.motor.approve_internally(
                result.edition_id, "Diretor", APPROVAL_PHRASE
            )
        self.assertEqual(
            self.store.get_edition(result.edition_id)["status"], "awaiting_human_approval"
        )
        story = self.store.list_stories()[0]
        original = next(
            row for row in self.store.story_detail(story["id"])["media"]
            if row["asset_id"] == "asset-original-demo"
        )
        self.assertEqual(original["decision"], "placeholder")
        self.assertIn("bloqueado", original["reason"])

        preview_path = self.store.safe_artifact_path(
            self.store.get_edition(result.edition_id)["preview_path"]
        )
        refreshed_preview = preview_path.read_text(encoding="utf-8")
        self.assertNotIn('data-asset-id="asset-original-demo"', refreshed_preview)
        self.assertNotIn("ARTE ORIGINAL DE TESTE", refreshed_preview)
        self.assertIn("bloqueado", refreshed_preview)
        story_events = self.store.list_events(story["id"])
        self.assertTrue(
            any(event["action"] == "media_permission_revalidated" for event in story_events)
        )
        edition_events = self.store.list_events(result.edition_id)
        self.assertTrue(
            any(
                event["action"] == "preview_refreshed_after_media_change"
                for event in edition_events
            )
        )

        # A later deliberate approval can proceed after the updated preview is reviewed.
        self.motor.approve_internally(result.edition_id, "Diretor", APPROVAL_PHRASE)
        self.assertEqual(
            self.store.get_edition(result.edition_id)["status"], "approved_internally"
        )

    def test_second_rejected_revision_records_terminal_intervention(self) -> None:
        motor = Motor(
            self.store,
            research_failures_to_inject=0,
            force_v2_review_failure=True,
        )
        result = motor.run_demo()
        self.assertEqual(result.status, "failed_intervention")
        self.assertIn("reprovada novamente", result.message)
        run = self.store.get_run("demo-motor-v0.1")
        self.assertEqual(run["status"], "failed_intervention")

        story = self.store.list_stories()[0]
        detail = self.store.story_detail(story["id"])
        self.assertEqual(detail["story"]["state"], "blocked_by_review")
        self.assertEqual(detail["story"]["current_revision_number"], 2)
        self.assertEqual(detail["revisions"][-1]["review_approved"], 0)
        self.assertTrue(
            any(
                event["action"] == "review_correction_limit_reached"
                for event in detail["events"]
            )
        )
        counts = self.store.counts()
        self.assertEqual(motor.run_demo().status, "failed_intervention")
        self.assertEqual(self.store.counts(), counts)

    def test_fixture_with_multiple_selectable_topics_is_rejected_before_writing(self) -> None:
        def add_second_story(data):
            data["items"].append({
                "id": "news-second-topic",
                "source_id": "source-community",
                "source_identifier": "mock://noticias/comunidade/segundo-topico",
                "title": "Nota fictícia de outro tópico selecionável",
                "published_at": "2026-10-04T10:00:00Z",
                "summary": "Conteúdo inventado para testar o limite de uma pauta por edição.",
                "topic_key": "second-selectable-topic",
                "relevance": True,
            })
            data["stories"].append({
                "topic_key": "second-selectable-topic",
                "question": "Qual é o segundo tópico fictício?",
            })

        motor = self.motor_with_fixture(add_second_story)
        with self.assertRaisesRegex(ValueError, "mais de uma pauta selecionável"):
            motor.run_demo()
        self.assertEqual(self.store.counts()["items"], 0)
        self.assertIsNone(self.store.get_run("demo-motor-v0.1"))

    def test_schema_v1_migrates_media_decision_required_flag(self) -> None:
        legacy_db = self.root / "legacy.sqlite3"
        with closing(sqlite3.connect(legacy_db)) as connection:
            with connection:
                connection.execute(
                    """CREATE TABLE media_decisions (
                           id TEXT PRIMARY KEY,
                           story_id TEXT NOT NULL,
                           asset_id TEXT NOT NULL,
                           decision TEXT NOT NULL CHECK (decision IN (
                               'include', 'placeholder', 'blocked'
                           )),
                           reason TEXT NOT NULL,
                           created_at TEXT NOT NULL,
                           UNIQUE(story_id, asset_id)
                       )"""
                )
                connection.execute(
                    "INSERT INTO media_decisions VALUES "
                    "('old-decision', 'old-story', 'old-asset', 'placeholder', 'legacy', '2026-10-01')"
                )
                connection.execute("PRAGMA user_version = 1")

        migrated = Store(legacy_db, self.root / "legacy-artifacts")
        with closing(migrated.connect()) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
            column_names = {
                row["name"] for row in connection.execute("PRAGMA table_info(media_decisions)")
            }
            self.assertIn("required", column_names)
            self.assertEqual(
                connection.execute(
                    "SELECT required FROM media_decisions WHERE id = 'old-decision'"
                ).fetchone()[0],
                1,
            )

    def test_panel_serves_database_preview_and_only_internal_actions(self) -> None:
        result = self.run_to_preview()
        server = create_server(self.motor, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            self.assertEqual(server.server_address[0], "127.0.0.1")
            with urlopen(base_url + "/", timeout=3) as response:
                dashboard = response.read().decode("utf-8")
            self.assertIn("Painel local", dashboard)
            self.assertIn("Aguardando aprovação humana", dashboard)
            csrf = re.search(r'name="csrf" value="([^"]+)"', dashboard).group(1)

            story = self.store.list_stories()[0]
            with urlopen(base_url + "/stories/" + story["id"], timeout=3) as response:
                detail = response.read().decode("utf-8")
            self.assertIn("Versão 1 — Devolvida para correção", detail)
            self.assertIn("Direitos de mídia", detail)

            with urlopen(
                base_url + f"/editions/{result.edition_id}/preview", timeout=3
            ) as response:
                preview = response.read().decode("utf-8")
            self.assertIn("SIMULAÇÃO — NÃO PUBLICAR", preview)

            form = urlencode({
                "csrf": csrf,
                "actor": "Diretoria de teste",
                "confirmation": APPROVAL_PHRASE,
            }).encode("utf-8")
            request = Request(
                base_url + f"/editions/{result.edition_id}/approve",
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urlopen(request, timeout=3) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(
                self.store.get_edition(result.edition_id)["status"], "approved_internally"
            )

            publish_request = Request(
                base_url + "/publish",
                data=urlencode({"csrf": csrf}).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as no_publish:
                urlopen(publish_request, timeout=3)
            self.assertEqual(no_publish.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
