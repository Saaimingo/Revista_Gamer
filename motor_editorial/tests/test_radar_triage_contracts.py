from __future__ import annotations

import json
import unittest

from motor_editorial.radar_store import RadarStoreError
from motor_editorial.radar_triage import build_investigator_input, resolve_triage_output


def batch_value() -> dict:
    return {
        "batch_id": "batch-001",
        "portfolio": ["edition-current"],
        "items": [
            {
                "item_id": "candidate-a",
                "url": "https://source.example.invalid/a",
                "publisher": "Fonte A",
                "evidence_refs": ["candidate-a", "event-a", "radar://document/doc-a", "snapshot-a"],
                "diff": json.dumps({
                    "claim_lineage": [{
                        "claim_id": "claim-rumor-a",
                        "epistemic_status": "attributed_rumor",
                        "relation_type": "origin",
                    }],
                    "rumor_status_is_not_content_confirmation": True,
                }),
            },
            {
                "item_id": "candidate-b",
                "url": "https://source.example.invalid/b",
                "publisher": "Fonte B",
                "evidence_refs": ["candidate-b", "event-b", "radar://document/doc-b", "snapshot-b"],
                "diff": "{}",
            },
        ],
    }


class RadarTriageContractTests(unittest.TestCase):
    def test_exact_event_and_document_refs_resolve_to_items_and_keep_monitoramento(self) -> None:
        batch = batch_value()
        result = resolve_triage_output(batch, {
            "no_change": False,
            "decisions": [
                {
                    "candidate_angle": "Apurar a origem do rumor",
                    "suggested_lane": "monitoramento",
                    "evidence_refs": ["event-a", "radar://document/doc-a"],
                },
                {
                    "candidate_angle": "Atualização publicada pela fonte",
                    "suggested_lane": "descartar",
                    "evidence_refs": ["event-b"],
                },
            ],
        })

        self.assertEqual(result.status, "candidates_resolved")
        self.assertEqual(result.decisions[0].candidate_item_ids, ("candidate-a",))
        self.assertEqual(result.eligible_decisions[0].suggested_lane, "monitoramento")
        self.assertEqual(result.discarded_decisions[0].candidate_item_ids, ("candidate-b",))
        investigator_input = build_investigator_input(
            batch,
            result,
            triage_task_id="task-triage-001",
        )
        self.assertEqual(investigator_input["search_limits"]["candidate_count"], 1)
        candidate = investigator_input["search_limits"]["candidate_records"][0]
        self.assertEqual(candidate["candidate_item_id"], "candidate-a")
        self.assertEqual(candidate["triage_lane"], "monitoramento")
        preserved = json.loads(candidate["discovery_item"]["diff"])
        self.assertEqual(preserved["claim_lineage"][0]["epistemic_status"], "attributed_rumor")
        self.assertTrue(preserved["rumor_status_is_not_content_confirmation"])

    def test_no_change_is_a_durable_no_story_yet_result(self) -> None:
        result = resolve_triage_output(batch_value(), {"no_change": True, "decisions": []})

        self.assertEqual(result.status, "no_story_yet")
        self.assertEqual(result.eligible_decisions, ())
        with self.assertRaisesRegex(RadarStoreError, "Não há candidato elegível"):
            build_investigator_input(batch_value(), result, triage_task_id="task-triage-empty")

    def test_absent_or_ambiguous_refs_are_rejected(self) -> None:
        with self.assertRaisesRegex(RadarStoreError, "refs ausentes"):
            resolve_triage_output(batch_value(), {
                "no_change": False,
                "decisions": [{"candidate_angle": "x", "suggested_lane": "principal", "evidence_refs": ["event-missing"]}],
            })

        batch = batch_value()
        batch["items"][1]["evidence_refs"].append("shared-event")
        batch["items"][0]["evidence_refs"].append("shared-event")
        with self.assertRaisesRegex(RadarStoreError, "refs ambíguas"):
            resolve_triage_output(batch, {
                "no_change": False,
                "decisions": [{"candidate_angle": "x", "suggested_lane": "principal", "evidence_refs": ["shared-event"]}],
            })

    def test_explicit_candidate_ids_must_match_batch_and_cited_refs(self) -> None:
        batch = batch_value()
        valid = resolve_triage_output(batch, {
            "no_change": False,
            "decisions": [{
                "candidate_angle": "Angle sustentado",
                "suggested_lane": "reserva",
                "evidence_refs": ["event-a"],
                "candidate_item_ids": ["candidate-a"],
            }],
        })
        self.assertEqual(valid.decisions[0].candidate_item_ids, ("candidate-a",))

        with self.assertRaisesRegex(RadarStoreError, "candidato ausente"):
            resolve_triage_output(batch, {
                "no_change": False,
                "decisions": [{
                    "candidate_angle": "Angle sustentado",
                    "suggested_lane": "reserva",
                    "evidence_refs": ["event-a"],
                    "candidate_item_ids": ["candidate-not-in-batch"],
                }],
            })

    def test_conflicting_decisions_for_same_candidate_are_rejected(self) -> None:
        with self.assertRaisesRegex(RadarStoreError, "mesmo candidate_item_id"):
            resolve_triage_output(batch_value(), {
                "no_change": False,
                "decisions": [
                    {"candidate_angle": "a", "suggested_lane": "principal", "evidence_refs": ["event-a"]},
                    {"candidate_angle": "b", "suggested_lane": "descartar", "evidence_refs": ["candidate-a"]},
                ],
            })

    def test_inconsistent_no_change_flag_is_rejected(self) -> None:
        with self.assertRaisesRegex(RadarStoreError, "no_change junto"):
            resolve_triage_output(batch_value(), {
                "no_change": True,
                "decisions": [{"candidate_angle": "a", "suggested_lane": "monitoramento", "evidence_refs": ["event-a"]}],
            })


if __name__ == "__main__":
    unittest.main()
