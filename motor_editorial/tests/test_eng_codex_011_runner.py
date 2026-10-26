from __future__ import annotations

import unittest

from motor_editorial.eng_codex_011 import (
    EDITOR_HANDOFF_LANES,
    _candidate_matches_triage_refs,
    _canonicalize_investigator_claim_ids,
    _map_persisted_live_items,
)


class PersistedTriageResumeTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
