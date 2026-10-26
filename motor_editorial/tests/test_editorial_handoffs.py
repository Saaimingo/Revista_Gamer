from __future__ import annotations

import unittest

from motor_editorial.editorial_handoffs import (
    CANDIDATE_DOSSIER_TYPE,
    JOURNALIST_TOPIC_MATRIX,
    build_assignment_editor_input,
    build_candidate_dossier,
    build_editorial_brief_from_assignment,
    project_editorial_brief_for_writer,
    validate_artifact,
    validate_assignment_editor_output,
)


class EditorialAgentHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate_dossier = build_candidate_dossier(
            story_id="discovery-batch-001",
            batch_id="batch-001",
            triage_task_id="task-triage-001",
            investigator_task_id="task-investigator-001",
            candidates=[{
                "candidate_item_id": "candidate-001",
                "triage_lane": "monitoramento",
                "candidate_angle": "Verificar a origem e o alcance do relato",
                "triage_evidence_refs": ["event-001", "radar://document/doc-001"],
                "evidence_ids": ["radar://document/doc-001"],
                "title": "Registro de origem",
                "publisher": "Fonte oficial",
                "url": "https://source.example.invalid/story",
                "source_lineage": [{"source_id": "source-001", "relation": "origin"}],
                "claim_lineage": [{"epistemic_status": "attributed_rumor"}],
            }],
            evidence=[{
                "evidence_id": "radar://document/doc-001",
                "source_id": "source-001",
                "source_document_id": "doc-001",
                "source_role": "primary_official_metadata",
                "publisher": "Fonte oficial",
                "source_url": "https://source.example.invalid/story",
                "content_sha256": "a" * 64,
                "excerpt": "Texto de origem que não pode ser copiado sem direito explícito.",
            }],
            investigator_output={
                "claims": [{
                    "claim_id": "O documento registra uma declaração, mas não confirma o conteúdo do rumor.",
                    "epistemic_status": "attributed_rumor",
                    "evidence_ids": ["radar://document/doc-001"],
                }],
                "blockers": ["Falta confirmação independente."],
                "open_questions": ["Existe fonte independente?"],
                "sufficiency": "partial",
            },
            portfolio=["edition-current"],
            triage_response_sha256="b" * 64,
            investigator_response_sha256="c" * 64,
        )

    def test_candidate_dossier_generates_safe_claim_id_without_losing_label_or_rumor(self) -> None:
        dossier = validate_artifact(self.candidate_dossier, CANDIDATE_DOSSIER_TYPE)
        payload = dossier["payload"]

        self.assertEqual(payload["candidate_item_ids"], ["candidate-001"])
        self.assertEqual(payload["candidates"][0]["triage_lane"], "monitoramento")
        self.assertEqual(payload["claims"][0]["epistemic_status"], "attributed_rumor")
        self.assertRegex(payload["claims"][0]["claim_id"], r"^claim-[a-f0-9]{24}$")
        self.assertEqual(
            payload["claims"][0]["source_claim_label"],
            "O documento registra uma declaração, mas não confirma o conteúdo do rumor.",
        )
        self.assertEqual(payload["claims"][0]["source_ids"], ["source-001"])
        self.assertEqual(payload["rumors"][0]["epistemic_status"], "attributed_rumor")
        self.assertIsNone(payload["evidence"][0]["excerpt"])
        self.assertFalse(payload["evidence"][0]["excerpt_authorized"])

    def test_candidate_dossier_rejects_unhashable_ids_as_contract_errors(self) -> None:
        malformed = {
            **self.candidate_dossier,
            "payload": {
                **self.candidate_dossier["payload"],
                "candidate_item_ids": [["candidate-001"]],
            },
        }

        with self.assertRaisesRegex(ValueError, "candidate_item_ids"):
            validate_artifact(malformed, CANDIDATE_DOSSIER_TYPE)

        malformed_portfolio = {
            **self.candidate_dossier,
            "payload": {
                **self.candidate_dossier["payload"],
                "portfolio": ["edition-current", "edition-current"],
            },
        }
        with self.assertRaisesRegex(ValueError, "portfolio"):
            validate_artifact(malformed_portfolio, CANDIDATE_DOSSIER_TYPE)

    def test_assignment_input_includes_monitoring_candidate_and_topic_role_matrix(self) -> None:
        editor_input = build_assignment_editor_input(
            self.candidate_dossier,
            edition_state={"edition_id": "edition-current", "active_story_ids": []},
        )

        self.assertEqual(editor_input["editorial_constraints"]["eligible_candidate_ids"], ["candidate-001"])
        self.assertEqual(editor_input["editorial_constraints"]["journalist_topic_matrix"], JOURNALIST_TOPIC_MATRIX)
        self.assertIn("monitoramento", editor_input["evidence_dossier"]["candidates"][0]["triage_lane"])
        self.assertIn("não os promova automaticamente", " ".join(editor_input["required_coverage"]))

    def test_assignment_output_must_select_candidate_and_approved_persona(self) -> None:
        output = {
            "candidate_item_id": "candidate-001",
            "angle": "O que a fonte realmente confirma",
            "genre": "investigation",
            "questions": ["Qual é a origem?"],
            "modules": [{"name": "evidence", "purpose": "separar fato de rumor"}],
            "gaps": ["Falta confirmação independente."],
            "needs_more_research": True,
            "journalist_persona_id": "nina-prisma",
        }
        validated = validate_assignment_editor_output(
            output,
            self.candidate_dossier,
            approved_persona_hashes={"nina-prisma": "d" * 64},
        )
        self.assertEqual(validated["candidate_item_id"], "candidate-001")
        self.assertEqual(validated["journalist_persona_ref"]["profile_sha256"], "d" * 64)

        with self.assertRaisesRegex(ValueError, "candidate_item_id ausente"):
            validate_assignment_editor_output({**output, "candidate_item_id": "candidate-other"}, self.candidate_dossier)
        with self.assertRaisesRegex(ValueError, "persona ausente"):
            validate_assignment_editor_output({**output, "journalist_persona_id": "unapproved-persona"}, self.candidate_dossier)
        with self.assertRaisesRegex(ValueError, "não corresponde ao tema"):
            validate_assignment_editor_output({**output, "editorial_theme": "hardware_technology_performance"}, self.candidate_dossier)

    def test_editorial_brief_binds_dossier_assignment_persona_and_hides_audit_from_writer(self) -> None:
        assignment = {
            "candidate_item_id": "candidate-001",
            "angle": "O que a fonte realmente confirma",
            "genre": "investigation",
            "questions": ["Qual é a origem?"],
            "modules": [{"name": "evidence", "purpose": "separar fato de rumor"}],
            "gaps": ["Falta confirmação independente."],
            "needs_more_research": True,
            "journalist_persona_id": "nina-prisma",
        }
        brief = build_editorial_brief_from_assignment(
            story_id="story-candidate-001",
            revision_id="assignment-001",
            candidate_dossier=self.candidate_dossier,
            assignment_output=assignment,
            approved_persona_hash="d" * 64,
            assignment_task_id="task-editor-001",
            assignment_response_sha256="e" * 64,
        )
        payload = brief["payload"]
        self.assertEqual(payload["candidate_dossier_sha256"], self.candidate_dossier["content_sha256"])
        self.assertEqual(payload["candidate_item_id"], "candidate-001")
        self.assertEqual(payload["triage_lane"], "monitoramento")
        self.assertEqual(payload["journalist_persona_ref"]["profile_sha256"], "d" * 64)
        self.assertFalse(payload["published"])
        reader_brief = project_editorial_brief_for_writer(brief)
        self.assertEqual(reader_brief["selected_journalist_id"], "nina-prisma")
        self.assertNotIn("assignment_task_id", reader_brief)
        self.assertNotIn("candidate_dossier_sha256", reader_brief)
        self.assertNotIn("published", reader_brief)


if __name__ == "__main__":
    unittest.main()
