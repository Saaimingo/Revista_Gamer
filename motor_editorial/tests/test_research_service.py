from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from motor_editorial.agent_contracts import ContractValidationError, ResearchRequest
from motor_editorial.radar_store import RadarStore
from motor_editorial.research_service import (
    DEFAULT_RESEARCH_PROFILES,
    PUBLIC_SOURCES_SCOPE,
    RADAR_INDEX_SCOPE,
    ResearchProviderResult,
    ResearchService,
)


NOW = "2026-10-25T16:00:00+00:00"


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_request(
    *, request_id: str,
    profile_id: str = "research.hardware.v1",
    question: str = "GPU benchmark at 1440p methodology",
    queries: tuple[str, ...] = ("GPU 1440p benchmark methodology",),
    persona_id: str = "persona:carranca:approved-v1",
    allowed_scope: tuple[str, ...] = (RADAR_INDEX_SCOPE,),
    schema_version: str = "1.1",
    story_revision_id: str | None = "revision-1",
    max_sources: int = 4,
    known_evidence_ids: tuple[str, ...] = (),
    required_evidence_kinds: tuple[str, ...] = ("official_statement",),
) -> ResearchRequest:
    value = {
        "schema_version": schema_version,
        "request_id": request_id,
        "parent_task_id": f"task-{request_id}",
        "story_id": f"story-{request_id}",
        "requester_role_id": "persona_writer",
        "requester_persona_id": persona_id,
        "research_profile_id": profile_id,
        "research_profile_version": "1.0.0",
        "question": question,
        "queries": list(queries),
        "entity_ids": [],
        "required_evidence_kinds": list(required_evidence_kinds),
        "preferred_source_ids": [],
        "preferred_domains": [],
        "languages": ["en", "pt-BR"],
        "time_window": {},
        "versions_configurations": {},
        "known_evidence_ids": list(known_evidence_ids),
        "exclusions": [],
        "max_sources": max_sources,
        "max_requests": 3,
        "max_bytes": 100_000,
        "max_duration_seconds": 30,
        "reason": "Local synthetic fixture for E11.",
        "allowed_scope": list(allowed_scope),
        "idempotency_key": f"idem-{request_id}",
        "human_gate_if_sensitive": True,
    }
    if schema_version == "1.1":
        value["story_revision_id"] = story_revision_id
    return ResearchRequest.from_mapping(value)


class FakeProvider:
    def __init__(self, *results: ResearchProviderResult):
        self.results = list(results)
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def search(self, request, profile, *, cached_document_ids, budget):
        self.calls.append((profile.profile_id, cached_document_ids, budget.max_sources))
        if not self.results:
            raise AssertionError("Unexpected provider call with no queued fixture result.")
        return self.results.pop(0)


class ResearchServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="revista-research-e11-")
        self.root = Path(self.temp.name)
        self.store = RadarStore(self.root / "radar.sqlite3")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_document(self, document_id: str, source_id: str, title: str) -> None:
        self.store.register_source(
            source_id=source_id,
            display_name=f"Fixture {source_id}",
            canonical_url=f"https://{source_id}.example.invalid/",
            source_type="publisher",
            access_policy="allowed",
            rights_status="authorized",
            now=NOW,
        )
        self.store.register_document(
            document_id=document_id,
            source_id=source_id,
            canonical_url=f"https://{source_id}.example.invalid/{document_id}",
            publisher=f"Fixture {source_id}",
            language="en",
            published_at="2026-10-20T12:00:00+00:00",
            fetched_at=NOW,
            content_sha256=sha256(f"body:{document_id}"),
            normalized_sha256=sha256(f"normalized:{document_id}"),
            title=title,
            access_policy="allowed",
            rights_status="authorized",
        )

    def test_three_profiles_share_one_index_and_are_selected_by_request(self) -> None:
        self.add_document("hardware-doc", "hardware-source", "GPU 1440p benchmark methodology")
        self.add_document("games-doc", "games-source", "Patch changes combat mechanics and balance")
        self.add_document("creators-doc", "creators-source", "Mod changelog update license")
        self.store.record_observation(
            event_id="hardware-first-seen", document_id="hardware-doc", source_id="hardware-source",
            event_type="first_seen", observed_at=NOW,
            current_content_sha256=sha256("body:hardware-doc"),
        )
        service = ResearchService(store=self.store)
        cases = (
            ("carranca", "research.hardware.v1", "GPU benchmark at 1440p methodology", ("GPU 1440p benchmark methodology",), "hardware-doc"),
            ("beto", "research.games.v1", "What changed in patch mechanics", ("patch changes combat mechanics",), "games-doc"),
            ("nina", "research.creators.v1", "Mod changelog license update", ("mod changelog license",), "creators-doc"),
        )
        for index, (persona, profile_id, question, queries, expected_document) in enumerate(cases):
            request = make_request(
                request_id=f"persona-{index}", profile_id=profile_id,
                question=question, queries=queries,
                persona_id=f"persona:{persona}:approved-v1",
            )
            result = service.execute(request, now=NOW)
            self.assertEqual(result.packet.status, "partial")
            self.assertEqual(result.packet.missing_evidence, ("official_statement",))
            self.assertEqual(result.index_hit_count, 1)
            self.assertEqual(result.packet.document_refs[0].ref, f"radar://document/{expected_document}")
            self.assertEqual(result.packet_id, self.store.get_row("radar_research_packets", "packet_id", result.packet_id)["packet_id"])
            stored_request = self.store.get_row("radar_research_requests", "request_id", request.request_id)
            self.assertEqual(stored_request["story_id"], request.story_id)
            self.assertEqual(stored_request["story_revision_id"], request.story_revision_id)
            self.assertEqual(result.story_revision_id, request.story_revision_id)
            self.assertFalse(result.provider_called)
            if expected_document == "hardware-doc":
                self.assertEqual(result.packet.new_material_since, NOW)

        carranca_can_ask_about_games = make_request(
            request_id="carranca-game-question", profile_id="research.games.v1",
            question="What changed in patch mechanics", queries=("patch changes combat mechanics",),
            persona_id="persona:carranca:approved-v1",
        )
        cross_profile = service.execute(carranca_can_ask_about_games, now=NOW)
        self.assertEqual(cross_profile.packet.document_refs[0].ref, "radar://document/games-doc")

    def test_local_index_follows_topics_and_entity_aliases(self) -> None:
        self.add_document("linked-doc", "linked-source", "Studio update")
        self.store.register_entity(
            entity_id="game-1", entity_kind="game", canonical_name="Sample Game",
            language="en", source_document_id="linked-doc", now=NOW,
        )
        self.store.add_entity_alias(
            alias_id="game-alias-1", entity_id="game-1", alias="Project Nova",
            language="en", source_document_id="linked-doc", created_at=NOW,
        )
        self.store.register_topic(
            topic_id="topic-1", canonical_key="sample-game:graphics", title="Graphics settings changes", now=NOW,
        )
        self.store.link_topic_entity(topic_id="topic-1", entity_id="game-1", relation_type="about")
        self.store.link_document_entity(document_id="linked-doc", entity_id="game-1", relation_type="about")
        self.store.link_document_topic(document_id="linked-doc", topic_id="topic-1", relation_type="about")
        service = ResearchService(store=self.store)

        topic_result = service.execute(make_request(
            request_id="topic-search", profile_id="research.games.v1",
            question="Graphics settings changes", queries=("graphics settings changes",),
        ), now=NOW)
        alias_result = service.execute(make_request(
            request_id="alias-search", profile_id="research.games.v1",
            question="Project Nova", queries=("Project Nova",),
        ), now=NOW)
        self.assertEqual(topic_result.packet.document_refs[0].ref, "radar://document/linked-doc")
        self.assertEqual(alias_result.packet.document_refs[0].ref, "radar://document/linked-doc")

    def test_not_found_is_empty_and_legacy_request_remains_parseable_but_not_e11_eligible(self) -> None:
        service = ResearchService(store=self.store)
        request = make_request(request_id="empty-index")
        result = service.execute(request, now=NOW)
        self.assertEqual(result.packet.status, "not_found")
        self.assertEqual(result.packet.document_refs, ())
        self.assertEqual(result.packet.relevant_excerpts_short, ())
        self.assertEqual(result.packet.missing_evidence, ("official_statement",))
        self.assertIsNone(result.packet.new_material_since)

        legacy_mapping = request.to_dict()
        legacy_mapping["schema_version"] = "1.0"
        legacy_mapping.pop("story_revision_id")
        legacy_mapping["request_id"] = "legacy-request"
        legacy_mapping["idempotency_key"] = "legacy-idempotency"
        legacy = ResearchRequest.from_mapping(legacy_mapping)
        self.assertEqual(legacy.schema_version, "1.0")
        self.assertNotIn("story_revision_id", legacy.to_dict())
        legacy_result = service.execute(legacy, now=NOW)
        self.assertEqual(legacy_result.packet.status, "blocked")
        self.assertIsNone(legacy_result.story_revision_id)
        with self.assertRaises(ContractValidationError):
            make_request(request_id="missing-revision", story_revision_id=None)

    def test_unregistered_profile_and_unauthorized_scope_fail_closed(self) -> None:
        provider = FakeProvider(ResearchProviderResult(status="found", document_ids=("missing",)))
        service = ResearchService(store=self.store, provider=provider)
        unknown_profile = make_request(
            request_id="bad-scope", profile_id="research.unknown.v1",
        )
        result = service.execute(unknown_profile, now=NOW)
        self.assertEqual(result.packet.status, "blocked")
        self.assertFalse(result.provider_called)
        self.assertEqual(provider.calls, [])
        self.assertIn("profile/version is not registered", result.packet.constraints[0])

        unsupported_scope = make_request(
            request_id="unsupported-scope", profile_id="research.games.v1",
            allowed_scope=(RADAR_INDEX_SCOPE, "write:publish"),
        )
        denied = service.execute(unsupported_scope, now=NOW)
        self.assertEqual(denied.packet.status, "blocked")
        self.assertFalse(denied.provider_called)
        self.assertIn("scope exceeds", denied.packet.constraints[0])
        self.assertEqual(provider.calls, [])

        malformed_time = make_request(request_id="malformed-time-window").to_dict()
        malformed_time["time_window"] = {"from": "next week"}
        invalid_window = service.execute(ResearchRequest.from_mapping(malformed_time), now=NOW)
        self.assertEqual(invalid_window.packet.status, "blocked")
        self.assertIn("invalid ISO date", invalid_window.packet.constraints[0])
        self.assertEqual(provider.calls, [])

    def test_provider_cache_replay_preserves_packet_id_and_avoids_repeated_call(self) -> None:
        provider = FakeProvider(ResearchProviderResult(
            status="not_found", missing_evidence=("official_statement",),
            requests_used=1, bytes_read=128, sources_considered=1, elapsed_seconds=0.25,
        ))
        service = ResearchService(store=self.store, provider=provider)
        request = make_request(
            request_id="cache-replay", allowed_scope=(RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE),
        )
        first = service.execute(request, now=NOW)
        replay = service.execute(request, now="2026-10-25T16:01:00+00:00")
        self.assertEqual(first.packet.status, "not_found")
        self.assertTrue(first.packet_id)
        self.assertEqual(first.packet_id, replay.packet_id)
        self.assertFalse(first.cache_hit)
        self.assertTrue(replay.cache_hit)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(provider.calls[0][0], "research.hardware.v1")
        self.assertEqual(provider.calls[0][1], ())
        self.assertEqual(provider.calls[0][2], request.max_sources)

    def test_provider_results_are_budgeted_and_references_are_validated(self) -> None:
        self.add_document("matching-doc", "matching-source", "GPU 1440p benchmark methodology")
        provider = FakeProvider(
            ResearchProviderResult(
                status="found", document_ids=("matching-doc",), missing_evidence=(),
                requests_used=1, bytes_read=100_001, sources_considered=1, elapsed_seconds=0.1,
            ),
        )
        service = ResearchService(store=self.store, provider=provider)
        request = make_request(
            request_id="over-budget", allowed_scope=(RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE),
        )
        result = service.execute(request, now=NOW)
        self.assertEqual(result.packet.status, "partial")
        self.assertTrue(result.packet.document_refs)  # local cached evidence remains identified
        self.assertTrue(any("max_bytes" in constraint for constraint in result.packet.constraints))

        invalid_provider = FakeProvider(ResearchProviderResult(
            status="found", document_ids=("not-in-radar",), missing_evidence=(),
            requests_used=1, bytes_read=10, sources_considered=1, elapsed_seconds=0.1,
        ))
        invalid_service = ResearchService(store=self.store, provider=invalid_provider)
        invalid_request = make_request(
            request_id="invalid-provider-reference", profile_id="research.games.v1",
            question="patch game mechanics changes", queries=("patch game mechanics changes",),
            allowed_scope=(RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE),
        )
        invalid = invalid_service.execute(invalid_request, now=NOW)
        self.assertEqual(invalid.packet.status, "blocked")
        self.assertEqual(invalid.packet.document_refs, ())
        self.assertTrue(any("absent from the Radar index" in constraint for constraint in invalid.packet.constraints))

    def test_provider_request_count_source_count_and_duration_limits(self) -> None:
        cases = (
            ("requests", ResearchProviderResult(status="not_found", requests_used=4), "max_requests"),
            ("sources", ResearchProviderResult(status="not_found", sources_considered=5), "max_sources"),
            ("duration", ResearchProviderResult(status="not_found", elapsed_seconds=31), "max_duration_seconds"),
        )
        for label, provider_result, expected_constraint in cases:
            with self.subTest(limit=label):
                provider = FakeProvider(provider_result)
                service = ResearchService(store=self.store, provider=provider)
                request = make_request(
                    request_id=f"limit-{label}",
                    allowed_scope=(RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE),
                )
                result = service.execute(request, now=NOW)
                self.assertEqual(result.packet.status, "blocked")
                self.assertTrue(any(expected_constraint in item for item in result.packet.constraints))

    def test_provider_can_return_claim_with_registered_source_lineage(self) -> None:
        self.add_document("claim-doc", "claim-source", "Community update")
        self.store.register_topic(topic_id="topic-1", canonical_key="game:patch", title="Game patch", now=NOW)
        self.store.register_claim(
            claim_id="claim-1", topic_id="topic-1",
            statement="A studio director confirms patch 2 improved quest mechanics.",
            epistemic_status="community_report", reported_by_source_id="claim-source",
            source_document_id="claim-doc", first_seen_at=NOW,
            confidence_in_attribution=0.8, confidence_in_content=0.6,
        )
        provider = FakeProvider(ResearchProviderResult(
            status="found", claim_ids=("claim-1",), missing_evidence=(),
            requests_used=1, bytes_read=64, sources_considered=1, elapsed_seconds=0.1,
        ))
        service = ResearchService(store=self.store, provider=provider)
        request = make_request(
            request_id="claim-research", profile_id="research.games.v1",
            question="patch 2 improved quest mechanics",
            queries=("patch 2 improved quest mechanics",),
            allowed_scope=(RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE),
        )
        result = service.execute(request, now=NOW)
        self.assertEqual(result.packet.status, "partial")
        self.assertEqual(result.packet.missing_evidence, ("official_statement",))
        self.assertEqual(result.packet.claim_refs, ("claim-1",))
        self.assertEqual(result.packet.document_refs[0].ref, "radar://document/claim-doc")
        self.assertTrue(any(entry.get("claim_id") == "claim-1" for entry in result.packet.source_lineage))
        self.assertEqual(len(provider.calls), 1)

        complete_local_request = make_request(
            request_id="local-ledger-complete", profile_id="research.games.v1",
            question="patch 2 improved quest mechanics",
            queries=("patch 2 improved quest mechanics",),
            allowed_scope=(RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE),
            required_evidence_kinds=("community_report",),
        )
        complete_local = service.execute(complete_local_request, now=NOW)
        self.assertEqual(complete_local.packet.status, "found")
        self.assertEqual(complete_local.packet.missing_evidence, ())
        self.assertEqual(len(provider.calls), 1)

    def test_rate_limited_packet_retries_only_after_retry_at(self) -> None:
        provider = FakeProvider(
            ResearchProviderResult(
                status="rate_limited", missing_evidence=("official_statement",),
                retry_at="2026-10-25T17:00:00Z", requests_used=1, sources_considered=1,
            ),
            ResearchProviderResult(
                status="not_found", missing_evidence=("official_statement",),
                requests_used=1, sources_considered=1,
            ),
        )
        service = ResearchService(store=self.store, provider=provider)
        request = make_request(
            request_id="rate-limit", allowed_scope=(RADAR_INDEX_SCOPE, PUBLIC_SOURCES_SCOPE),
        )
        first = service.execute(request, now=NOW)
        cached = service.execute(request, now="2026-10-25T16:30:00+00:00")
        retried = service.execute(request, now="2026-10-25T17:00:00+00:00")
        self.assertEqual(first.packet.status, "rate_limited")
        self.assertTrue(cached.cache_hit)
        self.assertEqual(first.packet_id, cached.packet_id)
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(retried.packet.status, "not_found")
        self.assertNotEqual(first.packet_id, retried.packet_id)


if __name__ == "__main__":
    unittest.main()
