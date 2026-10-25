"""Offline E18 preparation: bind persona references without model outputs."""

from __future__ import annotations

import json
import uuid
import unittest
from pathlib import Path

from motor_editorial.agent_contracts import (
    AgentRoleProfile,
    AgentTaskEnvelope,
    ContractValidationError,
    load_builtin_role_catalog,
)
from motor_editorial.db import json_dumps, stable_hash


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "persona_trials_offline_v1.json"
ROLE_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "agent_role_fixtures_v1.json"
CASE_IDS = [f"T{index:02d}" for index in range(1, 17)]
CANONICAL_PERSONA_IDS = {"ranzinza", "beto-cartucho", "nina-prisma"}


def make_persona_envelope(
    profile: AgentRoleProfile,
    input_value: dict,
    *,
    persona_id: str,
    persona_version: str,
    persona_instructions: str,
) -> AgentTaskEnvelope:
    task_id = str(uuid.uuid4())
    return AgentTaskEnvelope.from_mapping({
        "schema_version": "1.0",
        "task_id": task_id,
        "run_id": "e18-offline-binding",
        "story_id": f"story:{persona_id}",
        "role_id": profile.role_id,
        "role_version": profile.role_version,
        "role_hash": profile.content_hash,
        "input_payload_hash": stable_hash(json_dumps(input_value)),
        "persona_id": persona_id,
        "persona_version": persona_version,
        "persona_hash": stable_hash(persona_instructions),
        "input_artifact_refs": [{"ref": "artifact://e18/input", "sha256": "a" * 64}],
        "source_snapshot_ids": ["snapshot://e18/synthetic"],
        "authorized_tools": [profile.allowed_tools[0].to_dict()],
        "context_schema_version": "1.0",
        "usage_guardrails": {"max_calls": 1, "max_iterations": 1},
        "idempotency_key": f"e18:{persona_id}:{task_id}",
        "correlation_id": f"e18:{persona_id}",
        "requires_human_gate": True,
    })


class PersonaTrialsOfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.role_fixtures = json.loads(ROLE_FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.catalog = load_builtin_role_catalog()
        cls.writer = next(
            item for item in cls.catalog.to_mapping()["profiles"]
            if item["role_id"] == "persona_writer"
        )
        cls.profile = AgentRoleProfile.from_mapping(cls.writer)
        cls.input_value = cls.role_fixtures["roles"]["persona_writer"]["input"]

    def test_all_three_isolated_matrices_are_explicitly_not_executed(self) -> None:
        self.assertEqual(self.manifest["fixture_version"], "1.0")
        self.assertEqual(self.manifest["execution_mode"], "offline_contract_binding_only")
        personas = self.manifest["personas"]
        self.assertEqual({item["persona_id"] for item in personas}, CANONICAL_PERSONA_IDS)
        self.assertEqual(len(personas), 3)
        for persona in personas:
            with self.subTest(persona_id=persona["persona_id"]):
                self.assertEqual(persona["case_ids"], CASE_IDS)
                self.assertEqual(persona["execution_status"], "not_executed")
                self.assertEqual(persona["persona_axis_status"], "not_evaluated")
                self.assertEqual(persona["journalism_axis_status"], "not_evaluated")
                self.assertEqual(persona["human_review_status"], "pending_direction")
                self.assertRegex(persona["documentation_bundle_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(persona["source_commit"], r"^[0-9a-f]{40}$")

    def test_persona_instruction_hash_binds_only_the_referenced_isolated_identity(self) -> None:
        personas = self.manifest["personas"]
        for persona in personas:
            persona_id = persona["persona_id"]
            marker = f"OFFLINE_BINDING_SENTINEL::{persona_id}::{persona['documentation_bundle_sha256']}"
            envelope = make_persona_envelope(
                self.profile, self.input_value,
                persona_id=persona_id,
                persona_version="e18-offline-marker-v1",
                persona_instructions=marker,
            )
            context = self.catalog.prepare_invocation(
                envelope, input_payload=self.input_value, persona_instructions=marker,
            )
            persona_sections = [
                section for section in context.trusted_instruction_sections
                if section.source.startswith("persona:")
            ]
            self.assertEqual(len(persona_sections), 1)
            self.assertEqual(persona_sections[0].source, f"persona:{persona_id}")
            self.assertEqual(persona_sections[0].version, "e18-offline-marker-v1")
            self.assertEqual(persona_sections[0].text, marker)
            self.assertEqual(context.task_envelope.persona_hash, stable_hash(marker))

            other = next(item for item in personas if item["persona_id"] != persona_id)
            foreign_marker = f"OFFLINE_BINDING_SENTINEL::{other['persona_id']}::{other['documentation_bundle_sha256']}"
            with self.assertRaisesRegex(ContractValidationError, "Hash do DNA fornecido"):
                self.catalog.prepare_invocation(
                    envelope, input_payload=self.input_value, persona_instructions=foreign_marker,
                )

    def test_persona_writer_invocation_fails_closed_without_dna_instructions(self) -> None:
        envelope = make_persona_envelope(
            self.profile, self.input_value,
            persona_id="ranzinza",
            persona_version="e18-offline-marker-v1",
            persona_instructions="OFFLINE_BINDING_SENTINEL::ranzinza",
        )
        with self.assertRaisesRegex(ContractValidationError, "exige instruções do DNA versionado"):
            self.catalog.prepare_invocation(envelope, input_payload=self.input_value)


if __name__ == "__main__":
    unittest.main()
