from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from motor_editorial.evidence_packages import (
    DOSSIERS,
    DOSSIER_ROOT,
    EvidencePackageError,
    build_package,
    build_curated_trial_input,
    load_package,
    require_factory_ready,
    validate_package,
    write_package_manifests,
)


class EvidencePackageTests(unittest.TestCase):
    def test_three_curated_packages_match_their_dossier_bytes_and_keep_dna_as_reference(self) -> None:
        expected_counts = {
            "eng-codex-009-carranca": 12,
            "eng-codex-009-beto": 14,
            "eng-codex-009-nina": 11,
        }
        for spec in DOSSIERS:
            with self.subTest(package=spec.package_id):
                package = load_package(spec.package_id)
                result = validate_package(package)
                self.assertEqual(result["source_count"], expected_counts[spec.package_id])
                self.assertEqual(package["persona_reference"]["persona_id"], spec.persona_id)
                self.assertEqual(package["persona_reference"]["persona_version"], spec.persona_version)
                self.assertEqual(package["persona_reference"]["source_ref"], spec.persona_source_ref)
                self.assertEqual(package["persona_reference"]["source_commit"], spec.persona_source_commit)
                self.assertEqual(package["persona_reference"]["source_documents"], list(spec.persona_documents))
                self.assertTrue(package["persona_reference"]["must_remain_unchanged"])
                self.assertTrue(package["coverage_questions"])
                self.assertEqual(package["dossier_document"].split("/")[-1], spec.dossier_document)

    def test_manifests_label_summaries_as_curatorial_and_not_source_bodies(self) -> None:
        for spec in DOSSIERS:
            with self.subTest(package=spec.package_id):
                package = load_package(spec.package_id)
                self.assertTrue(all(
                    source["source_body_status"] in {"not_obtained", "unresolved_candidate"}
                    for source in package["source_candidates"]
                ))
                self.assertTrue(all(
                    source["rights_review_status"] == "not_revalidated"
                    and source["external_retrieval_authorized"] is False
                    and source["access_scope"] == "read:radar_index"
                    for source in package["source_candidates"]
                ))
                self.assertFalse(package["readiness"]["ready_for_article_generation"])
                self.assertTrue(package["readiness"]["curated_note_only_trial_ready"])
                self.assertEqual(validate_package(package)["source_bodies_obtained"], False)

    def test_curation_only_package_is_rejected_before_factory_use(self) -> None:
        package = load_package("eng-codex-009-carranca")
        with self.assertRaisesRegex(EvidencePackageError, "bloqueado para fábrica"):
            require_factory_ready(package)

    def test_deep_work_input_contains_only_curated_notes_and_preserves_all_evidence_gaps(self) -> None:
        for spec in DOSSIERS:
            with self.subTest(package=spec.package_id):
                package = load_package(spec.package_id)
                trial = build_curated_trial_input(package, test_id=f"trial-{spec.package_id}")
                dossier = trial["evidence_dossier"]
                brief = trial["editorial_brief"]
                self.assertEqual(brief["language"], "pt-BR")
                self.assertEqual(brief["article_form"], "full_investigative_report_with_expository_body_and_supported_editorial_conclusion")
                self.assertIn("reasoning between evidence and conclusions visible", brief["assignment"])
                self.assertEqual(brief["permitted_research_scope"], ["read:radar_index"])
                self.assertEqual(trial["writing_constraints"]["target_word_range"], package["requested_word_range"])
                self.assertEqual(dossier["corpus_status"], "curator_notes_only_source_bodies_not_obtained")
                self.assertEqual(dossier["rights_review_status"], "not_revalidated_for_this_run")
                self.assertTrue(dossier["evidence"])
                self.assertTrue(dossier["unresolved_source_candidates"])
                self.assertTrue(all(
                    row["provenance_status"] == "project_curated_summary_not_independently_revalidated"
                    and row["source_body_obtained"] is False
                    and row["rights_revalidated"] is False
                    for row in dossier["evidence"]
                ))
                self.assertEqual(len(dossier["evidence"]), validate_package(package)["curated_note_count"])
                self.assertFalse(package["readiness"]["ready_for_article_generation"])

    def test_index_only_research_route_is_typed_and_does_not_expand_permissions(self) -> None:
        package = load_package("eng-codex-009-nina")
        route = {
            "question": "What evidence is already in the local Radar index?",
            "purpose": "Fill a documented gap using read:radar_index only.",
            "profile_id": "research.creators.v1",
            "profile_version": "1.0.0",
            "evidence_kind": "official_statement",
        }
        trial = build_curated_trial_input(
            package, test_id="trial-nina-radar", local_research_route=route,
        )
        self.assertEqual(trial["editorial_brief"]["research_questions"], [{
            "question": route["question"], "purpose": route["purpose"],
        }])
        self.assertEqual(trial["editorial_brief"]["research_profile_id"], "research.creators.v1")
        self.assertEqual(trial["editorial_brief"]["required_evidence_kinds"], ["official_statement"])
        self.assertEqual(trial["editorial_brief"]["permitted_research_scope"], ["read:radar_index"])
        self.assertNotIn("read:registered_public_sources", trial["editorial_brief"]["permitted_research_scope"])

    def test_changed_document_or_access_gate_invalidates_manifest(self) -> None:
        package = load_package("eng-codex-009-beto")
        changed = copy.deepcopy(package)
        changed["readiness"]["external_retrieval_authorized"] = True
        with self.assertRaisesRegex(EvidencePackageError, "diverge"):
            validate_package(changed)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dossier = DOSSIER_ROOT / DOSSIERS[1].dossier_document
            root.joinpath(DOSSIERS[1].dossier_document).parent.mkdir(parents=True, exist_ok=True)
            root.joinpath(DOSSIERS[1].dossier_document).write_bytes(dossier.read_bytes() + b"\nchanged\n")
            with self.assertRaisesRegex(EvidencePackageError, "diverge"):
                validate_package(package, dossier_root=root)

    def test_package_writer_is_deterministic_and_creates_all_three_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = write_package_manifests(target=Path(temporary) / "first")
            second = write_package_manifests(target=Path(temporary) / "second")
            self.assertEqual([path.read_bytes() for path in first], [path.read_bytes() for path in second])
            self.assertEqual(len(first), 3)


if __name__ == "__main__":
    unittest.main()
