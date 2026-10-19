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
from motor_editorial.workflow import APPROVAL_PHRASE, EXCLUSION_PHRASE, Motor


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

    def approve_multipauta_demo(self):
        result = self.motor.run_multipauta_demo()
        self.motor.run_multipauta_demo()
        stories = {row["topic_key"]: row for row in self.store.list_stories()}
        garden = stories["garden-of-echoes-fotografia"]
        self.motor.exclude_story_from_edition(
            result.edition_id, garden["id"], "Diretoria de teste",
            "Bloqueio editorial ficticio documentado.", EXCLUSION_PHRASE,
        )
        self.motor.approve_internally(
            result.edition_id, "Diretoria de teste", APPROVAL_PHRASE
        )
        return result, stories

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

    def test_multipauta_isolates_failures_resumes_and_composes_two_ordered_articles(self) -> None:
        first = self.motor.run_multipauta_demo()
        self.assertEqual(first.status, "waiting_on_blockers")
        edition = self.store.get_edition(first.edition_id)
        self.assertEqual(edition["composition_status"], "waiting_on_blockers")
        stories = {row["topic_key"]: row for row in self.store.list_stories()}
        self.assertEqual(len(stories), 3)
        garden = stories["garden-of-echoes-fotografia"]
        orbit = stories["orbit-racers-copa-nebular"]
        harbor = stories["clockwork-harbor-cooperativo"]
        self.assertEqual(orbit["state"], "media_checked")
        self.assertEqual(garden["state"], "blocked_by_review")
        self.assertEqual(garden["processing_status"], "intervention_required")
        self.assertEqual(harbor["state"], "selected")
        self.assertEqual(harbor["processing_status"], "recoverable_failure")
        self.assertEqual(self.store.get_run(first.run_id)["status"], "running")
        self.assertEqual(self.store.counts()["items"], 8)
        with closing(self.store.connect()) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM source_items WHERE state = 'duplicate'").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM source_items WHERE state = 'discarded'").fetchone()[0],
                1,
            )

        # A second call resumes the failed research attempt without repeating completed work.
        attempts_before = self.store.counts()["attempts"]
        restarted_store = Store(self.root / "motor.sqlite3", self.root / "artifacts")
        restarted_motor = Motor(restarted_store)
        second = restarted_motor.run_multipauta_demo()
        self.assertEqual(second.status, "waiting_on_blockers")
        self.assertEqual(self.store.get_story(harbor["id"])["state"], "media_checked")
        self.assertEqual(self.store.get_story(orbit["id"])["state"], "media_checked")
        with closing(self.store.connect()) as connection:
            retries = connection.execute(
                "SELECT COUNT(*) FROM execution_attempts WHERE story_id = ? AND stage = 'research-v2'",
                (harbor["id"],),
            ).fetchone()[0]
        self.assertEqual(retries, 2)
        self.assertGreater(self.store.counts()["attempts"], attempts_before)
        self.assertEqual(self.store.get_edition(first.edition_id)["composition_status"], "waiting_on_blockers")

        with self.assertRaises(InvalidApproval):
            self.motor.approve_internally(first.edition_id, "Diretoria", APPROVAL_PHRASE)
        self.motor.exclude_story_from_edition(
            first.edition_id, garden["id"], "Diretoria de teste",
            "Revisao ficticia excedeu o limite desta demonstracao.", EXCLUSION_PHRASE,
        )
        edition = self.store.get_edition(first.edition_id)
        self.assertEqual(edition["composition_status"], "ready_for_approval")
        memberships = self.store.edition_members(first.edition_id)
        excluded = next(row for row in memberships if row["story_id"] == garden["id"])
        self.assertEqual(excluded["active"], 0)
        self.assertIn("Revisao ficticia", excluded["exclusion_reason"])
        self.assertEqual(self.store.get_story(garden["id"])["state"], "blocked_by_review")

        preview = self.store.safe_artifact_path(edition["preview_path"]).read_text(encoding="utf-8")
        self.assertEqual(preview.count('class="edition-story"'), 2)
        self.assertLess(preview.index(orbit["id"]), preview.index(harbor["id"]))
        self.assertIn(orbit["question"], preview)
        self.assertIn(harbor["question"], preview)
        self.assertNotIn(garden["question"], preview)
        self.assertIn("Fontes fictícias da demonstração", preview)
        self.assertIn("Placeholder interno", preview)
        self.assertNotIn('data-asset-id="asset-v02-pending-cover"', preview)
        events = self.store.list_events(f"{first.edition_id}:{garden['id']}")
        self.assertTrue(any(event["action"] == "story_excluded_from_edition" for event in events))

        with self.assertRaises(InvalidApproval):
            self.motor.approve_internally(first.edition_id, "Diretoria", "aprovar")
        self.motor.approve_internally(first.edition_id, "Diretoria", APPROVAL_PHRASE)
        self.assertEqual(
            self.store.get_edition(first.edition_id)["composition_status"], "approved_internally"
        )
        self.assertEqual(self.store.get_story(orbit["id"])["state"], "approved_internally")
        self.assertEqual(self.store.get_story(harbor["id"])["state"], "approved_internally")
        reopened = Store(self.root / "motor.sqlite3", self.root / "artifacts")
        self.assertEqual(reopened.get_edition(first.edition_id)["composition_status"], "approved_internally")

    def test_multipauta_rights_change_refreshes_preview_and_requires_new_approval(self) -> None:
        result = self.motor.run_multipauta_demo()
        self.motor.run_multipauta_demo()
        stories = {row["topic_key"]: row for row in self.store.list_stories()}
        garden = stories["garden-of-echoes-fotografia"]
        self.motor.exclude_story_from_edition(
            result.edition_id, garden["id"], "Diretoria",
            "Bloqueio editorial ficticio documentado.", EXCLUSION_PHRASE,
        )
        with self.store.transaction() as connection:
            connection.execute(
                "UPDATE media_assets SET permission_status = 'bloqueado' WHERE id = 'asset-v02-orbit-art'"
            )
        with self.assertRaisesRegex(InvalidApproval, "previa multipauta foi atualizada"):
            self.motor.approve_internally(result.edition_id, "Diretoria", APPROVAL_PHRASE)
        edition = self.store.get_edition(result.edition_id)
        preview = self.store.safe_artifact_path(edition["preview_path"]).read_text(encoding="utf-8")
        self.assertNotIn('data-asset-id="asset-v02-orbit-art"', preview)
        self.assertIn("bloqueado", preview)
        self.assertEqual(edition["composition_status"], "ready_for_approval")
        self.motor.approve_internally(result.edition_id, "Diretoria", APPROVAL_PHRASE)
        self.assertEqual(self.store.get_edition(result.edition_id)["status"], "approved_internally")

    def test_approved_multipauta_resumes_are_idempotent_and_preserve_approval(self) -> None:
        result, stories = self.approve_multipauta_demo()
        approved = self.store.get_edition(result.edition_id)
        approval_snapshot = (
            approved["status"], approved["composition_status"], approved["approved_by"],
            approved["approved_at"], approved["composition_fingerprint"],
        )
        counts_before = self.store.counts()
        events_before = tuple(
            (row["entity_id"], row["action"], row["actor"], row["after_json"])
            for row in self.store.list_events()
        )

        resumed_story = self.motor.run_multipauta_story(
            result.run_id, stories["orbit-racers-copa-nebular"]["id"]
        )
        resumed_batch = self.motor.run_multipauta_demo()

        self.assertEqual(resumed_story.status, "approved_internally")
        self.assertEqual(resumed_batch.status, "approved_internally")
        current = self.store.get_edition(result.edition_id)
        self.assertEqual(
            (
                current["status"], current["composition_status"], current["approved_by"],
                current["approved_at"], current["composition_fingerprint"],
            ),
            approval_snapshot,
        )
        self.assertEqual(self.store.counts(), counts_before)
        self.assertEqual(
            tuple(
                (row["entity_id"], row["action"], row["actor"], row["after_json"])
                for row in self.store.list_events()
            ),
            events_before,
        )
        self.assertTrue(
            all(self.store.get_story(row["id"])["state"] == "approved_internally"
                for row in stories.values() if row["topic_key"] != "garden-of-echoes-fotografia")
        )

    def test_rejected_current_revision_after_approval_keeps_edition_blocked_on_resume(self) -> None:
        result, stories = self.approve_multipauta_demo()
        orbit = stories["orbit-racers-copa-nebular"]
        with self.store.transaction() as connection:
            connection.execute(
                "UPDATE stories SET current_revision_number = 1 WHERE id = ?",
                (orbit["id"],),
            )
            rejected_revision = connection.execute(
                """SELECT ar.status, rr.approved FROM article_revisions ar
                   LEFT JOIN review_results rr ON rr.revision_id = ar.id
                   WHERE ar.story_id = ? AND ar.version = 1
                   ORDER BY rr.pass_number DESC LIMIT 1""",
                (orbit["id"],),
            ).fetchone()
        self.assertNotEqual(rejected_revision["status"], "approved")
        self.assertNotEqual(rejected_revision["approved"], 1)

        self.assertTrue(self.motor.revalidate_edition_preview_for_access(result.edition_id))
        invalidated = self.store.get_edition(result.edition_id)
        self.assertEqual(invalidated["status"], "awaiting_human_approval")
        self.assertEqual(invalidated["composition_status"], "waiting_on_blockers")
        self.assertIsNone(invalidated["approved_by"])
        self.assertIsNone(invalidated["approved_at"])

        resumed = self.motor.run_multipauta_demo()
        edition = self.store.get_edition(result.edition_id)
        self.assertEqual(resumed.status, "waiting_on_blockers")
        self.assertEqual(edition["composition_status"], "waiting_on_blockers")
        self.assertEqual(edition["status"], "awaiting_human_approval")
        self.assertEqual(self.store.get_story(orbit["id"])["current_revision_number"], 1)
        self.assertEqual(self.store.get_story(orbit["id"])["state"], "approved_internally")
        self.assertTrue(
            any(event["action"] == "internal_approval_invalidated"
                for event in self.store.list_events(result.edition_id))
        )

    def test_revoked_media_after_approval_invalidates_edition_and_requires_reapproval(self) -> None:
        result, stories = self.approve_multipauta_demo()
        approved = self.store.get_edition(result.edition_id)
        approved_fingerprint = approved["composition_fingerprint"]
        approved_at = approved["approved_at"]
        with self.store.transaction() as connection:
            connection.execute(
                "UPDATE media_assets SET permission_status = 'bloqueado' "
                "WHERE id = 'asset-v02-orbit-art'"
            )

        resumed = self.motor.run_multipauta_demo()

        self.assertEqual(resumed.status, "ready_for_approval")
        edition = self.store.get_edition(result.edition_id)
        self.assertEqual(edition["status"], "awaiting_human_approval")
        self.assertEqual(edition["composition_status"], "ready_for_approval")
        self.assertIsNone(edition["approved_by"])
        self.assertIsNone(edition["approved_at"])
        self.assertNotEqual(edition["composition_fingerprint"], approved_fingerprint)
        self.assertNotEqual(edition["approved_at"], approved_at)
        active_stories = [
            row for row in stories.values()
            if row["topic_key"] != "garden-of-echoes-fotografia"
        ]
        self.assertTrue(
            all(self.store.get_story(row["id"])["state"] == "awaiting_human_approval"
                for row in active_stories)
        )
        orbit_media = next(
            row for row in self.store.story_detail(stories["orbit-racers-copa-nebular"]["id"])["media"]
            if row["asset_id"] == "asset-v02-orbit-art"
        )
        self.assertEqual(orbit_media["decision"], "placeholder")
        preview = self.store.safe_artifact_path(edition["preview_path"]).read_text(encoding="utf-8")
        self.assertNotIn('data-asset-id="asset-v02-orbit-art"', preview)
        self.assertIn("bloqueado", preview)
        self.assertTrue(
            any(event["action"] == "internal_approval_invalidated"
                for event in self.store.list_events(result.edition_id))
        )

        self.motor.approve_internally(
            result.edition_id, "Diretoria de revalidacao", APPROVAL_PHRASE
        )
        final_edition = self.store.get_edition(result.edition_id)
        self.assertEqual(final_edition["status"], "approved_internally")
        self.assertEqual(final_edition["approved_by"], "Diretoria de revalidacao")

    def test_multipauta_preview_access_revalidates_media_after_approval(self) -> None:
        result, stories = self.approve_multipauta_demo()
        with self.store.transaction() as connection:
            connection.execute(
                "UPDATE media_assets SET permission_status = 'bloqueado' "
                "WHERE id = 'asset-v02-orbit-art'"
            )

        server = create_server(self.motor, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urlopen(
                base_url + f"/editions/{result.edition_id}/preview", timeout=3
            ) as response:
                self.assertEqual(response.status, 200)
                preview = response.read().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

        edition = self.store.get_edition(result.edition_id)
        self.assertEqual(edition["status"], "awaiting_human_approval")
        self.assertEqual(edition["composition_status"], "ready_for_approval")
        self.assertIsNone(edition["approved_by"])
        self.assertIsNone(edition["approved_at"])
        self.assertNotIn('data-asset-id="asset-v02-orbit-art"', preview)
        self.assertIn("bloqueado", preview)
        self.assertIn("Examine esta prévia", preview)
        self.assertEqual(
            self.store.get_story(stories["orbit-racers-copa-nebular"]["id"])["state"],
            "awaiting_human_approval",
        )
        self.assertTrue(
            any(event["action"] == "internal_approval_invalidated"
                for event in self.store.list_events(result.edition_id))
        )

    def test_multipauta_batch_and_individual_resume_share_serialization_lock(self) -> None:
        initial = self.motor.run_multipauta_demo()
        stories = {row["topic_key"]: row for row in self.store.list_stories()}
        orbit_id = stories["orbit-racers-copa-nebular"]["id"]
        harbor_id = stories["clockwork-harbor-cooperativo"]["id"]
        batch_paused = threading.Event()
        release_batch = threading.Event()
        individual_entered_while_batch_paused = threading.Event()
        individual_started = threading.Event()
        results = []
        errors = []
        original_run_story = self.motor._run_multipauta_story

        def controlled_run_story(run_id, story_id, data):
            if story_id == orbit_id and not batch_paused.is_set():
                batch_paused.set()
                if not release_batch.wait(timeout=5):
                    raise AssertionError("A barreira de concorrencia nao foi liberada.")
            elif story_id == harbor_id and batch_paused.is_set() and not release_batch.is_set():
                individual_entered_while_batch_paused.set()
                raise AssertionError("A retomada individual entrou durante a execucao em lote.")
            return original_run_story(run_id, story_id, data)

        def run_batch() -> None:
            try:
                results.append(self.motor.run_multipauta_demo())
            except Exception as error:  # surfaced as assertion below
                errors.append(error)

        def run_individual() -> None:
            try:
                individual_started.set()
                results.append(self.motor.run_multipauta_story(initial.run_id, harbor_id))
            except Exception as error:  # surfaced as assertion below
                errors.append(error)

        with patch.object(self.motor, "_run_multipauta_story", side_effect=controlled_run_story):
            batch_thread = threading.Thread(target=run_batch)
            individual_thread = threading.Thread(target=run_individual)
            batch_thread.start()
            self.assertTrue(batch_paused.wait(timeout=3))
            individual_thread.start()
            self.assertTrue(individual_started.wait(timeout=3))
            entered_while_paused = individual_entered_while_batch_paused.wait(timeout=0.2)
            release_batch.set()
            batch_thread.join(timeout=8)
            individual_thread.join(timeout=8)

        self.assertFalse(entered_while_paused)
        self.assertFalse(batch_thread.is_alive())
        self.assertFalse(individual_thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.edition_id == initial.edition_id for result in results))
        self.assertEqual(len(self.store.list_editions()), 1)
        self.assertEqual(len(self.store.list_stories()), 3)
        self.assertEqual(self.store.get_story(harbor_id)["state"], "media_checked")
        self.assertEqual(self.store.get_edition(initial.edition_id)["composition_status"], "waiting_on_blockers")
        with closing(self.store.connect()) as connection:
            research_attempts = connection.execute(
                "SELECT COUNT(*) FROM execution_attempts WHERE story_id = ? AND stage = 'research-v2'",
                (harbor_id,),
            ).fetchone()[0]
        self.assertEqual(research_attempts, 2)

    def test_multipauta_rejects_unaudited_or_invalid_exclusion_and_distinct_run_ids(self) -> None:
        first = self.motor.run_multipauta_demo("run-paralelo-a")
        self.motor.run_multipauta_demo("run-paralelo-b")
        first_ids = {row["id"] for row in self.store.list_stories() if row["run_id"] == "run-paralelo-a"}
        second_ids = {row["id"] for row in self.store.list_stories() if row["run_id"] == "run-paralelo-b"}
        self.assertEqual(len(first_ids), 3)
        self.assertTrue(first_ids.isdisjoint(second_ids))
        member = self.store.edition_members(first.edition_id)[1]
        with self.assertRaises(InvalidApproval):
            self.motor.exclude_story_from_edition(
                first.edition_id, member["story_id"], "Diretoria", "Motivo valido para teste.", ""
            )
        with self.assertRaises(InvalidApproval):
            self.motor.exclude_story_from_edition(
                first.edition_id, member["story_id"], "Diretoria", "curto", EXCLUSION_PHRASE
            )
        self.assertEqual(
            self.store.get_edition(first.edition_id)["composition_status"], "waiting_on_blockers"
        )

    def test_multipauta_concurrent_and_successive_calls_are_serialized_and_idempotent(self) -> None:
        barrier = threading.Barrier(3)
        results = []
        errors = []

        def run_once() -> None:
            try:
                barrier.wait(timeout=3)
                results.append(self.motor.run_multipauta_demo())
            except Exception as error:  # surfaced as assertion below
                errors.append(error)

        threads = [threading.Thread(target=run_once) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=3)
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.status == "waiting_on_blockers" for result in results))
        stories = self.store.list_stories()
        self.assertEqual(len(stories), 3)
        with closing(self.store.connect()) as connection:
            counts = {
                row["stage"]: row["total"] for row in connection.execute(
                    "SELECT stage, COUNT(*) AS total FROM execution_attempts GROUP BY stage"
                )
            }
        self.assertEqual(counts["triage-v2"], 1)
        self.assertEqual(counts["ingest-v2"], 1)
        self.assertEqual(counts["research-v2"], 4)
        before = self.store.counts()
        repeated = self.motor.run_multipauta_demo()
        self.assertEqual(repeated.status, "waiting_on_blockers")
        self.assertEqual(self.store.counts(), before)

    def test_multipauta_panel_runs_exclusion_and_preview_only_on_loopback(self) -> None:
        server = create_server(self.motor, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            self.assertEqual(server.server_address[0], "127.0.0.1")
            with urlopen(base_url + "/", timeout=3) as response:
                dashboard = response.read().decode("utf-8")
            self.assertIn("Motor Editorial", dashboard)
            csrf = re.search(r'name="csrf" value="([^"]+)"', dashboard).group(1)
            demo_form = urlencode({"csrf": csrf}).encode("utf-8")
            request = Request(
                base_url + "/demo/run", data=demo_form,
                headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
            )
            with urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
                after_batch = response.read().decode("utf-8")
            self.assertIn("Executar/retomar esta pauta", after_batch)
            harbor = next(
                row for row in self.store.list_stories()
                if row["topic_key"] == "clockwork-harbor-cooperativo"
            )
            request = Request(
                base_url + f"/stories/{harbor['id']}/run", data=demo_form,
                headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
            )
            with urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
            edition = self.store.list_editions()[0]
            garden = next(
                row for row in self.store.list_stories()
                if row["topic_key"] == "garden-of-echoes-fotografia"
            )
            with self.assertRaises(HTTPError) as pending:
                urlopen(base_url + f"/editions/{edition['id']}/preview", timeout=3)
            self.assertEqual(pending.exception.code, 409)
            exclude_form = urlencode({
                "csrf": csrf, "actor": "Diretoria local",
                "reason": "Intervencao editorial ficticia documentada.",
                "confirmation": EXCLUSION_PHRASE,
            }).encode("utf-8")
            request = Request(
                base_url + f"/editions/{edition['id']}/stories/{garden['id']}/exclude",
                data=exclude_form,
                headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
            )
            with urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
            with urlopen(base_url + f"/editions/{edition['id']}/preview", timeout=3) as response:
                preview = response.read().decode("utf-8")
            self.assertEqual(preview.count('class="edition-story"'), 2)
            with self.assertRaises(HTTPError) as no_publish:
                urlopen(base_url + "/publish", timeout=3)
            self.assertEqual(no_publish.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_schema_v2_migration_adds_multipauta_columns_without_losing_membership(self) -> None:
        legacy_db = self.root / "legacy-v2.sqlite3"
        with closing(sqlite3.connect(legacy_db)) as connection:
            with connection:
                connection.executescript(
                    """CREATE TABLE runs (id TEXT PRIMARY KEY);
                       CREATE TABLE stories (
                           id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                           topic_key TEXT NOT NULL, question TEXT NOT NULL, state TEXT NOT NULL,
                           current_revision_number INTEGER NOT NULL DEFAULT 0,
                           created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                       );
                       CREATE TABLE editions (
                           id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                           status TEXT NOT NULL, preview_path TEXT NOT NULL, approved_by TEXT,
                           approved_at TEXT, created_at TEXT NOT NULL, UNIQUE(run_id)
                       );
                       CREATE TABLE edition_stories (
                           edition_id TEXT NOT NULL REFERENCES editions(id),
                           story_id TEXT NOT NULL REFERENCES stories(id), position INTEGER NOT NULL,
                           PRIMARY KEY (edition_id, story_id), UNIQUE(edition_id, position)
                       );
                       INSERT INTO runs VALUES ('legacy-run');
                       INSERT INTO stories VALUES ('legacy-story', 'legacy-run', 'old-topic', 'Old question', 'media_checked', 0, 't', 't');
                       INSERT INTO editions VALUES ('legacy-edition', 'legacy-run', 'awaiting_human_approval', 'old-preview.html', NULL, NULL, 't');
                       INSERT INTO edition_stories VALUES ('legacy-edition', 'legacy-story', 1);
                       PRAGMA user_version = 2;"""
                )
        migrated = Store(legacy_db, self.root / "legacy-v2-artifacts")
        with closing(migrated.connect()) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
            edition = connection.execute(
                "SELECT composition_status FROM editions WHERE id = 'legacy-edition'"
            ).fetchone()
            member = connection.execute(
                "SELECT active, required, story_id FROM edition_stories WHERE edition_id = 'legacy-edition'"
            ).fetchone()
            story_columns = {row["name"] for row in connection.execute("PRAGMA table_info(stories)")}
        self.assertEqual(edition["composition_status"], "legacy_v1")
        self.assertEqual(member["story_id"], "legacy-story")
        self.assertEqual(member["active"], 1)
        self.assertEqual(member["required"], 1)
        self.assertIn("processing_status", story_columns)


if __name__ == "__main__":
    unittest.main()
