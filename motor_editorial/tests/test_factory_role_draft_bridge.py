from __future__ import annotations

import unittest

from motor_editorial.factory import role_story_draft_to_editorial_output
from motor_editorial.orchestration import TaskFailure


class FactoryRoleDraftBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence_rows = [
            {"evidence_id": "ev-official", "source_id": "S1"},
            {"evidence_id": "ev-secondary", "source_id": "S2"},
        ]
        self.valid_source_ids = {"S1", "S2"}
        self.role_output = {
            "title": "Título de ensaio",
            "dek": "Linha fina sintética.",
            "sections": [{
                "heading": "O que está documentado",
                "body": "A fonte oficial registra a informação.",
                "evidence_ids": ["ev-official", "ev-secondary"],
            }],
            "claim_refs": ["claim-1"],
            "requested_research": [],
        }

    def test_maps_evidence_to_existing_factory_source_citations(self) -> None:
        original = {**self.role_output, "sections": [dict(self.role_output["sections"][0])]}

        result = role_story_draft_to_editorial_output(
            self.role_output,
            evidence_rows=self.evidence_rows,
            valid_source_ids=self.valid_source_ids,
        )

        self.assertEqual(result["headline"], self.role_output["title"])
        self.assertEqual(result["dek"], self.role_output["dek"])
        self.assertEqual(result["source_ids"], ["S1", "S2"])
        self.assertIn("## O que está documentado", result["body_markdown"])
        self.assertIn("[S1] [S2]", result["body_markdown"])
        self.assertEqual(self.role_output, original)

    def test_existing_valid_inline_citation_is_not_duplicated(self) -> None:
        output = {**self.role_output, "sections": [{
            "heading": "O que está documentado",
            "body": "A fonte oficial registra a informação [S1].",
            "evidence_ids": ["ev-official", "ev-secondary"],
        }]}

        result = role_story_draft_to_editorial_output(
            output,
            evidence_rows=self.evidence_rows,
            valid_source_ids=self.valid_source_ids,
        )

        self.assertEqual(result["body_markdown"].count("[S1]"), 1)
        self.assertEqual(result["body_markdown"].count("[S2]"), 1)

    def test_unknown_evidence_reference_fails_closed(self) -> None:
        output = {**self.role_output, "sections": [{
            "heading": "Seção",
            "body": "Texto com evidência não vinculada.",
            "evidence_ids": ["ev-missing"],
        }]}

        with self.assertRaisesRegex(TaskFailure, "evidence_id ausente") as caught:
            role_story_draft_to_editorial_output(
                output,
                evidence_rows=self.evidence_rows,
                valid_source_ids=self.valid_source_ids,
            )

        self.assertEqual(caught.exception.code, "factory_storydraft_unknown_evidence")

    def test_inline_citation_must_be_bound_to_section_evidence(self) -> None:
        output = {**self.role_output, "sections": [{
            "heading": "Seção",
            "body": "Texto que cita outra fonte [S2].",
            "evidence_ids": ["ev-official"],
        }]}

        with self.assertRaisesRegex(TaskFailure, "não corresponde às evidências") as caught:
            role_story_draft_to_editorial_output(
                output,
                evidence_rows=self.evidence_rows,
                valid_source_ids=self.valid_source_ids,
            )

        self.assertEqual(caught.exception.code, "factory_storydraft_citation_mismatch")

    def test_evidence_dossier_cannot_point_outside_the_current_source_packet(self) -> None:
        with self.assertRaisesRegex(TaskFailure, "fora do pacote corrente") as caught:
            role_story_draft_to_editorial_output(
                self.role_output,
                evidence_rows=[{"evidence_id": "ev-official", "source_id": "S9"}],
                valid_source_ids=self.valid_source_ids,
            )

        self.assertEqual(caught.exception.code, "factory_storydraft_source_invalid")


if __name__ == "__main__":
    unittest.main()
