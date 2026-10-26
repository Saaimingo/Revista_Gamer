from __future__ import annotations

import copy
import unittest

from motor_editorial.research_mediation import (
    MAX_BYTES,
    MAX_DURATION_SECONDS,
    MAX_REQUESTS,
    MAX_SOURCES,
    POLICY_SCHEMA_VERSION,
    mediate_requested_research,
    validate_policy,
)
from motor_editorial.research_service import RADAR_INDEX_SCOPE


def route(
    route_id: str,
    question: str,
    purpose: str,
    *,
    profile: str = "research.games.v1",
    kinds: list[str] | None = None,
) -> dict:
    return {
        "route_id": route_id,
        "question": question,
        "purpose": purpose,
        "research_profile_id": profile,
        "research_profile_version": "1.0.0",
        "required_evidence_kinds": kinds or ["official_statement"],
        "reason": f"Brief exige apurar {route_id}.",
        "entity_ids": ["re:requiem"],
        "preferred_source_ids": [],
        "preferred_domains": [],
        "languages": ["pt-BR", "en"],
        "time_window": {},
        "versions_configurations": {},
        "known_evidence_ids": [],
        "exclusions": [],
    }


def policy(routes: list[dict]) -> dict:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "story_revision_id": "story-requiem-r1",
        "routes": routes,
    }


def mediate(suggestions: list[dict], motor_policy: dict | None = None, *, task_id: str = "task-research-001") -> dict:
    return mediate_requested_research(
        suggestions,
        policy=motor_policy,
        parent_task_id=task_id,
        story_id="story-requiem",
        role_id="persona_writer",
        persona_id="beto-cartucho",
    )


