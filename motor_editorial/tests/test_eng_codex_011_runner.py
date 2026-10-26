from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from motor_editorial.eng_codex_011 import (
    EDITOR_HANDOFF_LANES,
    SOURCE_CANDIDATES,
    Checkpoint,
    RunBlocked,
    _candidate_matches_triage_refs,
    _canonicalize_investigator_claim_ids,
    _make_radar_profile,
    _map_persisted_live_items,
    _normalize_writer_claim_refs_against_section_evidence,
    _register_source,
)
from motor_editorial.radar_store import RadarStore


class PersistedTriageResumeTests(unittest.TestCase):
    def test_source_registration_resume_requires_the_exact_saved_blocker(self) -> None:
        run_id = "eng-codex-011-fixture-run"
        with tempfile.TemporaryDirectory(prefix="eng011-checkpoint-resume-") as temporary:
            root = Path(temporary)
            (root / "active-run.json").write_text(json.dumps({
                "run_id": run_id, "status": "blocked", "blocker_code": "RadarStoreError",
            }), encoding="utf-8")
            (root / "checkpoint.json").write_text(json.dumps({
                "run_id": run_id, "stage": "persona_load", "status": "running",
                "events": [{"stage": "persona_load", "status": "succeeded"}],
            }), encoding="utf-8")

            checkpoint = Checkpoint.resume_after_source_registration_block(root, run_id)

            self.assertEqual(checkpoint.state["stage"], "resume_after_source_registration")
            self.assertEqual(checkpoint.state["events"][-1]["repeated_siwc_calls"], 0)
            self.assertEqual(checkpoint.state["events"][-1]["repeated_public_requests"], 0)

    def test_writer_preflight_resume_accepts_only_saved_persona_load_guard_blocker(self) -> None:
        run_id = "eng-codex-011-fixture-run"
        with tempfile.TemporaryDirectory(prefix="eng011-writer-checkpoint-") as temporary:
            root = Path(temporary)
            (root / "active-run.json").write_text(json.dumps({
                "run_id": run_id, "status": "blocked",
                "blocker_code": "existing_writer_task_is_not_a_safe_pre_external_recovery",
            }), encoding="utf-8")
            (root / "checkpoint.json").write_text(json.dumps({
                "run_id": run_id, "stage": "persona_load", "status": "running",
                "events": [{"stage": "persona_load", "status": "succeeded"}],
            }), encoding="utf-8")

            checkpoint = Checkpoint.resume_after_pre_external_writer_block(root, run_id)

            self.assertEqual(checkpoint.state["stage"], "resume_after_writer_preflight")
            self.assertEqual(checkpoint.state["events"][-1]["repeated_siwc_calls"], 0)
            self.assertEqual(checkpoint.state["events"][-1]["repeated_public_requests"], 0)

    def test_writer_revision_resume_accepts_only_saved_unknown_claim_blocker(self) -> None:
        run_id = "eng-codex-011-fixture-run"
        with tempfile.TemporaryDirectory(prefix="eng011-revision-checkpoint-") as temporary:
            root = Path(temporary)
            (root / "agent-usage").mkdir()
            (root / "agent-usage" / "revision.attempt-001.json").write_text("{}", encoding="utf-8")
            (root / "active-run.json").write_text(json.dumps({
                "run_id": run_id, "status": "blocked", "blocker_code": "persona_writer_call_blocked",
            }), encoding="utf-8")
            (root / "checkpoint.json").write_text(json.dumps({
                "run_id": run_id, "stage": "journalist_correction_agent", "status": "running",
                "events": [{
                    "stage": "journalist_correction_agent", "status": "blocked",
                    "task_id": "revision", "task_state": "blocked",
                    "error_code": "siwc_output_unknown_claim",
                    "usage_record_ref": "agent-usage/revision.attempt-001.json",
                }],
            }), encoding="utf-8")

            checkpoint = Checkpoint.resume_after_writer_revision_failure(root, run_id)

            self.assertEqual(checkpoint.state["stage"], "resume_after_writer_revision_failure")
            self.assertEqual(checkpoint.state["events"][-1]["repeated_siwc_calls"], 0)
            self.assertEqual(checkpoint.state["events"][-1]["repeated_public_requests"], 0)

    def test_event_reference_links_candidate_when_item_id_is_not_returned(self) -> None:
        candidate = {
            "item_id": "discovery-release-42",
            "triage_evidence_refs": ["event-abc", "snapshot-def", "radar://document/" + "a" * 32],
        }

        self.assertTrue(_candidate_matches_triage_refs(candidate, {"event-abc"}))
        self.assertTrue(_candidate_matches_triage_refs(candidate, {"discovery-release-42"}))
        self.assertFalse(_candidate_matches_triage_refs(candidate, {"event-unrelated"}))

    def test_monitoramento_is_forwarded_to_editor_for_decision(self) -> None:
        self.assertIn("monitoramento", EDITOR_HANDOFF_LANES)
        self.assertNotIn("descartada", EDITOR_HANDOFF_LANES)

    def test_natural_language_investigator_claim_id_is_normalized_and_label_preserved(self) -> None:
        source_label = "Proton 11.0-2e release metadata: title and published date"
        normalized, mapping = _canonicalize_investigator_claim_ids({
            "claims": [{"claim_id": source_label, "evidence_ids": ["radar://document/" + "a" * 32],
                        "epistemic_status": "official_statement"}],
            "blockers": [],
        })

        claim = normalized["claims"][0]
        self.assertRegex(claim["claim_id"], r"^claim-[a-f0-9]{24}$")
        self.assertEqual(claim["source_claim_label"], source_label)
        self.assertEqual(mapping[0]["source_claim_label"], source_label)
        self.assertEqual(mapping[0]["canonical_claim_id"], claim["claim_id"])

    def test_writer_claim_field_recovery_only_drops_evidence_refs_cited_in_sections(self) -> None:
        prompt_input = {
            "task_input_data": {"data": {"evidence_dossier": {
                "claims": [], "evidence": [{"evidence_id": "radar://document/release-01"}],
            }}},
        }
        output = {
            "title": "Release",
            "dek": "The official record confirms a date.",
            "sections": [{"heading": "Record", "body": "The tag is listed.",
                          "evidence_ids": ["radar://document/release-01"]}],
            "claim_refs": ["radar://document/release-01"],
        }

        normalized, dropped = _normalize_writer_claim_refs_against_section_evidence(output, prompt_input)

        self.assertEqual(dropped, ["radar://document/release-01"])
        self.assertEqual(normalized["claim_refs"], [])
        self.assertEqual(normalized["sections"][0]["evidence_ids"], ["radar://document/release-01"])
        self.assertEqual(output["claim_refs"], ["radar://document/release-01"])

    def test_writer_claim_field_recovery_rejects_unknown_claim_label(self) -> None:
        prompt_input = {
            "task_input_data": {"data": {"evidence_dossier": {
                "claims": [], "evidence": [{"evidence_id": "evidence-01"}],
            }}},
        }
        output = {
            "sections": [{"evidence_ids": ["evidence-01"]}],
            "claim_refs": ["unsupported-claim"],
        }

        with self.assertRaisesRegex(RunBlocked, "beyond_known_section_evidence"):
            _normalize_writer_claim_refs_against_section_evidence(output, prompt_input)

    def test_persisted_document_rebuilds_release_tag_and_source_fields(self) -> None:
        document_id = "a" * 32
        document = {
            "document_id": document_id,
            "source_id": "github-api-proton-releases",
            "origin_url": "https://github.com/ValveSoftware/Proton/releases/tag/proton-11.0-2e",
            "canonical_url": "https://api.github.com/repos/ValveSoftware/Proton/releases/408184123",
            "publisher": "Valve Proton public releases",
            "byline": "ivyl",
            "published_at": "2026-10-09T17:49:01+00:00",
            "fetched_at": "2026-10-26T15:22:29+00:00",
            "title": "Proton 11.0-2e",
            "summary_snippet": "A short official release excerpt.",
        }

        class FakeRadarStore:
            def get_row(self, table: str, key_column: str, key_value: str):
                if table == "radar_documents" and key_column == "document_id" and key_value == document_id:
                    return document
                return None

        source = {
            "source_id": "github-api-proton-releases",
            "owner": "ValveSoftware",
            "repo": "Proton",
            "label": "Valve Proton public releases",
        }
        item = {
            "item_id": "discovery-release-42",
            "url": document["canonical_url"],
            "publisher": document["publisher"],
            "published_at": document["published_at"],
            "diff": "{}",
            "evidence_refs": ["event-abc", f"radar://document/{document_id}"],
        }

        mapped = _map_persisted_live_items([item], {source["source_id"]: source}, FakeRadarStore())
        candidate = mapped["discovery-release-42"]
        self.assertEqual(candidate["tag_name"], "proton-11.0-2e")
        self.assertEqual(candidate["title"], "Proton 11.0-2e")
        self.assertEqual(candidate["body_excerpt"], "A short official release excerpt.")
        self.assertEqual(candidate["author"], "ivyl")

    def test_radar_source_registration_is_idempotent_but_rejects_route_conflicts(self) -> None:
        source = SOURCE_CANDIDATES[1]
        detail_source_id = "github-api-proton-detail"
        display_name = "ValveSoftware/Proton release detail"
        with tempfile.TemporaryDirectory(prefix="eng011-source-registration-") as temporary:
            store = RadarStore(Path(temporary) / "radar.sqlite3")
            profile, endpoint = _make_radar_profile(source, detail_source_id, details=True, tag="proton-11.0-2e")

            _register_source(store, profile, display_name, endpoint)
            _register_source(store, profile, display_name, endpoint)

            rows = store.list_rows("radar_sources")
            self.assertEqual(len(rows), 1)
            conflict_profile, conflict_endpoint = _make_radar_profile(
                source, detail_source_id, details=True, tag="proton-11.0-3",
            )
            with self.assertRaisesRegex(RunBlocked, "persisted_radar_source_conflicts"):
                _register_source(store, conflict_profile, display_name, conflict_endpoint)


if __name__ == "__main__":
    unittest.main()
