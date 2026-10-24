from __future__ import annotations

import copy
import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from motor_editorial.db import Store
from motor_editorial.layout.contracts import (
    ContractError,
    SCHEMA_PLAN,
    profile_sha256,
    seal_artifact,
    story_revision_sha256,
    validate_composition_validation,
    validate_layout_plan,
    validate_layout_reference,
    validate_media_inventory,
    validate_story_package,
)
from motor_editorial.layout.engine import (
    build_visual_needs,
    plan_layout,
    validate_plan,
)
from motor_editorial.layout.index import LayoutReferenceIndex
from motor_editorial.layout.pipeline import (
    DEFAULT_FIXTURE,
    _materialize_inventory,
    _materialize_references,
    _materialize_story,
    _read_fixture,
)
from motor_editorial.workflow import Motor


class LayoutContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.fixture = _read_fixture(DEFAULT_FIXTURE)
        self.references = _materialize_references(self.fixture["references"])

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def build_case(self, index: int = 0):
        case = self.fixture["scenarios"][index]
        story = _materialize_story(case["story_package"])
        inventory = _materialize_inventory(case["media_inventory"])
        local_index = LayoutReferenceIndex(self.root / f"index-{index}.sqlite3")
        local_index.add_references(self.references)
        needs = build_visual_needs(story)
        selected = local_index.search(
            [tag for need in needs["needs"] for tag in need["tags"]], limit=3
        )
        plan = plan_layout(story, inventory, needs, selected, local_index.fingerprint())
        return story, inventory, local_index, plan

    def test_all_fixture_contracts_are_versioned_hashed_and_offline(self) -> None:
        for reference in self.references:
            self.assertEqual(validate_layout_reference(reference)["schema_version"], "LayoutReference.v0")
            self.assertEqual(reference["payload"]["rights_scope"], "metadata_only")
        for index, scenario in enumerate(self.fixture["scenarios"]):
            story = _materialize_story(scenario["story_package"])
            inventory = _materialize_inventory(scenario["media_inventory"])
            self.assertEqual(validate_story_package(story)["schema_version"], "StoryPackage.v0")
            self.assertEqual(validate_media_inventory(inventory)["schema_version"], "MediaInventory.v0")
            self.assertEqual(story["payload"]["review"]["reviewed_story_sha256"], story_revision_sha256(story["payload"]))
            self.assertIn("writer_persona", story["payload"]["identities"])
            self.assertEqual(story["payload"]["identities"]["writer_persona"]["role"], "writer_persona")
            self.assertTrue(all(asset["synthetic"] for asset in inventory["payload"]["assets"]))

    def test_reference_index_returns_three_relevant_metadata_records(self) -> None:
        for index in range(3):
            story, _, local_index, _ = self.build_case(index)
            needs = build_visual_needs(story)
            selected = local_index.search(
                [tag for need in needs["needs"] for tag in need["tags"]], limit=3
            )
            self.assertEqual(len(selected), 3)
            self.assertTrue(all(row["payload"]["source_type"] == "synthetic_fixture" for row in selected))
            self.assertTrue(all("image_path" not in row["payload"] for row in selected))

    def test_reference_index_searches_metadata_facets_and_limitations(self) -> None:
        local_index = LayoutReferenceIndex(self.root / "facets.sqlite3")
        local_index.add_references(self.references)

        function_matches = local_index.search(["function:captioned_editorial_images"], limit=9)
        era_matches = local_index.search(["era:fixture"], limit=9)
        orientation_matches = local_index.search(["orientation:portrait"], limit=9)
        affordance_matches = local_index.search(["affordance:caption-pairing"], limit=9)
        media_matches = local_index.search(["media:editorial-image"], limit=9)
        limitation_matches = local_index.search(["limit:página"], limit=9)

        self.assertEqual(
            [row["payload"]["reference_id"] for row in function_matches],
            ["reference-reportage-small-figures"],
        )
        self.assertEqual(len(era_matches), len(self.references))
        self.assertIn("reference-reportage-small-figures", [
            row["payload"]["reference_id"] for row in orientation_matches
        ])
        self.assertIn("reference-reportage-small-figures", [
            row["payload"]["reference_id"] for row in affordance_matches
        ])
        self.assertIn("reference-reportage-small-figures", [
            row["payload"]["reference_id"] for row in media_matches
        ])
        self.assertEqual(len(limitation_matches), len(self.references))

    def test_plan_is_rejected_after_the_story_revision_changes(self) -> None:
        story, inventory, local_index, plan = self.build_case(0)
        changed_payload = copy.deepcopy(story["payload"])
        changed_payload["story_revision"] = 2
        changed_payload["sections"][0]["text"] = "Texto atualizado na revisão seguinte."
        changed_payload["review"]["reviewed_story_sha256"] = story_revision_sha256(changed_payload)
        changed_story = seal_artifact(
            story["artifact_id"], "StoryPackage.v0", 2, changed_payload
        )
        validation = validate_composition_validation(validate_plan(
            changed_story, inventory, plan, local_index.fingerprint(), local_index.references()
        ))
        self.assertEqual(validation["payload"]["status"], "FAIL")
        self.assertEqual(
            next(check["status"] for check in validation["payload"]["checks"]
                 if check["check_id"] == "story_revision_current"),
            "FAIL",
        )

    def test_rehashed_plan_must_preserve_story_order_and_sequence(self) -> None:
        story, inventory, local_index, plan = self.build_case(0)
        mutations = []

        reordered_payload = copy.deepcopy(plan["payload"])
        reordered_payload["block_placements"].reverse()
        for sequence, placement in enumerate(reordered_payload["block_placements"], start=1):
            placement["sequence"] = sequence
        mutations.append(reordered_payload)

        resequenced_payload = copy.deepcopy(plan["payload"])
        placements = resequenced_payload["block_placements"]
        placements[0]["sequence"], placements[1]["sequence"] = (
            placements[1]["sequence"], placements[0]["sequence"]
        )
        mutations.append(resequenced_payload)

        for payload in mutations:
            with self.subTest(placements=payload["block_placements"]):
                tampered_plan = seal_artifact(
                    plan["artifact_id"], SCHEMA_PLAN, plan["revision"], payload
                )
                # A valid new envelope hash must not legitimize semantic reordering.
                validate_layout_plan(tampered_plan)
                validation = validate_composition_validation(validate_plan(
                    story, inventory, tampered_plan,
                    local_index.fingerprint(), local_index.references(),
                ))
                check_status = {
                    check["check_id"]: check["status"]
                    for check in validation["payload"]["checks"]
                }
                self.assertEqual(validation["payload"]["status"], "FAIL")
                self.assertEqual(check_status.get("editorial_order_and_sequence"), "FAIL")

    def test_plan_role_identity_hashes_use_the_canonical_profile_rule(self) -> None:
        story, inventory, local_index, _ = self.build_case(0)
        story_payload = copy.deepcopy(story["payload"])
        # This StoryPackage extension is included in its revision hash but is not
        # part of the canonical identity fields hashed by profile_sha256().
        story_payload["identities"]["writer_persona"]["fixture_note"] = "metadata-only"
        story_payload["review"]["reviewed_story_sha256"] = story_revision_sha256(story_payload)
        story_with_metadata = validate_story_package(seal_artifact(
            story["artifact_id"], story["schema_version"], story["revision"], story_payload
        ))
        needs = build_visual_needs(story_with_metadata)
        references = local_index.search(
            [tag for need in needs["needs"] for tag in need["tags"]], limit=3
        )
        plan = plan_layout(
            story_with_metadata, inventory, needs, references, local_index.fingerprint()
        )

        expected_sources = {}
        for role in ("editor", "writer_persona", "reviewer"):
            identity = story_payload["identities"][role]
            expected_sources[role] = {
                "profile_id": identity["profile_id"],
                "version": identity["version"],
                "profile_sha256": profile_sha256(identity),
            }
        self.assertEqual(plan["payload"]["source_role_identities"], expected_sources)
        validation = validate_composition_validation(validate_plan(
            story_with_metadata, inventory, plan,
            local_index.fingerprint(), local_index.references(),
        ))
        self.assertEqual(validation["payload"]["status"], "PASS")

    def test_rehashed_plan_rejects_missing_or_divergent_source_role_identities(self) -> None:
        story, inventory, local_index, plan = self.build_case(0)
        roles = ("editor", "writer_persona", "reviewer")
        mutations = []
        for role in roles:
            for field, value in (
                ("profile_id", f"different-{role}"),
                ("version", "99.0.0"),
                ("profile_sha256", "0" * 64),
            ):
                payload = copy.deepcopy(plan["payload"])
                payload["source_role_identities"][role][field] = value
                mutations.append((role, field, payload))
        missing_payload = copy.deepcopy(plan["payload"])
        missing_payload["source_role_identities"].pop("writer_persona")
        mutations.append(("writer_persona", "missing", missing_payload))

        for role, field, payload in mutations:
            with self.subTest(role=role, field=field):
                tampered_plan = seal_artifact(
                    plan["artifact_id"], SCHEMA_PLAN, plan["revision"], payload
                )
                validate_layout_plan(tampered_plan)
                validation = validate_composition_validation(validate_plan(
                    story, inventory, tampered_plan,
                    local_index.fingerprint(), local_index.references(),
                ))
                check_status = {
                    check["check_id"]: check["status"]
                    for check in validation["payload"]["checks"]
                }
                self.assertEqual(validation["payload"]["status"], "FAIL")
                self.assertEqual(
                    check_status.get("source_role_identities_match_story_package"), "FAIL"
                )

    def test_unlicensed_or_advertising_asset_blocks_editorial_composition(self) -> None:
        story, inventory, local_index, plan = self.build_case(0)
        changed_payload = copy.deepcopy(inventory["payload"])
        changed_payload["assets"][0]["media_kind"] = "advertising"
        changed_payload["assets"][0]["rights_status"] = "pending"
        changed_inventory = seal_artifact(
            inventory["artifact_id"], "MediaInventory.v0", inventory["revision"], changed_payload
        )
        validation = validate_composition_validation(validate_plan(
            story, changed_inventory, plan, local_index.fingerprint(), local_index.references()
        ))
        check_status = {
            check["check_id"]: check["status"] for check in validation["payload"]["checks"]
        }
        self.assertEqual(validation["payload"]["status"], "FAIL")
        self.assertEqual(check_status["media_rights_gate"], "FAIL")
        self.assertEqual(check_status["advertising_separated"], "FAIL")

    def test_license_and_rights_status_must_match_the_preview_mode(self) -> None:
        story, inventory, local_index, _ = self.build_case(0)
        needs = build_visual_needs(story)
        references = local_index.search(
            [tag for need in needs["needs"] for tag in need["tags"]], limit=3
        )
        cases = (
            ("pending", "authorized", ["internal_preview"]),
            ("authorized", "pending", ["internal_preview"]),
            ("authorized", "authorized", []),
        )
        for license_status, rights_status, permitted_modes in cases:
            with self.subTest(
                license_status=license_status,
                rights_status=rights_status,
                permitted_modes=permitted_modes,
            ):
                inventory_payload = copy.deepcopy(inventory["payload"])
                asset = inventory_payload["assets"][0]
                asset.update({
                    "media_kind": "editorial",
                    "rights_status": rights_status,
                    "synthetic": False,
                    "asset_sha256": "a" * 64,
                    "dimensions": {"width": 640, "height": 360},
                    "license": {"status": license_status, "evidence": "fixture synthetic"},
                    "permitted_modes": permitted_modes,
                })
                changed_inventory = validate_media_inventory(seal_artifact(
                    inventory["artifact_id"], "MediaInventory.v0",
                    inventory["revision"], inventory_payload,
                ))
                plan = plan_layout(
                    story, changed_inventory, needs, references, local_index.fingerprint()
                )
                validation = validate_composition_validation(validate_plan(
                    story, changed_inventory, plan,
                    local_index.fingerprint(), local_index.references(),
                ))
                check_status = {
                    check["check_id"]: check["status"]
                    for check in validation["payload"]["checks"]
                }
                self.assertEqual(validation["payload"]["status"], "FAIL")
                self.assertEqual(check_status["media_rights_gate"], "FAIL")

    def test_unknown_license_status_is_not_accepted_by_the_contract(self) -> None:
        _, inventory, _, _ = self.build_case(0)
        inventory_payload = copy.deepcopy(inventory["payload"])
        inventory_payload["assets"][0]["license"]["status"] = "arbitrary text"
        changed_inventory = seal_artifact(
            inventory["artifact_id"], "MediaInventory.v0",
            inventory["revision"], inventory_payload,
        )
        with self.assertRaises(ContractError):
            validate_media_inventory(changed_inventory)

    def test_missing_references_and_spread_mobile_fallback_fail_validation(self) -> None:
        story, inventory, local_index, plan = self.build_case(1)
        missing = validate_composition_validation(validate_plan(
            story, inventory, plan, local_index.fingerprint(), []
        ))
        self.assertEqual(missing["payload"]["status"], "FAIL")
        self.assertEqual(
            next(check["status"] for check in missing["payload"]["checks"]
                 if check["check_id"] == "three_references_present"),
            "FAIL",
        )

        plan_payload = copy.deepcopy(plan["payload"])
        plan_payload["layouts"]["mobile"]["fallback"] = ""
        broken_plan = seal_artifact(plan["artifact_id"], SCHEMA_PLAN, plan["revision"], plan_payload)
        no_fallback = validate_composition_validation(validate_plan(
            story, inventory, broken_plan, local_index.fingerprint(), local_index.references()
        ))
        self.assertEqual(no_fallback["payload"]["status"], "FAIL")
        self.assertEqual(
            next(check["status"] for check in no_fallback["payload"]["checks"]
                 if check["check_id"] == "spread_mobile_fallback"),
            "FAIL",
        )


