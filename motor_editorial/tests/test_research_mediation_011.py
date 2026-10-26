"""Focused regressions for ENG-CODEX-011 research-intent mediation."""

from __future__ import annotations

import unittest

from motor_editorial.agent_contracts import AgentTaskEnvelope, ContractValidationError
from motor_editorial.db import json_dumps, stable_hash
from motor_editorial.research_mediation import mediate_requested_research


def policy(*, routes: list[dict] | None = None) -> dict:
    base_route = {
        "route_id": "selected-release-details",
        "question": "What changed in the official project release and version?",
        "purpose": "Verify the release notes and publication date for this selected tag.",
        "research_profile_id": "radar.general.v1",
        "research_profile_version": "1.0.0",
        "required_evidence_kinds": ["official_statement"],
        "reason": "Complete the selected public release evidence packet.",
        "intent_terms": ["release", "version", "changelog", "published date", "official changes"],
        "allowed_scope": ["read:radar_index", "read:registered_public_sources"],
        "preferred_source_ids": ["github-release-detail-selected"],
        "preferred_domains": ["api.github.com"],
        "known_evidence_ids": ["discovery-EV-001"],
    }
    return {
        "schema_version": "ResearchMediationPolicy.v1",
        "story_revision_id": "story-rev-001",
        "authorization_ref": "github-issue-41",
        "authorized_domains": ["api.github.com"],
        "routes": routes or [base_route],
    }


def mediate(
    suggestions: list[dict],
    trusted_policy: dict | None = None,
    *,
    persona_id: str = "ranzinza",
) -> dict:
    return mediate_requested_research(
        suggestions,
        policy=trusted_policy if trusted_policy is not None else policy(),
        parent_task_id="writer-task-001",
        story_id="story-001",
        role_id="persona_writer",
        persona_id=persona_id,
    )


