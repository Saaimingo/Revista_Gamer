from __future__ import annotations

import hashlib
import json
import socket
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping
from xml.sax.saxutils import escape

from motor_editorial.radar_connectors import (
    HttpResponse,
    PerOriginLimiter,
    RadarConnectorService,
    SourceProfile,
)
from motor_editorial.radar_incremental import IncrementalRadarService, canonicalize_content_url
from motor_editorial.radar_policy import PersistentDomainQuotaGuard
from motor_editorial.radar_store import RadarStore, RadarStoreError


NOW = "2026-10-25T18:00:00+00:00"


class FakeResolver:
    def __call__(self, host: str, port: int, *, type: int) -> list[tuple[Any, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))]


class FakeTransport:
    def __init__(self, *responses: HttpResponse):
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, str]]] = []

    def request(
        self, url: str, pinned_address: str, *, headers: Mapping[str, str], timeout_seconds: float,
        max_response_bytes: int, allow_loopback_http: bool = False,
    ) -> HttpResponse:
        self.calls.append((url, dict(headers)))
        return self.responses.pop(0)


def make_profile(source_id: str, host: str) -> SourceProfile:
    return SourceProfile.from_mapping({
        "source_id": source_id,
        "connector_kind": "rss_atom",
        "root_url": f"https://{host}/feed?edition=pt&format=rss",
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
    *, title: str = "Novo recurso gamer anunciado", body: str = "Uma análise extensa sobre o recurso, suas consequências para os jogadores e o contexto técnico apresentado na publicação.",
    byline: str = "Ana Repórter", link: str = "https://news.example.invalid/story?id=9&edition=pt",
    source: str | None = None,
) -> bytes:
    source_xml = f'<source url="{escape(source, {chr(34): "&quot;"})}">origem</source>' if source else ""
    return (
        "<rss><channel><item>"
        f"<title>{escape(title)}</title><link>{escape(link)}</link><guid>item-9</guid>"
        f"<author>{escape(byline)}</author><description><![CDATA[<p>{body}</p>]]></description>{source_xml}"
        "</item></channel></rss>"
    ).encode("utf-8")


class RadarIncrementalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="revista-radar-e06-")
        self.store = RadarStore(Path(self.temp.name) / "radar.sqlite3")
        self.monotonic = [0.0]
        self.transport: FakeTransport | None = None
        self.connector: RadarConnectorService | None = None
        self.service: IncrementalRadarService | None = None

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_source(self, source_id: str, host: str) -> None:
        self.store.register_source(
            source_id=source_id, display_name=f"Fonte {host}", canonical_url=f"https://{host}/",
            source_type="publisher", access_policy="allowed", rights_status="unknown", language="pt-BR", now=NOW,
        )

    def use_transport(self, *responses: HttpResponse) -> None:
        self.transport = FakeTransport(*responses)
        self.connector = RadarConnectorService(
            transport=self.transport, resolver=FakeResolver(),
            limiter=PerOriginLimiter(monotonic=lambda: self.monotonic[0]),
        )
        self.service = IncrementalRadarService(store=self.store, connector=self.connector)

    def test_canonical_url_preserves_query_values_and_order(self) -> None:
        value = canonicalize_content_url("https://NEWS.example.invalid/story?item=7&utm_source=feed&edition=pt#section")
        self.assertEqual(value, "https://news.example.invalid/story?item=7&utm_source=feed&edition=pt")
        with self.assertRaises(RadarStoreError):
            canonicalize_content_url("https://news.example.invalid/story?api_key=private")
        with self.assertRaises(RadarStoreError):
            canonicalize_content_url("https://news.example.invalid/story?key=private")

    def test_v11_source_fetch_to_parse_and_ingest_receipts_are_linked(self) -> None:
        host = "official.example.invalid"
        source_id = "official-source"
        source_name = "Fonte Oficial"
        self.store.register_source(
            source_id=source_id, display_name=source_name, canonical_url=f"https://{host}/",
            source_type="official", access_policy="allowed", rights_status="unknown", language="pt-BR",
            metadata={
                "source_class": "official", "source_owner": "Studio Exemplo",
                "profile_version": "founder-profile-1",
            }, now=NOW,
        )
        profile = SourceProfile.from_mapping({
            "source_id": source_id, "connector_kind": "public_api",
            "root_url": f"https://{host}/api/releases", "allowed_hosts": [host],
            "allowed_operations": ["api_metadata_read"], "access_policy": "allowed",
            "terms_checked_at": "2026-10-24", "robots_policy": "allowed", "robots_checked_at": "2026-10-24",
            "robots_rules_by_host": {host: "User-agent: *\\nAllow: /"},
            "schema_version": "1.1", "profile_version": "founder-profile-1",
            "source_name": source_name, "source_owner": "Studio Exemplo", "source_class": "official",
            "channel": "public_api", "allowed_path_prefixes": ["/api/releases"],
            "terms_evidence_url": f"https://{host}/terms", "authenticated": False,
            "reuse_policy": "metadata_only", "rights_status": "unknown", "language": "pt-BR",
            "quota_per_host_day": 4, "quota_per_mission": 3,
            "parser_schema_id": "metadata_records_v1", "adapter_version": "official-json-v1",
            "min_poll_interval_seconds": 1,
        })
        payload = (
            b'{"items":[{"id":"patch-11","title":"Patch 11",'
            b'"html_url":"https://game.example.invalid/news/11",'
            b'"api_url":"https://official.example.invalid/api/releases/11",'
            b'"published_at":"2026-10-25"}]}'
        )
        empty_payload = b'{"items":[]}'
        unsupported_payload = b'{"unexpected":[{"title":"Patch 12"}]}'
        transport = FakeTransport(
            HttpResponse(200, {"content-type": "application/json"}, payload),
            HttpResponse(200, {"content-type": "application/json"}, empty_payload),
            HttpResponse(200, {"content-type": "application/json"}, unsupported_payload),
        )
        guard = PersistentDomainQuotaGuard(
            self.store, quotas={host: 4}, timezone_name="America/Sao_Paulo",
        )
        connector = RadarConnectorService(
            transport=transport, resolver=FakeResolver(),
            limiter=PerOriginLimiter(monotonic=lambda: self.monotonic[0]),
            domain_quota_guard=guard,
        )
        service = IncrementalRadarService(store=self.store, connector=connector)

        result = service.fetch(
            profile, now=NOW, mission_id="eng012-offline-integration", mission_request_limit=3,
        )
        self.assertEqual(result.fetch.status, "observed")
        self.assertEqual(result.fetch.parse_status, "parsed")
        self.assertEqual(result.ingest_status, "ingested")
        self.assertEqual(result.documents_persisted, 1)
        self.assertEqual(result.documents[0].canonical_url, "https://game.example.invalid/news/11")
        fetch = self.store.list_rows(
            "radar_fetch_events", where_column="fetch_event_id", where_value=result.fetch_event_id,
        )[0]
        self.assertEqual(fetch["http_status"], 200)
        self.assertEqual(fetch["payload_bytes"], len(payload))
        self.assertEqual(fetch["response_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(fetch["source_profile_hash"], profile.policy_sha256())
        self.assertEqual(fetch["profile_version"], "founder-profile-1")
        self.assertEqual(fetch["transport_status"], "response_received")
        self.assertEqual(fetch["parse_status"], "not_attempted")
        events = self.store.list_fetch_processing_events(fetch_event_id=str(result.fetch_event_id))
        self.assertEqual([event["stage"] for event in events], ["parse", "ingest"])
        self.assertEqual([event["status"] for event in events], ["parsed", "ingested"])
        self.assertEqual(events[0]["candidate_count"], 1)
        self.assertEqual(events[1]["documents_persisted"], 1)
        self.assertIn(result.documents[0].document_id, events[1]["artifact_refs_json"])
        self.assertNotIn("raw_body", " ".join(fetch.keys()) + " ".join(events[0].keys()))

        self.monotonic[0] += 3
        empty = service.fetch(
            profile, now="2026-10-25T18:01:00+00:00",
            mission_id="eng012-offline-integration", mission_request_limit=3,
        )
        self.assertEqual(empty.fetch.http_status, 200)
        self.assertEqual(empty.fetch.status, "observed")
        self.assertEqual(empty.fetch.parse_status, "parsed_empty")
        self.assertEqual(empty.ingest_status, "no_new_story")
        self.assertEqual(empty.outcome_code, "no_candidate_records")
        self.assertEqual(empty.documents, ())

        self.monotonic[0] += 3
        unsupported = service.fetch(
            profile, now="2026-10-25T18:02:00+00:00",
            mission_id="eng012-offline-integration", mission_request_limit=4,
        )
        self.assertEqual(unsupported.fetch.http_status, 200)
        self.assertEqual(unsupported.fetch.status, "error")
        self.assertEqual(unsupported.fetch.parse_status, "unsupported")
        self.assertEqual(unsupported.ingest_status, "not_attempted")
        self.assertEqual(unsupported.outcome_code, "parser_unsupported")
        self.assertEqual(unsupported.documents, ())

    def test_conditional_cache_shared_across_profiles_and_changes_update_one_document(self) -> None:
        host = "news.example.invalid"
        source_id = "source-news"
        self.add_source(source_id, host)
        initial = feed_xml()
        edited = feed_xml(title="Novo recurso gamer é adiado", body="Uma análise extensa sobre o recurso e as consequências do adiamento para os jogadores, incluindo contexto técnico e novas informações divulgadas.")
        self.use_transport(
            HttpResponse(200, {"content-type": "application/rss+xml", "etag": '"v1"', "last-modified": "Sun, 25 Oct 2026 12:00:00 GMT"}, initial),
            HttpResponse(304, {"etag": '"v1"'}, b""),
            HttpResponse(200, {"content-type": "application/rss+xml", "etag": '"v2"'}, edited),
            HttpResponse(200, {"content-type": "application/rss+xml"}, edited),
        )
        first = self.service.fetch(make_profile(source_id, host), now=NOW)  # type: ignore[union-attr]
        self.assertEqual(first.documents[0].event_type, "first_seen")
        self.assertTrue(first.documents[0].requires_triage)
        first_id = first.documents[0].document_id
        first_cache = self.store.get_fetch_cache(source_id=source_id, request_url="https://news.example.invalid/feed?edition=pt&format=rss")
        self.assertEqual(first_cache["etag"], '"v1"')  # type: ignore[index]
        self.assertRegex(first_cache["response_sha256"], r"^[a-f0-9]{64}$")  # type: ignore[index]

        self.monotonic[0] += 3
        second_profile = make_profile(source_id, host)
        unchanged = self.service.fetch(second_profile, now="2026-10-25T18:01:00+00:00")  # type: ignore[union-attr]
        self.assertEqual(unchanged.fetch.status, "not_modified")
        self.assertFalse(unchanged.requires_triage)
        self.assertEqual(self.transport.calls[1][1]["If-None-Match"], '"v1"')  # type: ignore[union-attr]
        self.assertEqual(self.transport.calls[1][1]["If-Modified-Since"], "Sun, 25 Oct 2026 12:00:00 GMT")  # type: ignore[union-attr]

        self.monotonic[0] += 3
        changed = self.service.fetch(make_profile(source_id, host), now="2026-10-25T18:02:00+00:00")  # type: ignore[union-attr]
        self.assertEqual(changed.documents[0].document_id, first_id)
        self.assertEqual(changed.documents[0].event_type, "title_changed")
        self.assertTrue(changed.documents[0].requires_triage)
        documents = self.store.list_rows("radar_documents", where_column="source_id", where_value=source_id)
        self.assertEqual(len(documents), 1)
        observations = self.store.list_rows("radar_observation_events", where_column="document_id", where_value=first_id)
        self.assertEqual([event["event_type"] for event in observations], ["first_seen", "title_changed"])
        diff = json.loads(observations[-1]["diff_json"])
        self.assertTrue(diff["content_hash"]["normalized_changed"])
        self.assertTrue(diff["body"]["added_segment_hashes"])
        self.assertTrue(diff["body"]["removed_segment_hashes"])

        self.monotonic[0] += 3
        exact_copy = self.service.fetch(make_profile(source_id, host), now="2026-10-25T18:03:00+00:00")  # type: ignore[union-attr]
        self.assertEqual(exact_copy.documents[0].event_type, "repeated")
        self.assertFalse(exact_copy.requires_triage)
        current_cache = self.store.get_fetch_cache(source_id=source_id, request_url="https://news.example.invalid/feed?edition=pt&format=rss")
        self.assertIsNone(current_cache["etag"])  # type: ignore[index]
        self.assertEqual(len(self.store.list_rows("radar_documents", where_column="source_id", where_value=source_id)), 1)
        fetch_events = self.store.list_rows("radar_fetch_events", where_column="source_id", where_value=source_id)
        self.assertEqual([event["fetch_status"] for event in fetch_events], ["observed", "not_modified", "observed", "observed"])

    def test_identical_copies_group_only_with_matching_byline_and_preserve_documents(self) -> None:
        source_a, host_a = "source-a", "a.example.invalid"
        source_b, host_b = "source-b", "b.example.invalid"
        source_c, host_c = "source-c", "c.example.invalid"
        for source_id, host in ((source_a, host_a), (source_b, host_b), (source_c, host_c)):
            self.add_source(source_id, host)
        same_a = feed_xml(link=f"https://{host_a}/story?id=1")
        same_b = feed_xml(link=f"https://{host_b}/story?id=2")
        independent = feed_xml(link=f"https://{host_c}/story?id=3", byline="Bruno Jornalista")
        self.use_transport(
            HttpResponse(200, {"content-type": "application/rss+xml"}, same_a),
            HttpResponse(200, {"content-type": "application/rss+xml"}, same_b),
            HttpResponse(200, {"content-type": "application/rss+xml"}, independent),
        )
        first = self.service.fetch(make_profile(source_a, host_a), now=NOW)  # type: ignore[union-attr]
        self.monotonic[0] += 3
        copy = self.service.fetch(make_profile(source_b, host_b), now="2026-10-25T18:01:00+00:00")  # type: ignore[union-attr]
        self.assertIsNone(first.documents[0].republication_group_id)
        self.assertIsNotNone(copy.documents[0].republication_group_id)
        self.assertFalse(copy.documents[0].requires_triage)
        group_members = self.store.list_republication_members(group_id=copy.documents[0].republication_group_id or "")
        self.assertEqual(len(group_members), 2)

        self.monotonic[0] += 3
        other_author = self.service.fetch(make_profile(source_c, host_c), now="2026-10-25T18:02:00+00:00")  # type: ignore[union-attr]
        self.assertIsNone(other_author.documents[0].republication_group_id)
        self.assertTrue(other_author.documents[0].requires_triage)
        self.assertEqual(len(self.store.list_rows("radar_documents")), 3)
        bylines = {doc["byline"] for doc in self.store.list_rows("radar_documents")}
        self.assertEqual(bylines, {"Ana Repórter", "Bruno Jornalista"})

    def test_declared_origin_groups_different_bylines_without_merging_author_records(self) -> None:
        original = "https://original.example.invalid/story?id=33&edition=pc"
        pairs = (("source-x", "x.example.invalid", "Ana"), ("source-y", "y.example.invalid", "Bia"))
        for source_id, host, _ in pairs:
            self.add_source(source_id, host)
        self.use_transport(
            HttpResponse(200, {"content-type": "application/rss+xml"}, feed_xml(link="https://x.example.invalid/story", byline="Ana", source=original)),
            HttpResponse(200, {"content-type": "application/rss+xml"}, feed_xml(link="https://y.example.invalid/repost", byline="Bia", source=original)),
        )
        first = self.service.fetch(make_profile("source-x", "x.example.invalid"), now=NOW)  # type: ignore[union-attr]
        self.monotonic[0] += 3
        second = self.service.fetch(make_profile("source-y", "y.example.invalid"), now="2026-10-25T18:01:00+00:00")  # type: ignore[union-attr]
        self.assertEqual(second.documents[0].republication_group_id, first.documents[0].republication_group_id)
        self.assertEqual({doc["byline"] for doc in self.store.list_rows("radar_documents")}, {"Ana", "Bia"})


if __name__ == "__main__":
    unittest.main()