class LayoutMotorIntegrationTests(unittest.TestCase):
    def test_motor_runs_three_scenarios_offline_and_reuses_completed_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = Store(root / "motor.sqlite3", root / "artifacts")
            motor = Motor(store)
            first = motor.run_layout_demo()
            self.assertEqual(first["status"], "awaiting_approval")
            self.assertEqual(first["scenario_count"], 3)
            self.assertTrue(all(row["status"] == "PASS" for row in first["scenario_results"]))
            self.assertEqual(first["network_calls"], 0)
            self.assertEqual(first["siwc_calls"], 0)
            self.assertEqual(first["paid_api_calls"], 0)
            self.assertFalse(first["published"])

            for scenario in first["scenario_results"]:
                self.assertEqual(len(scenario["reference_ids"]), 3)
                self.assertTrue(Path(scenario["plan_path"]).is_file())
                self.assertTrue(Path(scenario["validation_path"]).is_file())
                validation_payload = json.loads(
                    Path(scenario["validation_path"]).read_text(encoding="utf-8")
                )["payload"]
                self.assertTrue(all(check["status"] == "PASS" for check in validation_payload["checks"]))
                preview_path = Path(scenario["preview_path"])
                self.assertTrue(preview_path.is_file())
                preview = preview_path.read_text(encoding="utf-8")
                self.assertIn("SIMULAÇÃO INTERNA — NÃO PUBLICAR", preview)
                self.assertIn("Alternar para leitura contínua", preview)
                self.assertNotIn("<img", preview)
                self.assertNotIn("https://", preview)
                self.assertNotIn("overflow:hidden", preview)
                if scenario["scenario_id"] != "reportagem-duas-imagens":
                    self.assertIn('data-page-number="2"', preview)
                    self.assertIn('data-page-number="3"', preview)
                    self.assertIn("grid-template-columns:repeat(2,minmax(0,1fr))", preview)
                    self.assertIn("girar o aparelho", preview)
                    self.assertIn("rotação estiver bloqueada", preview)
                if scenario["scenario_id"] == "mapa-panoramico-spread":
                    self.assertIn("Ampliar mapa", preview)
                    self.assertIn("overflow:auto", preview)

            reportagem = next(
                row for row in first["scenario_results"]
                if row["scenario_id"] == "reportagem-duas-imagens"
            )
            article_html = Path(reportagem["preview_path"]).read_text(encoding="utf-8")
            self.assertIn("Visão geral fictícia do circuito de teste.", article_html)
            self.assertIn("Curva ilustrativa criada para o cenário de ensaio.", article_html)
            plan_payload = self._read_plan(reportagem)["payload"]
            self.assertEqual(
                plan_payload["source_role_identities"]["writer_persona"]["profile_id"],
                "fixture-gamer-persona",
            )
            self.assertEqual(len(plan_payload["references"]), 3)

            with closing(store.connect()) as connection:
                before = connection.execute(
                    "SELECT COUNT(*) FROM execution_attempts WHERE run_id = ?",
                    (first["run_id"],),
                ).fetchone()[0]
            second = motor.run_layout_demo()
            with closing(store.connect()) as connection:
                after = connection.execute(
                    "SELECT COUNT(*) FROM execution_attempts WHERE run_id = ?",
                    (second["run_id"],),
                ).fetchone()[0]
            self.assertEqual(before, after)

    def test_motor_replans_when_a_story_revision_hash_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture_path = root / "layout-demo.json"
            fixture_path.write_bytes(DEFAULT_FIXTURE.read_bytes())
            store = Store(root / "motor.sqlite3", root / "artifacts")
            motor = Motor(store)

            first = motor.run_layout_demo(fixture_path)
            first_story = first["scenario_results"][0]
            with closing(store.connect()) as connection:
                attempts_before = connection.execute(
                    "SELECT COUNT(*) FROM execution_attempts WHERE run_id = ?",
                    (first["run_id"],),
                ).fetchone()[0]

            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            story = fixture["scenarios"][0]["story_package"]
            story["story_revision"] = 2
            story["sections"][0]["text"] = "Texto revisado na nova versão da matéria sintética."
            fixture_path.write_text(
                json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            second = motor.run_layout_demo(fixture_path)
            second_story = second["scenario_results"][0]

            with closing(store.connect()) as connection:
                attempts_after = connection.execute(
                    "SELECT COUNT(*) FROM execution_attempts WHERE run_id = ?",
                    (second["run_id"],),
                ).fetchone()[0]
            self.assertEqual(second["status"], "awaiting_approval")
            self.assertNotEqual(
                first_story["story_revision_sha256"], second_story["story_revision_sha256"]
            )
            self.assertNotEqual(first_story["plan_sha256"], second_story["plan_sha256"])
            self.assertGreater(attempts_after, attempts_before)

    def test_failed_rights_gate_stays_blocked_without_repeating_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture_path = root / "layout-demo.json"
            fixture = json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8"))
            fixture["scenarios"][0]["media_inventory"]["assets"][0]["rights_status"] = "pending"
            fixture_path.write_text(
                json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            store = Store(root / "motor.sqlite3", root / "artifacts")
            motor = Motor(store)

            first = motor.run_layout_demo(fixture_path)
            self.assertEqual(first["status"], "failed_intervention")
            failed_scenario = next(
                row for row in first["scenario_results"]
                if row["scenario_id"] == "reportagem-duas-imagens"
            )
            self.assertEqual(failed_scenario["status"], "FAIL")
            validation = json.loads(
                Path(failed_scenario["validation_path"]).read_text(encoding="utf-8")
            )["payload"]
            checks = {row["check_id"]: row["status"] for row in validation["checks"]}
            self.assertEqual(checks["media_rights_gate"], "FAIL")
            self.assertIn("Prévia bloqueada", Path(failed_scenario["preview_path"]).read_text(encoding="utf-8"))

            with closing(store.connect()) as connection:
                before = connection.execute(
                    "SELECT COUNT(*) FROM execution_attempts WHERE run_id = ?",
                    (first["run_id"],),
                ).fetchone()[0]
            second = motor.run_layout_demo(fixture_path)
            with closing(store.connect()) as connection:
                after = connection.execute(
                    "SELECT COUNT(*) FROM execution_attempts WHERE run_id = ?",
                    (second["run_id"],),
                ).fetchone()[0]
            self.assertEqual(second["status"], "failed_intervention")
            self.assertEqual(before, after)

    @staticmethod
    def _read_plan(scenario_result: dict[str, object]) -> dict[str, object]:
        return json.loads(Path(str(scenario_result["plan_path"])).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