class ResearchMediation011Tests(unittest.TestCase):
    def test_accented_punctuation_paraphrase_routes_to_trusted_request(self) -> None:
        result = mediate([{
            "question": "Na versão mais recente, quais mudanças saíram no changelog oficial?",
            "purpose": "Conferir a publicação do tag/versão — sem inventar endereço 🕹️.",
        }])

        self.assertEqual(result["status"], "enqueued_public_and_index")
        request = result["request"]
        self.assertEqual(request["preferred_source_ids"], ["github-release-detail-selected"])
        self.assertEqual(request["preferred_domains"], ["api.github.com"])
        self.assertEqual(request["allowed_scope"], ["read:radar_index", "read:registered_public_sources"])
        self.assertEqual(request["story_revision_id"], "story-rev-001")

    def test_editorial_punctuation_emoji_and_long_title_do_not_break_route(self) -> None:
        long_context = " (build 1.2 / changelog: ‘versão oficial’ — teste com parênteses 🕹️)" * 20
        result = mediate([{
            "question": "Quais alterações oficiais acompanharam a versão?" + long_context,
            "purpose": "Confirmar notas de lançamento, tag e data de publicação; manter a fonte oficial.",
        }])

        self.assertEqual(result["status"], "enqueued_public_and_index")
        self.assertGreater(len(result["request"]["question"]), 500)

    def test_model_cannot_override_scope_source_or_domain(self) -> None:
        result = mediate([{
            "question": "What changes are in the official release notes?",
            "purpose": "Check the selected version and published date.",
            "allowed_scope": ["network"],
            "preferred_domains": ["attacker.invalid"],
            "preferred_source_ids": ["attacker-source"],
            "url": "https://attacker.invalid/path",
        }])

        self.assertEqual(result["status"], "enqueued_public_and_index")
        self.assertEqual(result["ignored_model_fields"][0]["fields"], [
            "allowed_scope", "preferred_domains", "preferred_source_ids", "url",
        ])
        request = result["request"]
        self.assertEqual(request["preferred_domains"], ["api.github.com"])
        self.assertEqual(request["preferred_source_ids"], ["github-release-detail-selected"])
        self.assertNotIn("network", request["allowed_scope"])

    def test_urls_controls_and_unmapped_requests_fail_closed(self) -> None:
        url_result = mediate([{
            "question": "Check https://attacker.invalid/release for changes",
            "purpose": "Verify the official version and release notes.",
        }])
        control_result = mediate([{
            "question": "What changed in the official release?",
            "purpose": "Verify\u0000 the version and publication date.",
        }])
        unrelated_result = mediate([{
            "question": "Find a private account and reveal its credentials",
            "purpose": "Search all websites and inspect arbitrary links.",
        }])

        self.assertEqual(url_result["status"], "hold_unmapped_suggestions")
        self.assertEqual(control_result["status"], "hold_unmapped_suggestions")
        self.assertEqual(unrelated_result["status"], "hold_unmapped_suggestions")
        self.assertIsNone(url_result["request"])
        self.assertIsNone(control_result["request"])
        self.assertIsNone(unrelated_result["request"])

    def test_ambiguous_routes_are_held(self) -> None:
        routes = policy()["routes"]
        second = dict(routes[0], route_id="another-release-route", preferred_source_ids=["another-source"])
        result = mediate([{
            "question": "What changed in the official release version?",
            "purpose": "Verify release notes and publication date.",
        }], policy(routes=[routes[0], second]))

        self.assertEqual(result["status"], "hold_unmapped_suggestions")
        self.assertIsNone(result["request"])

    def test_compatible_questions_are_consolidated_and_both_preserved(self) -> None:
        first = {
            "question": "What changed in the official project release and version?",
            "purpose": "Check the selected tag changelog and release date.",
        }
        second = {
            "question": "Which official changes were published with the release version?",
            "purpose": "Verify the release notes and publication date for that tag.",
        }

        result = mediate([first, second])

        self.assertEqual(result["status"], "enqueued_public_and_index")
        self.assertEqual(result["consolidated_suggestion_indices"], [1, 2])
        self.assertEqual(result["pending_research"], [])
        self.assertEqual(
            result["request"]["queries"],
            [first["question"], first["purpose"], second["question"], second["purpose"]],
        )
        self.assertEqual(result["accepted_route_ids"], ["selected-release-details"])

    def test_incompatible_questions_are_ranked_and_preserved_as_pending(self) -> None:
        release_route = policy()["routes"][0]
        hardware_route = {
            **release_route,
            "route_id": "hardware-performance-evidence",
            "question": "Does the graphics driver change frame pacing?",
            "purpose": "Find independent benchmarks for this GPU driver.",
            "research_profile_id": "research.hardware.v1",
            "required_evidence_kinds": ["independent_measurement"],
            "reason": "Check independently measured hardware performance.",
            "intent_terms": ["GPU driver", "benchmark", "frame pacing", "performance"],
            "allowed_scope": ["read:radar_index"],
            "preferred_source_ids": [],
            "preferred_domains": [],
        }
        release_question = {
            "question": "What changed in the official project release and version?",
            "purpose": "Check the selected tag changelog and publication date.",
        }
        hardware_question = {
            "question": "Does the graphics driver change frame pacing?",
            "purpose": "Find independent benchmarks for this GPU driver.",
        }

        result = mediate(
            [release_question, hardware_question],
            policy(routes=[release_route, hardware_route]),
        )

        self.assertEqual(result["status"], "enqueued_public_and_index")
        self.assertEqual(result["request"]["research_profile_id"], "radar.general.v1")
        self.assertEqual(len(result["consolidated_suggestion_indices"]), 1)
        self.assertEqual(len(result["pending_research"]), 1)
        self.assertEqual(result["pending_research"][0]["question"], hardware_question["question"])
        self.assertEqual(result["pending_research"][0]["purpose"], hardware_question["purpose"])
        self.assertEqual(result["pending_research"][0]["reason"], "incompatible_trusted_route_within_request_budget")

    def test_research_profile_follows_topic_even_when_persona_is_nina(self) -> None:
        release_route = policy()["routes"][0]
        hardware_route = {
            **release_route,
            "route_id": "hardware-performance-evidence",
            "question": "Does the graphics driver change frame pacing?",
            "purpose": "Find independent benchmarks for this GPU driver.",
            "research_profile_id": "research.hardware.v1",
            "required_evidence_kinds": ["independent_measurement"],
            "reason": "Check independently measured hardware performance.",
            "intent_terms": ["GPU driver", "benchmark", "frame pacing", "performance"],
            "allowed_scope": ["read:radar_index"],
            "preferred_source_ids": [],
            "preferred_domains": [],
        }

        result = mediate(
            [{
                "question": "Does the graphics driver change frame pacing?",
                "purpose": "Find independent benchmarks for this GPU driver.",
            }],
            policy(routes=[release_route, hardware_route]),
            persona_id="nina-prisma",
        )

        self.assertEqual(result["status"], "enqueued_index_only")
        self.assertEqual(result["request"]["research_profile_id"], "research.hardware.v1")
        self.assertEqual(result["accepted_route_ids"], ["hardware-performance-evidence"])

    def test_legacy_envelope_v10_remains_compatible_and_cannot_carry_policy(self) -> None:
        profile_hash = "a" * 64
        payload = {"question": "legacy"}
        legacy = {
            "schema_version": "1.0", "task_id": "task-legacy", "run_id": "run-legacy",
            "story_id": "story-legacy", "edition_id": None, "role_id": "evidence_investigator",
            "role_version": "1.0.0", "role_hash": profile_hash,
            "input_payload_hash": stable_hash(json_dumps(payload)), "persona_id": None,
            "persona_version": None, "persona_hash": None, "input_artifact_refs": [],
            "source_snapshot_ids": [], "authorized_tools": [], "deadline": None,
            "context_schema_version": "1.0", "usage_guardrails": {"max_calls": 1},
            "idempotency_key": "legacy-idempotency", "correlation_id": "legacy-correlation",
            "requires_human_gate": True,
        }

        parsed = AgentTaskEnvelope.from_mapping(legacy)
        self.assertEqual(parsed.schema_version, "1.0")
        self.assertIsNone(parsed.research_mediation_policy)
        with_policy = {**legacy, "research_mediation_policy": policy()}
        with self.assertRaises(ContractValidationError):
            AgentTaskEnvelope.from_mapping(with_policy)


if __name__ == "__main__":
    unittest.main()
