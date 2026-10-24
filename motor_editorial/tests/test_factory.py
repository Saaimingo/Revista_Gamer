from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from motor_editorial import cli
from motor_editorial.db import Store
from motor_editorial.editorial import article_revision_sha256, review_matches_revision
from motor_editorial.factory import run_factory_demo
from motor_editorial.layout.contracts import (
    profile_sha256,
    story_revision_sha256,
    validate_layout_plan,
    validate_story_package,
)
from motor_editorial.orchestration import AgentQueue, TaskDispatcher


class SyntheticFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.store = Store(self.data_dir / "motor.sqlite3", self.data_dir / "artifacts")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_happy_path_uses_one_dispatcher_and_stops_at_simulated_internal_gate(self) -> None:
        with patch("motor_editorial.factory.TaskDispatcher", wraps=TaskDispatcher) as dispatcher_class:
            report = run_factory_demo(self.store, run_id="factory-c1-test-run")
        self.assertEqual(dispatcher_class.call_count, 1)
        self.assertEqual(report["status"], "simulated_approved_internally")
        self.assertEqual(report["task_ledger"], "agent_tasks/agent_task_events")
        self.assertEqual(report["task_count"], 15)
        self.assertTrue(report["synthetic_fixture_only"])
        self.assertEqual(report["composition_status"], "PASS")
        self.assertFalse(report["published"])
        self.assertEqual(report["publication_state"], "not_published")
        self.assertEqual(report["network_calls"], 0)
        self.assertEqual(report["siwc_calls"], 0)
        self.assertEqual(report["paid_api_calls"], 0)

        queue = AgentQueue(self.store)
        tasks = {task.task_id: task for task in queue.list_tasks(limit=100)}
        run_tasks = [tasks[task_id] for task_id in report["task_ids"]]
        self.assertEqual(len(run_tasks), 15)
        self.assertTrue(all(task.state == "succeeded" for task in run_tasks))
        self.assertEqual([row["stage"] for row in report["task_stages"][:5]], [
            "source_analysis", "outline", "draft", "fact_check", "review",
        ])
        self.assertEqual(
            {row["profile_id"] for row in report["task_stages"]},
            {
                "internal-controlled-editorial-experiment",
                "synthetic-rights-inventory",
                "synthetic-contract-adapter",
                "synthetic-layout-engine",
                "fixture-human-approval-gate",
            },
        )
        self.assertGreater(sum(len(queue.events(task.task_id)) for task in run_tasks), 15)

        with closing(self.store.connect()) as connection:
            attempts = connection.execute("SELECT COUNT(*) FROM execution_attempts").fetchone()[0]
        self.assertEqual(attempts, 0)

        package_task = next(task for task in run_tasks if task.task_type == "factory.story_package")
        story_package = package_task.result["story_package"]
        validate_story_package(story_package)
        self.assertEqual(
            story_package["payload"]["editorial_provenance"]["article_revision_sha256"],
            report["article_revision_sha256"],
        )
        self.assertEqual(
            story_package["payload"]["review"]["reviewed_story_sha256"],
            story_revision_sha256(story_package["payload"]),
        )
        self.assertEqual(story_package["payload"]["review"]["review_kind"], "synthetic_contract_bridge")
        self.assertFalse(story_package["payload"]["review"]["human_approval"])
        self.assertNotEqual(
            story_package["payload"]["review"]["reviewed_story_sha256"],
            report["reviewed_revision_sha256"],
        )
        for role, identity in story_package["payload"]["identities"].items():
            self.assertEqual(identity["role"], role)
            self.assertTrue(profile_sha256(identity))

        editorial_tasks = {
            task.payload["stage"]: task for task in run_tasks
            if task.task_type == "editorial.stage"
        }
        draft = editorial_tasks["draft"].result["structured_output"]
        review = editorial_tasks["review"].result["structured_output"]
        self.assertEqual(review["reviewed_revision_sha256"], article_revision_sha256(draft))
        self.assertTrue(review_matches_revision(review, draft))

        plan_task = next(task for task in run_tasks if task.payload["stage"] == "layout_plan")
        validate_layout_plan(plan_task.result["layout_plan"])
        preview_path = Path(report["preview_path"])
        self.assertTrue(preview_path.is_file())
        html = preview_path.read_text(encoding="utf-8")
        self.assertIn("Farol de Papel", html)
        self.assertIn("Placeholder sintético", html)
        self.assertNotIn("<img", html.casefold())
        self.assertNotIn("http://", html.casefold())
        self.assertNotIn("https://", html.casefold())

        resumed = run_factory_demo(self.store, run_id="factory-c1-test-run")
        self.assertEqual(resumed["task_ids"], report["task_ids"])
        self.assertEqual(resumed["task_count"], report["task_count"])
        self.assertEqual(len(queue.list_tasks(limit=100)), 15)

    def test_cli_factory_demo_emits_audit_report(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli.main([
                "--data-dir", str(self.data_dir / "cli"),
                "factory-demo", "--run-id", "factory-cli-c1-test",
            ])
        self.assertEqual(exit_code, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["status"], "simulated_approved_internally")
        self.assertEqual(report["composition_status"], "PASS")
        self.assertFalse(report["published"])


if __name__ == "__main__":
    unittest.main()
