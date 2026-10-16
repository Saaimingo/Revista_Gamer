"""End-to-end checks for the offline editorial simulation."""

from __future__ import annotations

import re
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from unittest.mock import patch

from motor_editorial.db import Store
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
