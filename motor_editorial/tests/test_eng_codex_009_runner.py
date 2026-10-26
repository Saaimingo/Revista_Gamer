from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from motor_editorial import eng_codex_009
from motor_editorial.evidence_packages import DOSSIERS


class EngCodex009RunnerTests(unittest.TestCase):
    def test_prepare_snapshots_verbatim_approved_docs_and_curated_only_trial_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary)

            def source_bytes(commit: str, source_path: str, *, repo_root: Path) -> bytes:
                return f"VERBATIM SOURCE {commit} {source_path}\n".encode("utf-8")

            with patch.object(eng_codex_009, "_git_show", side_effect=source_bytes):
                prepared = eng_codex_009.prepare_battery(
                    private_root=private_root,
                    repo_root=eng_codex_009.REPOSITORY_ROOT,
                    franchise_percent_reported=76,
                )

            self.assertEqual(len(prepared), 3)
            self.assertEqual(
                {item["persona_id"] for item in prepared},
                {"ranzinza", "beto-cartucho", "nina-prisma"},
            )
            for spec, item in zip(DOSSIERS, prepared):
                with self.subTest(persona=spec.persona_id):
                    self.assertEqual(item["persona_source_commit"], spec.persona_source_commit)
                    manifest_path = private_root / item["persona_manifest_ref"]
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    self.assertTrue(manifest["original_documents_unchanged"])
                    self.assertFalse(manifest["approved_sample_texts_included"])
                    self.assertEqual(len(manifest["documents"]), len(spec.persona_documents))
                    for index, source in enumerate(spec.persona_documents, start=1):
                        stored = private_root / manifest["documents"][index - 1]["private_copy_ref"]
                        self.assertEqual(
                            stored.read_bytes(),
                            f"VERBATIM SOURCE {spec.persona_source_commit} {source}\n".encode("utf-8"),
                        )
                    trial_path = private_root / item["input_ref"]
                    trial = json.loads(trial_path.read_text(encoding="utf-8"))
                    self.assertEqual(trial["editorial_brief"]["persona_id"], spec.persona_id)
                    self.assertEqual(trial["evidence_dossier"]["corpus_status"], "curator_notes_only_source_bodies_not_obtained")
                    self.assertEqual(trial["editorial_brief"]["permitted_research_scope"], ["read:radar_index"])
                    self.assertTrue(trial["evidence_dossier"]["evidence"])
                    self.assertTrue(trial["evidence_dossier"]["unresolved_source_candidates"])
                    self.assertFalse(item["source_bodies_obtained"])
                    self.assertFalse(item["ready_for_article_generation"])

            checkpoint = json.loads((private_root / "checkpoint.json").read_text(encoding="utf-8"))
            self.assertEqual(checkpoint["franchise_observation"]["percent"], 76)
            self.assertEqual(checkpoint["franchise_observation"]["source"], "user_reported_in_conversation")
            self.assertEqual(checkpoint["h04_real_tests_repeated"], 0)
            self.assertFalse(checkpoint["external_retrieval_authorized"])

    def test_user_facing_run_summary_omits_full_article_body(self) -> None:
        body = "PRIVATE FULL ARTICLE BODY THAT MUST NOT BE PRINTED"
        summary = eng_codex_009._public_summary({
            "status": "completed",
            "task_state": "succeeded",
            "task_id": "task-safe",
            "journalist": "Test Journalist",
            "article": {
                "word_count": 8,
                "full_text_sha256": "a" * 64,
                "full_text_ref": "story-versions/private/story.full.md",
                "full_text": body,
            },
            "factory_adapter": {"status": "awaiting_human_review"},
        })
        serialized = json.dumps(summary, ensure_ascii=False)
        self.assertNotIn(body, serialized)
        self.assertEqual(summary["word_count"], 8)
        self.assertTrue(summary["full_text_stored_privately"])


if __name__ == "__main__":
    unittest.main()
