from __future__ import annotations

import json
import socket
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping
from xml.sax.saxutils import escape

from motor_editorial.agent_contracts import envelope_from_payload, load_builtin_role_catalog
from motor_editorial.db import Store
from motor_editorial.orchestration import AgentQueue
from motor_editorial.radar_connectors import (
    HttpResponse,
    PerOriginLimiter,
    RadarConnectorService,
    SourceProfile,
)
from motor_editorial.radar_incremental import IncrementalRadarService
from motor_editorial.radar_store import RadarStore
from motor_editorial.radar_triage import RadarGeneralService, RadarTriagePolicy


NOW = "2026-10-25T18:00:00+00:00"
RUMOR_ORIGIN = "https://origin.example.invalid/rumor?id=7&edition=pc"


class FakeResolver:
    def __call__(self, host: str, port: int, *, type: int) -> list[tuple[Any, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))]


class FakeTransport:
    def __init__(self, *responses: HttpResponse):
        self.responses = list(responses)
        self.calls: list[str] = []

    def request(
        self, url: str, pinned_address: str, *, headers: Mapping[str, str], timeout_seconds: float,
        max_response_bytes: int, allow_loopback_http: bool = False,
    ) -> HttpResponse:
        self.calls.append(url)
        return self.responses.pop(0)


def make_profile(source_id: str, host: str) -> SourceProfile:
    return SourceProfile.from_mapping({
        "source_id": source_id,
        "connector_kind": "rss_atom",
        "root_url": f"https://{host}/",
        "feed_url": f"https://{host}/feed?edition=pt&format=rss",
        "allowed_hosts": [host],
        "allowed_operations": ["feed_read"],
        "access_policy": "allowed",
        "terms_checked_at": "2026-10-24",
        "robots_policy": "allowed",
        "robots_checked_at": "2026-10-24",
        "robots_rules_by_host": {host: "User-agent: *\nAllow: /"},
        "min_poll_interval_seconds": 1,
        "max_response_bytes": 1_000_000,
        "timeout_seconds": 2,
        "max_redirects": 2,
    })


def feed_xml(
    *, title: str = "Estúdio anuncia recurso gamer",
    body: str = "Uma análise extensa sobre o recurso, suas consequências para os jogadores e o contexto técnico apresentado pela publicação.",
    link: str = "https://news.example.invalid/story?id=9&edition=pt",
    source: str | None = None,
) -> bytes:
    source_xml = f'<source url="{escape(source, {chr(34): "&quot;"})}">origem</source>' if source else ""
    return (
        "<rss><channel><item>"
        f"<title>{escape(title)}</title><link>{escape(link)}</link><guid>item-9</guid>"
        f"<author>Repórter Exemplo</author><description><![CDATA[<p>{body}</p>]]></description>{source_xml}"
        "</item></channel></rss>"
    ).encode("utf-8")


class RadarTriageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="revista-radar-e10-")
        root = Path(self.temp.name)
        self.radar_store = RadarStore(root / "radar.sqlite3")
        self.queue = AgentQueue(Store(root / "motor.sqlite3", root / "artifacts"))
        self.catalog = load_builtin_role_catalog()
        self.monotonic = [0.0]
        self.transport: FakeTransport | None = None
        self.service: RadarGeneralService | None = None

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_source(self, source_id: str, host: str) -> None:
        self.radar_store.register_source(
            source_id=source_id, display_name=f"Fonte {source_id}", canonical_url=f"https://{host}/",
            source_type="publisher", access_policy="allowed", rights_status="unknown", language="pt-BR", now=NOW,
        )

    def start_service(self, *responses: HttpResponse) -> None:
        self.transport = FakeTransport(*responses)
        connector = RadarConnectorService(
            transport=self.transport, resolver=FakeResolver(),
            limiter=PerOriginLimiter(monotonic=lambda: self.monotonic[0]),
        )
        incremental = IncrementalRadarService(store=self.radar_store, connector=connector)
        self.service = RadarGeneralService(
            store=self.radar_store, incremental=incremental, queue=self.queue, catalog=self.catalog,
        )

    def queue_count(self) -> int:
        with closing(self.queue.store.connect()) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM agent_tasks").fetchone()[0])

    def get_task(self, task_id: str) -> Any:
        return self.queue.get(task_id)

    def test_material_discovery_queues_one_versioned_triage_task_and_304_does_not_wake_ai(self) -> None:
        host = "news.example.invalid"
        self.add_source("source-news", host)
        article_body = "Uma análise extensa sobre o recurso, suas consequências para os jogadores e o contexto técnico apresentado pela publicação."
        self.start_service(
            HttpResponse(200, {"content-type": "application/rss+xml", "etag": '"v1"'}, feed_xml(body=article_body, link=f"https://{host}/story?id=9&edition=pt")),
            HttpResponse(304, {"etag": '"v1"'}, b""),
        )

        first = self.service.scan([make_profile("source-news", host)], now=NOW, portfolio=["edition-demo"])  # type: ignore[union-attr]
        self.assertIsNotNone(first.triage_task_id)
        self.assertEqual(len(first.batch.items), 1)
        task = self.get_task(first.triage_task_id or "")
        self.assertEqual(task.state, "queued")
        self.assertFalse(task.external_request_started)
        self.assertEqual(task.task_type, "agent.role.triage_analyst")
        self.assertEqual(task.executor_id, "triage.pending")
        self.catalog.validate_task(
            envelope_from_payload(task.payload), input_payload=task.payload["input"],
        )
        task_input = task.payload["input"]
        self.assertEqual(task_input["portfolio"], ["edition-demo"])
        item = task_input["items"][0]
        detail = json.loads(item["diff"])
        self.assertEqual(detail["relevance_score"], 0.65)
        self.assertEqual(detail["policy"]["score_basis"], "observation_event_type_only")
        self.assertFalse(detail["policy"]["editorial_relevance_decision"])
        self.assertNotIn(article_body, json.dumps(task.payload, ensure_ascii=False))

        self.monotonic[0] += 3
        second = self.service.scan(  # type: ignore[union-attr]
            [make_profile("source-news", host)], now="2026-10-25T18:01:00+00:00", portfolio=["edition-demo"],
        )
        self.assertEqual(second.fetches[0].fetch.status, "not_modified")
        self.assertEqual(second.batch.items, ())
        self.assertIsNone(second.triage_task_id)
        self.assertEqual(self.queue_count(), 1)
        self.assertEqual(len(self.transport.calls if self.transport else []), 2)

    def test_threshold_and_priority_weights_are_configurable_and_audited(self) -> None:
        host = "weighted.example.invalid"
        self.add_source("source-weighted", host)
        self.start_service(HttpResponse(
            200, {"content-type": "application/rss+xml"},
            feed_xml(link=f"https://{host}/story"),
        ))
        policy = RadarTriagePolicy(
            relevance_threshold=0.80,
            priority_weights={"first_seen": 0.91},
            version="direction-tunable-fixture-v1",
        )
        result = self.service.scan(  # type: ignore[union-attr]
            [make_profile("source-weighted", host)], now=NOW, policy=policy,
        )
        self.assertIsNotNone(result.triage_task_id)
        self.assertEqual(len(result.batch.items), 1)
        detail = json.loads(result.batch.items[0]["diff"])
        self.assertEqual(detail["relevance_score"], 0.91)
        self.assertEqual(detail["policy"]["relevance_threshold"], 0.8)
        self.assertEqual(detail["policy"]["priority_weights"], {"first_seen": 0.91})
        self.assertEqual(detail["policy"]["policy_version"], "direction-tunable-fixture-v1")
        self.assertEqual(self.queue_count(), 1)

    def test_threshold_above_event_weight_filters_without_enqueuing(self) -> None:
        host = "filtered.example.invalid"
        self.add_source("source-filtered", host)
        self.start_service(HttpResponse(
            200, {"content-type": "application/rss+xml"},
            feed_xml(link=f"https://{host}/story"),
        ))
        result = self.service.scan(  # type: ignore[union-attr]
            [make_profile("source-filtered", host)],
            now=NOW,
            policy=RadarTriagePolicy(relevance_threshold=0.8, priority_weights={"first_seen": 0.65}),
        )
        self.assertEqual(result.batch.items, ())
        self.assertIsNone(result.triage_task_id)
        self.assertEqual(result.below_threshold_count, 1)
        self.assertEqual(self.queue_count(), 0)

    def test_rumor_origin_group_is_one_triage_item_with_both_sources_and_epistemic_status(self) -> None:
        source_a, host_a = "rumor-a", "rumor-a.example.invalid"
        source_b, host_b = "rumor-b", "rumor-b.example.invalid"
        self.add_source(source_a, host_a)
        self.add_source(source_b, host_b)
        edited = feed_xml(
            title="Rumor atribuído recebe nova atualização",
            body="Uma análise extensa relata uma nova atualização sobre o rumor, preservando a origem e os limites da informação disponível.",
            link=f"https://{host_b}/report?id=22",
            source=RUMOR_ORIGIN,
        )
        self.start_service(
            HttpResponse(200, {"content-type": "application/rss+xml"}, feed_xml(
                title="Rumor atribuído sobre projeto ainda não anunciado",
                body="Uma análise extensa relata um rumor sobre um projeto e preserva a atribuição original sem declarar que o conteúdo foi confirmado.",
                link=f"https://{host_a}/report?id=11", source=RUMOR_ORIGIN,
            )),
            HttpResponse(200, {"content-type": "application/rss+xml"}, feed_xml(
                title="Rumor atribuído sobre projeto ainda não anunciado",
                body="Uma análise extensa relata um rumor sobre um projeto e preserva a atribuição original sem declarar que o conteúdo foi confirmado.",
                link=f"https://{host_b}/report?id=22", source=RUMOR_ORIGIN,
            )),
        )
        profiles = [make_profile(source_a, host_a), make_profile(source_b, host_b)]
        initial = self.service.scan(profiles, now=NOW)  # type: ignore[union-attr]
        self.assertEqual(len(initial.batch.items), 1)
        first_detail = json.loads(initial.batch.items[0]["diff"])
        self.assertEqual({item["source_id"] for item in first_detail["source_lineage"]}, {source_a, source_b})
        self.assertEqual(self.queue_count(), 1)

        source_c, host_c = "rumor-c", "rumor-c.example.invalid"
        self.add_source(source_c, host_c)
        self.monotonic[0] += 3
        self.transport.responses.extend([
            HttpResponse(304, {}, b""),
            HttpResponse(304, {}, b""),
            HttpResponse(200, {"content-type": "application/rss+xml"}, feed_xml(
                title="Rumor atribuído sobre projeto ainda não anunciado",
                body="Uma análise extensa relata um rumor sobre um projeto e preserva a atribuição original sem declarar que o conteúdo foi confirmado.",
                link=f"https://{host_c}/report?id=33", source=RUMOR_ORIGIN,
            )),
        ])
        duplicate = self.service.scan(  # type: ignore[union-attr]
            [*profiles, make_profile(source_c, host_c)], now="2026-10-25T18:01:00+00:00",
        )
        self.assertEqual(duplicate.batch.items, ())
        self.assertIsNone(duplicate.triage_task_id)
        self.assertEqual(duplicate.duplicate_source_count, 1)
        self.assertEqual(self.queue_count(), 1)

        docs = {row["source_id"]: row for row in self.radar_store.list_rows("radar_documents")}
        topic_id = "topic-rumor-fixture"
        self.radar_store.register_topic(
            topic_id=topic_id, canonical_key="project-rumor-fixture", title="Projeto sob rumor", now=NOW,
        )
        self.radar_store.register_claim(
            claim_id="claim-rumor-fixture", topic_id=topic_id,
            statement="O projeto teria sido anunciado.", epistemic_status="attributed_rumor",
            reported_by_source_id=source_a, earliest_traceable_source_id=source_a,
            source_document_id=docs[source_a]["document_id"], first_seen_at=NOW,
            confidence_in_attribution=0.9, confidence_in_content=0.2,
        )
        self.radar_store.link_claim_source(
            claim_id="claim-rumor-fixture", source_id=source_a, relation_type="origin",
            origin_group_id="rumor-origin-fixture", document_id=docs[source_a]["document_id"], linked_at=NOW,
        )
        self.radar_store.link_claim_source(
            claim_id="claim-rumor-fixture", source_id=source_b, relation_type="republished",
            origin_group_id="rumor-origin-fixture", document_id=docs[source_b]["document_id"],
            based_on_source_id=source_a, linked_at=NOW,
        )
        self.radar_store.link_claim_source(
            claim_id="claim-rumor-fixture", source_id=source_c, relation_type="republished",
            origin_group_id="rumor-origin-fixture", document_id=docs[source_c]["document_id"],
            based_on_source_id=source_a, linked_at=NOW,
        )

        self.monotonic[0] += 3
        self.transport.responses.extend([
            HttpResponse(304, {}, b""),
            HttpResponse(200, {"content-type": "application/rss+xml"}, edited),
            HttpResponse(304, {}, b""),
        ])
        update = self.service.scan(  # type: ignore[union-attr]
            [*profiles, make_profile(source_c, host_c)], now="2026-10-25T18:02:00+00:00",
        )
        self.assertIsNotNone(update.triage_task_id)
        self.assertEqual(len(update.batch.items), 1)
        detail = json.loads(update.batch.items[0]["diff"])
        self.assertEqual(len(detail["claim_lineage"]), 3)
        self.assertEqual({claim["epistemic_status"] for claim in detail["claim_lineage"]}, {"attributed_rumor"})
        self.assertEqual({claim["relation_type"] for claim in detail["claim_lineage"]}, {"origin", "republished"})
        self.assertEqual({line["source_id"] for line in detail["source_lineage"]}, {source_a, source_b, source_c})
        self.assertEqual({event["event_type"] for event in detail["observations"]}, {"title_changed"})
        self.assertTrue(detail["rumor_status_is_not_content_confirmation"])
        self.assertEqual(self.queue_count(), 2)


if __name__ == "__main__":
    unittest.main()
