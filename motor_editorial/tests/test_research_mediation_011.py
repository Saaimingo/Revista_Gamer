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


def mediate(suggestions: list[dict], trusted_policy: dict | None = None) -> dict:
    return mediate_requested_research(
        suggestions,
        policy=trusted_policy if trusted_policy is not None else policy(),
        parent_task_id="writer-task-001",
        story_id="story-001",
        role_id="persona_writer",
        persona_id="ranzinza",
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
