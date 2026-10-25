from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from motor_editorial.radar_portfolio import RadarPortfolioPolicy, RadarPortfolioService
from motor_editorial.radar_store import RadarStore, RadarStoreError


NOW = "2026-10-25T16:20:00+00:00"


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class RadarPortfolioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="revista-radar-e12-")
        self.root = Path(self.temp.name)
        self.store = RadarStore(self.root / "radar.sqlite3")
        self.service = RadarPortfolioService(store=self.store)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_topic(self, topic_id: str) -> None:
        self.store.register_topic(
            topic_id=topic_id, canonical_key=f"key-{topic_id}", title=f"Topico sintetico {topic_id}", now=NOW,
        )

    def add_candidate(self, topic_id: str, priority: float, *, edition_id: str = "edition-fixture") -> str:
        if not any(row["topic_id"] == topic_id for row in self.store.list_rows("radar_topics")):
            self.add_topic(topic_id)
        portfolio = self.service.upsert_candidate(
            topic_id=topic_id, edition_id=edition_id, priority=priority,
            reason="Sinal sintetico para priorizacao", depth_available="moderada",
            evidence_risk="fixture, sem alegacao factual", now=NOW,
        )
        row = next(row for lane in (portfolio.principal, portfolio.reserve, portfolio.monitoring) for row in lane
                   if row["topic_id"] == topic_id)
        return str(row["candidate_id"])

    def add_source_and_document(self, *, source_id: str, document_id: str, topic_id: str) -> None:
        self.store.register_source(
            source_id=source_id, display_name=f"Fonte {source_id}", canonical_url=f"https://{source_id}.example.invalid/",
            source_type="publisher", access_policy="allowed", rights_status="unknown", now=NOW,
        )
        self.store.register_document(
            document_id=document_id, source_id=source_id, canonical_url=f"https://{source_id}.example.invalid/item",
            publisher=f"Publicacao {source_id}", language="pt-BR", fetched_at=NOW,
            content_sha256=sha256(document_id), normalized_sha256=sha256(f"norm-{document_id}"),
            title=f"Documento sintetico {document_id}", access_policy="allowed", fetch_status="observed",
        )
        self.store.link_document_topic(document_id=document_id, topic_id=topic_id, relation_type="fixture_context")

    def test_default_portfolio_is_ten_plus_ten_without_story_drafts(self) -> None:
        portfolio = None
        for index in range(22):
            portfolio = self._add_and_upsert(index)

        assert portfolio is not None
        self.assertEqual((len(portfolio.principal), len(portfolio.reserve), len(portfolio.monitoring)), (10, 10, 2))
        self.assertEqual([row["topic_id"] for row in portfolio.principal], [f"topic-{i:02d}" for i in range(21, 11, -1)])
        self.assertEqual([row["topic_id"] for row in portfolio.reserve], [f"topic-{i:02d}" for i in range(11, 1, -1)])
        all_rows = [*portfolio.principal, *portfolio.reserve, *portfolio.monitoring]
        self.assertEqual(len({row["topic_id"] for row in all_rows}), 22)
        self.assertTrue(all(row["story_id"] is None for row in all_rows))
        self.assertEqual(portfolio.to_dict()["story_drafts_created"], 0)
        events = self.store.list_rows("radar_candidate_events")
        self.assertEqual(len([event for event in events if event["event_kind"] == "candidate_created"]), 22)
        self.assertTrue(any(event["event_kind"] == "lane_changed" for event in events))

    def _add_and_upsert(self, index: int):
        topic_id = f"topic-{index:02d}"
        self.add_topic(topic_id)
        return self.service.upsert_candidate(
            topic_id=topic_id, edition_id="edition-10x10", priority=index / 100,
            reason="fixture de carteira", depth_available="moderada", evidence_risk="somente fixture", now=NOW,
        )

    def test_upsert_is_idempotent_by_edition_and_topic_and_rebalances_priority(self) -> None:
        candidate_a = self.add_candidate("topic-a", 0.3)
        candidate_b = self.add_candidate("topic-b", 0.7)
        initial = self.service.get_portfolio("edition-fixture")
        self.assertEqual(initial.principal[0]["candidate_id"], candidate_b)
        updated = self.service.upsert_candidate(
            topic_id="topic-a", edition_id="edition-fixture", priority=0.9,
            reason="Prioridade ajustada em fixture", depth_available="alta", evidence_risk="sem evidencia real", now=NOW,
        )
        self.assertEqual(updated.principal[0]["candidate_id"], candidate_a)
        self.assertEqual(len(self.store.list_rows("radar_candidates", where_column="edition_id", where_value="edition-fixture")), 2)
        events = self.store.list_rows("radar_candidate_events", where_column="candidate_id", where_value=candidate_a)
        self.assertIn("candidate_updated", {event["event_kind"] for event in events})

    def test_blocked_candidate_does_not_stop_other_topics_and_history_is_retained(self) -> None:
        self.service = RadarPortfolioService(
            store=self.store, policy=RadarPortfolioPolicy(principal_limit=2, reserve_limit=2),
        )
        candidates = [self.add_candidate(f"topic-{i}", 1 - (i * 0.1)) for i in range(5)]
        initial = self.service.get_portfolio("edition-fixture")
        blocked_id = str(initial.principal[0]["candidate_id"])
        result = self.service.resolve_evaluation(
            candidate_id=blocked_id, outcome="blocked", evaluation_ref="fixture-evaluation-1",
            reason="Bloqueio isolado de teste", now="2026-10-25T16:21:00+00:00", actor="fixture-editor",
        )
        self.assertEqual(len(result.principal), 2)
        self.assertEqual(result.principal[0]["candidate_id"], candidates[1])
        blocked = next(row for row in result.monitoring if row["candidate_id"] == blocked_id)
        self.assertEqual(blocked["evaluation_state"], "blocked")
        self.assertEqual(len(self.store.list_rows("radar_candidates", where_column="edition_id", where_value="edition-fixture")), 5)
        events = self.store.list_rows("radar_candidate_events", where_column="candidate_id", where_value=blocked_id)
        self.assertIn("evaluation_resolved", {event["event_kind"] for event in events})
        self.assertTrue(any(event["to_lane"] == "principal" for event in events))

    def test_claim_event_reactivates_candidate_for_review_without_erasing_history(self) -> None:
        self.add_topic("topic-rumor")
        self.add_source_and_document(source_id="source-a", document_id="doc-a", topic_id="topic-rumor")
        self.store.register_claim(
            claim_id="claim-rumor", topic_id="topic-rumor", statement="Rumor sintetico atribuido",
            epistemic_status="attributed_rumor", reported_by_source_id="source-a", first_seen_at=NOW,
            confidence_in_attribution=0.9, source_document_id="doc-a", url="https://source-a.example.invalid/item",
        )
        candidate_id = self.add_candidate("topic-rumor", 0.9)
        self.add_candidate("topic-other", 0.8)
        self.store.record_claim_event(
            event_id="claim-correction-1", claim_id="claim-rumor", event_type="correction_recorded",
            occurred_at="2026-10-25T16:22:00+00:00", reason="Correcao sintetica adicionada",
            event_source_id="source-a", event_document_id="doc-a", details={"fixture": True},
        )
        automatic = self.store.get_row("radar_candidates", "candidate_id", candidate_id)
        self.assertEqual(automatic["evaluation_state"], "needs_evaluation")  # type: ignore[index]
        self.assertEqual(automatic["queue_lane"], "monitoramento")  # type: ignore[index]
        reactivated = self.service.reactivate_for_material_evidence(
            topic_id="topic-rumor", evidence_kind="claim_event", evidence_event_id="claim-correction-1",
            now="2026-10-25T16:23:00+00:00",
        )
        self.assertEqual(reactivated, (candidate_id,))
        candidate = self.store.get_row("radar_candidates", "candidate_id", candidate_id)
        self.assertEqual(candidate["evaluation_state"], "needs_evaluation")  # type: ignore[index]
        self.assertEqual(candidate["queue_lane"], "monitoramento")  # type: ignore[index]
        other = self.store.list_rows("radar_candidates", where_column="topic_id", where_value="topic-other")[0]
        self.assertEqual(other["evaluation_state"], "eligible")
        events = self.store.list_rows("radar_candidate_events", where_column="candidate_id", where_value=candidate_id)
        self.assertTrue(any(event["event_kind"] == "evaluation_reactivated" for event in events))
        repeated = self.service.reactivate_for_material_evidence(
            topic_id="topic-rumor", evidence_kind="claim_event", evidence_event_id="claim-correction-1",
            now="2026-10-25T16:24:00+00:00",
        )
        self.assertEqual(repeated, (candidate_id,))
        self.assertEqual(len([event for event in events if event["event_kind"] == "candidate_created"]), 1)

    def test_source_observation_reactivates_only_a_topic_with_document_link(self) -> None:
        self.add_topic("topic-source")
        self.add_source_and_document(source_id="source-b", document_id="doc-b", topic_id="topic-source")
        candidate_id = self.add_candidate("topic-source", 0.5)
        self.store.record_observation(
            event_id="observation-correction-1", document_id="doc-b", source_id="source-b",
            event_type="corrected", observed_at="2026-10-25T16:25:00+00:00", diff={"fixture": "metadata only"},
        )
        automatic = self.store.get_row("radar_candidates", "candidate_id", candidate_id)
        self.assertEqual(automatic["evaluation_state"], "needs_evaluation")  # type: ignore[index]
        reactivated = self.service.reactivate_for_material_evidence(
            topic_id="topic-source", evidence_kind="observation_event", evidence_event_id="observation-correction-1",
            now="2026-10-25T16:26:00+00:00",
        )
        self.assertEqual(reactivated, (candidate_id,))
        row = self.store.get_row("radar_candidates", "candidate_id", candidate_id)
        self.assertEqual(row["evaluation_state"], "needs_evaluation")  # type: ignore[index]
        with self.assertRaisesRegex(RadarStoreError, "não está vinculado"):
            self.service.reactivate_for_material_evidence(
                topic_id="topic-unrelated", evidence_kind="observation_event",
                evidence_event_id="observation-correction-1", now="2026-10-25T16:27:00+00:00",
            )

    def test_swap_requires_approval_and_pins_auditable_lane_overrides(self) -> None:
        service = RadarPortfolioService(
            store=self.store, policy=RadarPortfolioPolicy(principal_limit=1, reserve_limit=1),
        )
        for topic_id in ("topic-main", "topic-reserve"):
            self.add_topic(topic_id)
        main_portfolio = service.upsert_candidate(
            topic_id="topic-main", edition_id="edition-swap", priority=0.9, reason="main",
            depth_available="moderada", evidence_risk="fixture", now=NOW,
        )
        reserve_portfolio = service.upsert_candidate(
            topic_id="topic-reserve", edition_id="edition-swap", priority=0.5, reason="reserve",
            depth_available="moderada", evidence_risk="fixture", now=NOW,
        )
        main_id = str(main_portfolio.principal[0]["candidate_id"])
        reserve_id = str(reserve_portfolio.reserve[0]["candidate_id"])
        with closing(self.store.connect()) as connection:
            connection.execute("UPDATE radar_candidates SET story_id='story-main' WHERE candidate_id=?", (main_id,))
            connection.commit()
        with self.assertRaisesRegex(RadarStoreError, "approved"):
            service.authorize_swap(
                principal_candidate_id=main_id, reserve_candidate_id=reserve_id,
                authorization={"decision": "proposed", "scope": "edition_membership_change",
                               "reference": "issue-fixture", "approved_by": "fixture-director"},
                actor="fixture-codex", reason="troca de teste", now="2026-10-25T16:28:00+00:00",
            )
        result = service.authorize_swap(
            principal_candidate_id=main_id, reserve_candidate_id=reserve_id,
            authorization={"decision": "approved", "scope": "edition_membership_change",
                           "reference": "issue-fixture#approval", "approved_by": "fixture-director"},
            actor="fixture-codex", reason="troca autorizada somente na fixture", now="2026-10-25T16:29:00+00:00",
        )
        self.assertEqual(result.principal[0]["candidate_id"], reserve_id)
        self.assertEqual(result.reserve[0]["candidate_id"], main_id)
        after_rebalance = service.rebalance(edition_id="edition-swap", now="2026-10-25T16:30:00+00:00")
        self.assertEqual(after_rebalance.principal[0]["candidate_id"], reserve_id)
        events = self.store.list_rows("radar_candidate_events")
        swaps = [event for event in events if event["event_kind"] == "manual_swap"]
        self.assertEqual(len(swaps), 2)
        self.assertTrue(all("issue-fixture#approval" in event["evidence_json"] for event in swaps))

    def test_over_capacity_of_pinned_members_fails_without_partial_rebalance(self) -> None:
        service = RadarPortfolioService(
            store=self.store, policy=RadarPortfolioPolicy(principal_limit=1, reserve_limit=1),
        )
        ids = [self.add_candidate("topic-pin-a", 0.9), self.add_candidate("topic-pin-b", 0.8)]
        with closing(self.store.connect()) as connection:
            connection.execute("UPDATE radar_candidates SET story_id='story-a' WHERE candidate_id=?", (ids[0],))
            connection.execute("UPDATE radar_candidates SET story_id='story-b', queue_lane='principal' WHERE candidate_id=?", (ids[1],))
            connection.commit()
        before = [self.store.get_row("radar_candidates", "candidate_id", candidate_id)["queue_lane"] for candidate_id in ids]  # type: ignore[index]
        with self.assertRaisesRegex(RadarStoreError, "excedem a capacidade"):
            service.rebalance(edition_id="edition-fixture", now="2026-10-25T16:31:00+00:00")
        after = [self.store.get_row("radar_candidates", "candidate_id", candidate_id)["queue_lane"] for candidate_id in ids]  # type: ignore[index]
        self.assertEqual(after, before)

    def test_priority_rejects_nan_and_missing_topics_fail_closed(self) -> None:
        with self.assertRaisesRegex(RadarStoreError, "finita"):
            self.service.upsert_candidate(
                topic_id="missing", edition_id="edition-fixture", priority=float("nan"), reason="fixture",
                depth_available="baixa", evidence_risk="fixture", now=NOW,
            )
        with self.assertRaisesRegex(RadarStoreError, "topic_id já registrado"):
            self.service.upsert_candidate(
                topic_id="missing", edition_id="edition-fixture", priority=0.5, reason="fixture",
                depth_available="baixa", evidence_risk="fixture", now=NOW,
            )
        with closing(sqlite3.connect(self.store.db_path)) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM radar_candidates").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
