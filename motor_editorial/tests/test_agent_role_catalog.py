"""Offline fixtures for the six enabled roles and two optional disabled profiles."""

from __future__ import annotations

import json
import unittest
import uuid
from pathlib import Path

from motor_editorial.agent_contracts import (
    AgentRoleCatalog,
    AgentRoleProfile,
    AgentTaskEnvelope,
    ContractValidationError,
    load_builtin_role_catalog,
    validate_json_schema,
)
from motor_editorial.db import json_dumps, stable_hash


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "agent_role_fixtures_v1.json"
ENABLED_ROLES = {
    "triage_analyst", "evidence_investigator", "assignment_editor", "persona_writer",
    "fact_checker", "editorial_reviewer",
}
OPTIONAL_ROLES = {"media_researcher", "layout_planner"}


def role_profiles(catalog: AgentRoleCatalog) -> dict[str, AgentRoleProfile]:
    return {
        item["role_id"]: AgentRoleProfile.from_mapping(item)
        for item in catalog.to_mapping()["profiles"]
    }


def envelope_for(profile: AgentRoleProfile, input_value: dict, *, with_persona: bool) -> AgentTaskEnvelope:
    task_id = str(uuid.uuid4())
    persona = {
        "persona_id": "persona-fixture",
        "persona_version": "fixture-1",
        "persona_hash": "c" * 64,
    } if with_persona else {"persona_id": None, "persona_version": None, "persona_hash": None}
    tool = profile.allowed_tools[0]
    return AgentTaskEnvelope.from_mapping({
        "schema_version": "1.0", "task_id": task_id, "run_id": "run-fixture", "story_id": "story-fixture",
        "role_id": profile.role_id, "role_version": profile.role_version, "role_hash": profile.content_hash,
        "input_payload_hash": stable_hash(json_dumps(input_value)),
        "input_artifact_refs": [{"ref": "artifact://fixture/input", "sha256": "a" * 64}],
        "source_snapshot_ids": ["snapshot-fixture"],
        "authorized_tools": [tool.to_dict()], "context_schema_version": "1.0",
        "usage_guardrails": {"max_calls": 1, "max_iterations": 1},
        "idempotency_key": f"fixture:{task_id}", "correlation_id": "story-fixture:role-test",
        "requires_human_gate": True, **persona,
    })


class AgentRoleCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_builtin_role_catalog()
        cls.profiles = role_profiles(cls.catalog)
        cls.fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_catalog_registers_six_roles_and_two_optional_roles_as_disabled(self) -> None:
        self.assertEqual(set(self.catalog.enabled_role_ids), ENABLED_ROLES)
        self.assertEqual(set(self.catalog.disabled_role_ids), OPTIONAL_ROLES)
        self.assertEqual(set(self.profiles), ENABLED_ROLES | OPTIONAL_ROLES)
        self.assertEqual(self.fixtures["fixture_version"], "1.0")

    def test_each_role_has_pinned_instructions_schemas_prohibitions_and_fixture(self) -> None:
        refs = set(self.fixtures["roles"])
        self.assertEqual(refs, set(self.profiles))
        for role_id, profile in self.profiles.items():
            with self.subTest(role_id=role_id):
                self.assertEqual(profile.instructions_sha256, stable_hash(profile.instructions))
                self.assertTrue(profile.success_criteria)
                self.assertTrue(profile.excluded_actions)
                self.assertTrue(profile.quality_rubric)
                self.assertEqual(profile.evaluation_fixture_refs, (f"fixture://agent_roles/v1/{role_id}",))
                expected_output_version = "1.1.0" if role_id == "assignment_editor" else "1.0.0"
                self.assertEqual(profile.output_schema["version"], expected_output_version)
                self.assertTrue(profile.human_review_gate["required"])
                self.assertEqual(profile.allowed_model_policy["fallback"], "none")

    def test_valid_input_and_output_fixtures_pass_every_role_schema(self) -> None:
        for role_id, fixture in self.fixtures["roles"].items():
            profile = self.profiles[role_id]
            with self.subTest(role_id=role_id):
                validate_json_schema(fixture["input"], profile.input_schema)
                validate_json_schema(fixture["output"], profile.output_schema)

    def test_every_role_rejects_unknown_input_and_missing_required_output(self) -> None:
        for role_id, fixture in self.fixtures["roles"].items():
            profile = self.profiles[role_id]
            with self.subTest(role_id=role_id):
                bad_input = dict(fixture["input"])
                bad_input["unapproved_field"] = "unexpected"
                with self.assertRaises(ContractValidationError):
                    validate_json_schema(bad_input, profile.input_schema)
                bad_output = dict(fixture["output"])
                del bad_output[profile.output_schema["required"][0]]
                with self.assertRaises(ContractValidationError):
                    validate_json_schema(bad_output, profile.output_schema)

    def test_only_profiles_that_can_request_research_receive_the_tool(self) -> None:
        for role_id, profile in self.profiles.items():
            tool_ids = {tool.tool_id for tool in profile.allowed_tools}
            with self.subTest(role_id=role_id):
                self.assertEqual(profile.request_research_allowed, "motor.request_research" in tool_ids)
                self.assertNotIn("shell", tool_ids)
                self.assertNotIn("http.get", tool_ids)

    def test_disabled_optional_profiles_are_inspectable_but_not_dispatchable(self) -> None:
        layout = self.profiles["layout_planner"]
        self.assertEqual(
            self.catalog.resolve(layout.role_id, layout.role_version, layout.content_hash, allow_disabled=True),
            layout,
        )
        with self.assertRaisesRegex(ContractValidationError, "desligado"):
            self.catalog.resolve(layout.role_id, layout.role_version, layout.content_hash)
        envelope = envelope_for(layout, self.fixtures["roles"][layout.role_id]["input"], with_persona=False)
        with self.assertRaisesRegex(ContractValidationError, "desligado"):
            self.catalog.validate_task(envelope, input_payload=self.fixtures["roles"][layout.role_id]["input"])

    def test_persona_writer_requires_only_a_separate_persona_reference(self) -> None:
        profile = self.profiles["persona_writer"]
        input_value = self.fixtures["roles"][profile.role_id]["input"]
        missing_ref = envelope_for(profile, input_value, with_persona=False)
        with self.assertRaisesRegex(ContractValidationError, "exige referência imutável"):
            self.catalog.validate_task(missing_ref, input_payload=input_value)
        valid_ref = envelope_for(profile, input_value, with_persona=True)
        loaded = self.catalog.validate_task(valid_ref, input_payload=input_value)
        self.assertEqual(loaded.role_id, "persona_writer")
        self.assertEqual(valid_ref.persona_id, "persona-fixture")
        self.assertNotIn("persona-fixture", loaded.instructions)
        self.assertNotIn("nina-prisma", loaded.instructions)

    def test_catalog_configuration_round_trip_preserves_disabled_flags_and_hashes(self) -> None:
        restored = AgentRoleCatalog.from_mapping(self.catalog.to_mapping())
        self.assertEqual(restored.enabled_role_ids, self.catalog.enabled_role_ids)
        self.assertEqual(restored.disabled_role_ids, self.catalog.disabled_role_ids)
        for role_id, profile in self.profiles.items():
            self.assertEqual(
                restored.resolve(role_id, profile.role_version, profile.content_hash, allow_disabled=True).content_hash,
                profile.content_hash,
            )


if __name__ == "__main__":
    unittest.main()