class ResearchMediationTests(unittest.TestCase):
    def test_one_exact_brief_route_becomes_bounded_index_only_request(self) -> None:
        approved = route("brief-launch", "Qual data oficial foi confirmada para o lançamento?", "confirmar anúncio oficial")
        result = mediate([{"question": approved["question"], "purpose": approved["purpose"]}], policy([approved]))

        self.assertEqual(result["status"], "enqueued_index_only")
        request = result["request"]
        self.assertEqual(request["schema_version"], "1.1")
        self.assertEqual(request["queries"], [approved["question"]])
        self.assertEqual(request["required_evidence_kinds"], ["official_statement"])
        self.assertEqual(request["allowed_scope"], [RADAR_INDEX_SCOPE])
        self.assertEqual(request["human_gate_if_sensitive"], False)
        self.assertEqual(request["max_sources"], MAX_SOURCES)
        self.assertEqual(request["max_requests"], MAX_REQUESTS)
        self.assertEqual(request["max_bytes"], MAX_BYTES)
        self.assertEqual(request["max_duration_seconds"], MAX_DURATION_SECONDS)
        self.assertEqual(result["suggestions"][0]["question"], approved["question"])

    def test_two_compatible_routes_consolidate_into_one_request(self) -> None:
        first = route("brief-launch", "Qual data oficial foi confirmada para o lançamento?", "confirmar anúncio oficial")
        second = route("brief-platform", "Quais plataformas foram anunciadas oficialmente?", "confirmar lista oficial de plataformas")
        result = mediate([
            {"question": first["question"], "purpose": first["purpose"]},
            {"question": second["question"], "purpose": second["purpose"]},
        ], policy([first, second]))

        self.assertEqual(result["status"], "enqueued_index_only")
        self.assertEqual(result["accepted_route_ids"], ["brief-launch", "brief-platform"])
        self.assertEqual(result["request"]["queries"], [first["question"], second["question"]])
        self.assertEqual(result["request"]["max_requests"], 1)

    def test_incompatible_route_is_preserved_as_pending_without_a_second_request(self) -> None:
        first = route("brief-launch", "Qual data oficial foi confirmada para o lançamento?", "confirmar anúncio oficial")
        second = route(
            "brief-benchmark", "Qual medição independente informa a taxa de quadros?", "localizar benchmark independente",
            profile="research.hardware.v1", kinds=["independent_measurement"],
        )
        result = mediate([
            {"question": first["question"], "purpose": first["purpose"]},
            {"question": second["question"], "purpose": second["purpose"]},
        ], policy([first, second]))

        self.assertEqual(result["status"], "partial_index_only_pending")
        self.assertEqual(result["request"]["queries"], [first["question"]])
        self.assertEqual(result["pending_research"], [{
            "suggestion_index": 2,
            "route_id": "brief-benchmark",
            "reason": "incompatible_profile_or_evidence_kinds",
        }])

    def test_unmapped_or_ambiguous_suggestions_hold_instead_of_guessing(self) -> None:
        approved = route("brief-launch", "Qual data oficial foi confirmada para o lançamento?", "confirmar anúncio oficial")
        result = mediate([{"question": "Buscar notícias recentes", "purpose": "pesquisar"}], policy([approved]))

        self.assertEqual(result["status"], "hold_unmapped_suggestions")
        self.assertIsNone(result["request"])
        self.assertEqual(result["pending_research"][0]["reason"], "no_exact_brief_route_match")

    def test_model_supplied_scope_and_evidence_fields_are_ignored(self) -> None:
        approved = route("brief-launch", "Qual data oficial foi confirmada para o lançamento?", "confirmar anúncio oficial")
        suggestion = {
            "question": approved["question"],
            "purpose": approved["purpose"],
            "allowed_scope": ["read:registered_public_sources"],
            "required_evidence_kinds": ["editorial_interpretation"],
        }
        result = mediate([suggestion], policy([approved]))

        self.assertEqual(result["request"]["allowed_scope"], [RADAR_INDEX_SCOPE])
        self.assertEqual(result["request"]["required_evidence_kinds"], ["official_statement"])
        self.assertEqual(result["ignored_model_fields"][0]["fields"], ["allowed_scope", "required_evidence_kinds"])

    def test_duplicate_pairs_and_replays_produce_one_deterministic_request(self) -> None:
        approved = route("brief-launch", "Qual data oficial foi confirmada para o lançamento?", "confirmar anúncio oficial")
        suggestion = {"question": approved["question"], "purpose": approved["purpose"]}
        duplicate = {"question": approved["question"].upper(), "purpose": approved["purpose"]}
        result = mediate([suggestion, duplicate], policy([approved]))
        replay = mediate([suggestion], policy([approved]))

        self.assertEqual(result["status"], "enqueued_index_only")
        self.assertEqual(len(result["request"]["queries"]), 1)
        self.assertEqual(result["request"]["request_id"], replay["request"]["request_id"])
        self.assertEqual(result["deduplicated_suggestions"], [2])

    def test_missing_policy_or_wrong_role_never_creates_a_request(self) -> None:
        suggestion = {"question": "Pergunta", "purpose": "Finalidade"}
        no_policy = mediate([suggestion])
        self.assertEqual(no_policy["status"], "hold_missing_motor_policy")
        self.assertIsNone(no_policy["request"])

        raw = policy([route("q1", "Pergunta", "Finalidade")])
        wrong_role = mediate_requested_research(
            [suggestion], policy=raw, parent_task_id="task-x", story_id="story-x",
            role_id="fact_checker", persona_id=None,
        )
        self.assertEqual(wrong_role["status"], "hold_invalid_motor_policy")
        self.assertIsNone(wrong_role["request"])

    def test_unknown_profile_or_epistemic_kind_is_rejected_in_preflight(self) -> None:
        invalid = policy([route("q1", "Pergunta", "Finalidade", profile="research.unknown.v1")])
        with self.assertRaisesRegex(ValueError, "perfil não registrado"):
            validate_policy(invalid, story_id="story-requiem", role_id="persona_writer", persona_id="beto-cartucho")

        invalid_kind = copy.deepcopy(policy([route("q1", "Pergunta", "Finalidade")]))
        invalid_kind["routes"][0]["required_evidence_kinds"] = ["unverified_kind"]
        with self.assertRaisesRegex(ValueError, "tipo epistêmico"):
            validate_policy(invalid_kind, story_id="story-requiem", role_id="persona_writer", persona_id="beto-cartucho")


if __name__ == "__main__":
    unittest.main()
