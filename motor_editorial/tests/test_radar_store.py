from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from motor_editorial import db
from motor_editorial.agent_contracts import RESEARCH_REQUEST_SCHEMA_VERSION, ResearchPacket, ResearchRequest
from motor_editorial.radar_store import RADAR_SCHEMA_VERSION, RUNTIME_DB_PATH, RadarStore, RadarStoreError


NOW = "2026-10-25T16:00:00+00:00"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_request(*, request_id: str = "research-1", idempotency_key: str = "idem-1") -> ResearchRequest:
    return ResearchRequest.from_mapping(
        {
            "schema_version": RESEARCH_REQUEST_SCHEMA_VERSION,
            "request_id": request_id,
            "parent_task_id": "task-1",
            "story_id": "story-1",
            "requester_role_id": "evidence_investigator",
            "research_profile_id": "hardware",
            "research_profile_version": "1.0.0",
            "question": "Quais fontes independentes confirmam a pauta sintética?",
            "queries": ["fixture query"],
            "entity_ids": ["entity-1"],
            "required_evidence_kinds": ["official_statement"],
            "preferred_source_ids": [],
            "preferred_domains": ["example.invalid"],
            "languages": ["pt-BR"],
            "time_window": {"from": "2026-01-01", "to": "2026-10-25"},
            "versions_configurations": {"profile": "hardware-v1"},
            "known_evidence_ids": [],
            "exclusions": ["sem busca externa"],
            "max_sources": 3,
            "max_requests": 5,
            "max_bytes": 100_000,
            "max_duration_seconds": 30,
            "reason": "Fixture offline E04.",
            "allowed_scope": ["metadata"],
            "idempotency_key": idempotency_key,
            "human_gate_if_sensitive": True,
        }
    )


class RadarStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="revista-radar-e04-")
        self.root = Path(self.temp.name)
        self.db_path = self.root / "radar.sqlite3"
        self.store = RadarStore(self.db_path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_source(self, source_id: str = "source-1", *, access_policy: str = "allowed") -> None:
        self.store.register_source(
            source_id=source_id,
            display_name=f"Fonte {source_id}",
            canonical_url=f"https://{source_id}.example.invalid/",
            source_type="publisher",
            access_policy=access_policy,
            rights_status="unknown",
            now=NOW,
        )

    def add_document(self, *, document_id: str = "doc-1", source_id: str = "source-1", **overrides: object) -> None:
        fields: dict[str, object] = {
            "document_id": document_id,
            "source_id": source_id,
            "canonical_url": f"https://{source_id}.example.invalid/story",
            "publisher": f"Editora {source_id}",
            "language": "pt-BR",
            "fetched_at": NOW,
            "content_sha256": sha256("conteudo"),
            "normalized_sha256": sha256("conteudo normalizado"),
            "title": "Pauta sintética",
        }
        fields.update(overrides)
        self.store.register_document(**fields)  # type: ignore[arg-type]

    def add_topic(self, topic_id: str = "topic-1") -> None:
        self.store.register_topic(topic_id=topic_id, canonical_key=f"key-{topic_id}", title="Pauta sintética", now=NOW)

    def test_schema_is_separate_versioned_and_runtime_path_is_refused(self) -> None:
        self.assertEqual(RADAR_SCHEMA_VERSION, 4)
        self.assertEqual(db.SCHEMA_VERSION, 5)
        names = self.store.table_names()
        self.assertGreaterEqual(
            len(names),
            16,
        )
        self.assertTrue(all(name.startswith("radar_") for name in names))
        with closing(self.store.connect()) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 4)
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        with self.assertRaisesRegex(RadarStoreError, "não pode abrir"):
            RadarStore(RUNTIME_DB_PATH)

    def test_v0_fixture_migrates_and_backup_restores_original(self) -> None:
        fixture_path = self.root / "legacy-v0.sqlite3"
        backup_path = self.root / "legacy-v0-backup.sqlite3"
        restore_path = self.root / "legacy-v0-restored.sqlite3"
        with closing(sqlite3.connect(fixture_path)) as connection:
            connection.execute(
                "CREATE TABLE radar_sources_v0 (source_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, canonical_url TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO radar_sources_v0 VALUES (?, ?, ?, ?)",
                ("legacy-source", "Fonte legada", "https://legacy.example.invalid/", NOW),
            )
            connection.commit()

        RadarStore.backup_database(fixture_path, backup_path)
        migrated = RadarStore(fixture_path)
        source = migrated.get_row("radar_sources", "source_id", "legacy-source")
        self.assertEqual(source["access_policy"], "unreviewed")  # type: ignore[index]
        self.assertEqual(source["rights_status"], "unknown")  # type: ignore[index]
        self.assertNotIn("radar_sources_v0", migrated.table_names())
        RadarStore.restore_backup(backup_path, restore_path)
        with closing(sqlite3.connect(restore_path)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT count(*) FROM radar_sources_v0").fetchone()[0], 1)

    def test_failed_v0_migration_rolls_back_fixture_ddl_and_data(self) -> None:
        broken_path = self.root / "broken-v0.sqlite3"
        with closing(sqlite3.connect(broken_path)) as connection:
            connection.execute(
                "CREATE TABLE radar_sources_v0 (source_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, canonical_url TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO radar_sources_v0 VALUES (?, ?, ?, ?)",
                ("broken", "Fonte quebrada", "http://legacy.example.invalid/", NOW),
            )
            connection.commit()
        with self.assertRaisesRegex(RadarStoreError, "HTTPS"):
            RadarStore(broken_path)
        with closing(sqlite3.connect(broken_path)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT source_id FROM radar_sources_v0").fetchone()[0], "broken")
            self.assertIsNone(
                connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='radar_sources'").fetchone()
            )

    def test_v0_migration_refuses_unrelated_tables(self) -> None:
        mixed_path = self.root / "mixed.sqlite3"
        with closing(sqlite3.connect(mixed_path)) as connection:
            connection.execute("CREATE TABLE unrelated (value TEXT)")
            connection.commit()
        with self.assertRaisesRegex(RadarStoreError, "fora do fixture"):
            RadarStore(mixed_path)

    def test_source_foreign_key_https_and_short_excerpt_rights_guard(self) -> None:
        with self.assertRaisesRegex(RadarStoreError, "HTTPS"):
            self.store.register_source(
                source_id="bad", display_name="HTTP", canonical_url="http://example.invalid/", now=NOW
            )
        with self.assertRaisesRegex(RadarStoreError, "parâmetros de credencial"):
            self.store.register_source(
                source_id="query-secret", display_name="URL com segredo",
                canonical_url="https://example.invalid/feed?api_key=fixture", now=NOW,
            )
        with self.assertRaisesRegex(RadarStoreError, "direitos autorizados"):
            self.store.register_document(
                document_id="unauthorized", source_id="missing", canonical_url="https://example.invalid/a",
                publisher="Publisher", language="pt-BR", fetched_at=NOW, content_sha256=sha256("a"),
                normalized_sha256=sha256("a"), title="Title", summary_snippet="excerpt",
                content_retention="short_excerpt", rights_status="unknown",
            )
        with self.assertRaisesRegex(RadarStoreError, "exige retenção"):
            self.store.register_document(
                document_id="metadata-only-text", source_id="missing", canonical_url="https://example.invalid/a",
                publisher="Publisher", language="pt-BR", fetched_at=NOW, content_sha256=sha256("a"),
                normalized_sha256=sha256("a"), title="Title", summary_snippet="excerpt",
            )
        with self.assertRaisesRegex(RadarStoreError, "fonte de origem inexistente"):
            self.add_document()
        self.add_source()
        self.add_document(
            document_id="doc-authorized", summary_snippet="excerpt", rights_status="authorized",
            content_retention="short_excerpt", published_at="2026-10-25",
        )
        self.assertEqual(self.store.get_row("radar_documents", "document_id", "doc-authorized")["published_at"], "2026-10-25")  # type: ignore[index]

    def test_observation_events_keep_hash_diffs_and_are_append_only(self) -> None:
        self.add_source()
        self.add_document()
        self.store.record_observation(
            event_id="obs-1", document_id="doc-1", source_id="source-1", event_type="first_seen",
            observed_at=NOW, current_content_sha256=sha256("v1"), diff={"title": {"new": "Pauta"}},
        )
        self.store.record_observation(
            event_id="obs-2", document_id="doc-1", source_id="source-1", event_type="body_changed",
            observed_at="2026-10-25T17:00:00+00:00", previous_content_sha256=sha256("v1"),
            current_content_sha256=sha256("v2"), diff={"changed_sections": ["correção"]},
        )
        events = self.store.list_rows("radar_observation_events", where_column="document_id", where_value="doc-1")
        self.assertEqual([event["event_type"] for event in events], ["first_seen", "body_changed"])
        self.assertEqual(events[1]["previous_content_sha256"], sha256("v1"))
        self.assertIn("correção", events[1]["diff_json"])
        with closing(self.store.connect()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE radar_observation_events SET event_type='repeated' WHERE event_id='obs-1'")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM radar_observation_events WHERE event_id='obs-1'")

    def test_v1_schema_migrates_additively_through_v4(self) -> None:
        from motor_editorial.radar_store import _SCHEMA_V1_STATEMENTS

        fixture_path = self.root / "radar-v1.sqlite3"
        with closing(sqlite3.connect(fixture_path)) as connection:
            for statement in _SCHEMA_V1_STATEMENTS:
                connection.execute(statement)
            connection.execute("PRAGMA user_version = 1")
            connection.commit()
        migrated = RadarStore(fixture_path)
        with closing(migrated.connect()) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 4)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(radar_documents)")}
            self.assertTrue({"body_sha256", "body_segment_hashes_json", "body_char_count", "origin_url"} <= columns)
            entity_columns = {row[1] for row in connection.execute("PRAGMA table_info(radar_entities)")}
            self.assertTrue({"identity_source_document_id", "identity_context"} <= entity_columns)
            claim_source_columns = {row[1] for row in connection.execute("PRAGMA table_info(radar_claim_sources)")}
            self.assertIn("based_on_source_id", claim_source_columns)
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({"radar_fetch_events", "radar_fetch_cache", "radar_republication_groups", "radar_republication_members", "radar_entity_roles", "radar_interviews", "radar_interview_variants"} <= tables)
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_v2_homonym_migration_preserves_entity_links_and_adds_disambiguation(self) -> None:
        from motor_editorial.radar_store import RadarStore as Store

        fixture_path = self.root / "radar-v2-homonyms.sqlite3"
        with closing(sqlite3.connect(fixture_path)) as connection:
            Store._migrate_v0_to_v1(connection)
            Store._migrate_v1_to_v2(connection)
            connection.execute(
                """INSERT INTO radar_sources
                   (source_id, display_name, canonical_url, domain, source_type, access_policy,
                    rights_status, metadata_json, created_at, updated_at)
                   VALUES ('public-source', 'Fonte pública', 'https://public.example.invalid/',
                           'public.example.invalid', 'publisher', 'allowed', 'unknown', '{}', ?, ?)""",
                (NOW, NOW),
            )
            connection.execute(
                """INSERT INTO radar_documents
                   (document_id, source_id, canonical_url, publisher, language, fetched_at,
                    content_sha256, normalized_sha256, title, access_policy, fetch_status)
                   VALUES ('public-doc', 'public-source', 'https://public.example.invalid/interview',
                           'Fonte pública', 'en', ?, ?, ?, 'Interview', 'allowed', 'observed')""",
                (NOW, sha256("body"), sha256("normalized")),
            )
            connection.execute(
                """INSERT INTO radar_entities
                   (entity_id, entity_kind, canonical_name, normalized_name, language, metadata_json, created_at, updated_at)
                   VALUES ('legacy-person', 'person', 'Alex Lee', 'alex lee', 'en', '{}', ?, ?)""",
                (NOW, NOW),
            )
            connection.execute(
                """INSERT INTO radar_entity_aliases
                   (alias_id, entity_id, alias, normalized_alias, language, source_document_id, created_at)
                   VALUES ('legacy-alias', 'legacy-person', 'A. Lee', 'a lee', 'en', 'public-doc', ?)""",
                (NOW,),
            )
            connection.execute(
                "INSERT INTO radar_document_entities(document_id, entity_id, relation_type) VALUES ('public-doc', 'legacy-person', 'interview_subject')"
            )
            connection.commit()
        migrated = Store(fixture_path)
        self.assertEqual(migrated.get_row("radar_entities", "entity_id", "legacy-person")["identity_context"], "")  # type: ignore[index]
        self.assertEqual(len(migrated.list_rows("radar_entity_aliases", where_column="entity_id", where_value="legacy-person")), 1)
        self.assertEqual(len(migrated.list_rows("radar_document_entities", where_column="entity_id", where_value="legacy-person")), 1)
        migrated.register_entity(
            entity_id="alex-studio-b", entity_kind="person", canonical_name="Alex Lee", language="en",
            source_document_id="public-doc", identity_context="Game director at Studio B", now=NOW,
        )
        self.assertEqual(len(migrated.list_rows("radar_entities", where_column="normalized_name", where_value="alex lee")), 2)
        self.assertEqual(migrated.table_names(), {name for name in migrated.table_names() if name.startswith("radar_")})

    def test_v2_to_v3_migration_rolls_back_when_legacy_foreign_key_is_orphaned(self) -> None:
        from motor_editorial.radar_store import RadarStore as Store

        fixture_path = self.root / "radar-v2-orphan.sqlite3"
        with closing(sqlite3.connect(fixture_path)) as connection:
            Store._migrate_v0_to_v1(connection)
            Store._migrate_v1_to_v2(connection)
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(
                """INSERT INTO radar_document_entities(document_id, entity_id, relation_type)
                   VALUES ('missing-document', 'missing-person', 'interview_subject')"""
            )
            connection.commit()

        with self.assertRaisesRegex(RadarStoreError, "referências sem destino"):
            Store(fixture_path)

        with closing(sqlite3.connect(fixture_path)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(radar_entities)")}
            self.assertNotIn("identity_context", columns)
            self.assertEqual(
                connection.execute(
                    "SELECT document_id, entity_id FROM radar_document_entities"
                ).fetchone(),
                ("missing-document", "missing-person"),
            )

    def test_fetch_cache_is_shared_by_source_url_and_fetch_events_are_append_only(self) -> None:
        self.add_source()
        url = "https://source-1.example.invalid/feed?edition=pc&format=rss"
        self.store.save_fetch_cache(
            source_id="source-1", request_url=url, fetched_at=NOW, fetch_status="observed",
            etag='"rev-1"', last_modified="Sun, 25 Oct 2026 12:00:00 GMT", response_sha256=sha256("feed"),
        )
        self.assertEqual(self.store.get_fetch_cache(source_id="source-1", request_url=url)["etag"], '"rev-1"')  # type: ignore[index]
        event_id = self.store.record_fetch_event(
            source_id="source-1", request_url=url, observed_at=NOW, fetch_status="not_modified",
            etag='"rev-1"', last_modified="Sun, 25 Oct 2026 12:00:00 GMT",
        )
        self.assertEqual(self.store.list_rows("radar_fetch_events", where_column="source_id", where_value="source-1")[0]["fetch_event_id"], event_id)
        with closing(self.store.connect()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE radar_fetch_events SET fetch_status='observed' WHERE fetch_event_id=?", (event_id,))
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM radar_fetch_events WHERE fetch_event_id=?", (event_id,))

    def test_entities_aliases_topics_and_claim_history_are_linked(self) -> None:
        self.add_source()
        self.add_document(access_policy="allowed")
        self.store.register_entity(
            entity_id="person-1", entity_kind="person", canonical_name="Pessoa Exemplo", language="pt-BR",
            source_document_id="doc-1", now=NOW,
        )
        self.store.add_entity_alias(
            alias_id="alias-1", entity_id="person-1", alias="P. Exemplo", language="pt-BR",
            source_document_id="doc-1", created_at=NOW,
        )
        self.add_topic()
        self.store.link_topic_entity(topic_id="topic-1", entity_id="person-1", relation_type="subject", source_document_id="doc-1")
        self.store.link_document_entity(document_id="doc-1", entity_id="person-1", relation_type="mentions")
        self.store.link_document_topic(document_id="doc-1", topic_id="topic-1", relation_type="covers")
        self.store.register_claim(
            claim_id="claim-1", topic_id="topic-1", statement="A pessoa teria anunciado um projeto.",
            epistemic_status="attributed_rumor", reported_by_source_id="source-1", first_seen_at=NOW,
            confidence_in_attribution=0.8, confidence_in_content=0.25, asserted_by_entity_id="person-1",
            source_document_id="doc-1", earliest_traceable_source_id="source-1",
            independent_origin_groups=["origin-1"],
        )
        self.store.link_claim_source(
            claim_id="claim-1", source_id="source-1", relation_type="origin", origin_group_id="origin-1",
            document_id="doc-1", linked_at=NOW,
        )
        for number in range(10):
            source_id = f"repost-{number}"
            self.add_source(source_id)
            document_id = f"doc-{source_id}"
            self.add_document(document_id=document_id, source_id=source_id, access_policy="allowed")
            self.store.link_claim_source(
                claim_id="claim-1", source_id=source_id, relation_type="republished", origin_group_id="origin-1",
                document_id=document_id, based_on_source_id="source-1", linked_at=NOW,
            )
        self.add_source("independent-origin")
        self.add_document(document_id="independent-doc", source_id="independent-origin", access_policy="allowed")
        self.store.link_claim_source(
            claim_id="claim-1", source_id="independent-origin", relation_type="independent",
            origin_group_id="origin-2", document_id="independent-doc", linked_at=NOW,
        )
        self.add_source("untraced-repost")
        self.add_document(document_id="untraced-repost-doc", source_id="untraced-repost", access_policy="allowed")
        with self.assertRaisesRegex(RadarStoreError, "Republicação exige"):
            self.store.link_claim_source(
                claim_id="claim-1", source_id="untraced-repost", relation_type="republished",
                origin_group_id="origin-3", document_id="untraced-repost-doc", linked_at=NOW,
            )
        with self.assertRaisesRegex(RadarStoreError, "mesma linhagem"):
            self.store.link_claim_source(
                claim_id="claim-1", source_id="untraced-repost", relation_type="republished",
                origin_group_id="origin-3", document_id="untraced-repost-doc",
                based_on_source_id="source-1", linked_at=NOW,
            )
        self.store.record_claim_event(
            event_id="claim-event-contradiction", claim_id="claim-1", event_type="content_contradicted",
            content_status="contradicted", occurred_at="2026-10-26T10:00:00+00:00",
            reason="A evidência independente contradiz a alegação sintética.",
            event_source_id="independent-origin", event_document_id="independent-doc",
        )
        self.store.record_claim_event(
            event_id="claim-event-correction", claim_id="claim-1", event_type="correction_recorded",
            occurred_at="2026-10-27T10:00:00+00:00", reason="Correção posterior preservada como evento separado.",
            event_source_id="source-1", event_document_id="doc-1",
        )
        claim = self.store.get_row("radar_claims", "claim_id", "claim-1")
        self.assertEqual(claim["epistemic_status"], "attributed_rumor")  # type: ignore[index]
        self.assertEqual(claim["confidence_in_content"], 0.25)  # type: ignore[index]
        event = self.store.get_row("radar_claim_events", "event_id", "claim-event-contradiction")
        self.assertEqual(event["content_status"], "contradicted")  # type: ignore[index]
        self.assertEqual(event["event_type"], "content_contradicted")  # type: ignore[index]
        history = self.store.list_rows("radar_claim_events", where_column="claim_id", where_value="claim-1")
        self.assertEqual(len(history), 2)
        self.assertEqual({row["event_type"] for row in history}, {"content_contradicted", "correction_recorded"})
        with closing(self.store.connect()) as connection:
            groups = connection.execute(
                "SELECT COUNT(DISTINCT origin_group_id) FROM radar_claim_sources WHERE claim_id='claim-1'"
            ).fetchone()[0]
            copied_sources = connection.execute(
                "SELECT COUNT(*) FROM radar_claim_sources WHERE claim_id='claim-1' AND origin_group_id='origin-1'"
            ).fetchone()[0]
        self.assertEqual(groups, 2)
        self.assertEqual(copied_sources, 11)
        with self.assertRaisesRegex(RadarStoreError, "content_status=confirmed"):
            self.store.record_claim_event(
                event_id="claim-event-invalid-status", claim_id="claim-1", event_type="content_confirmed",
                content_status="contradicted", occurred_at="2026-10-28T10:00:00+00:00",
                reason="Estado intencionalmente inconsistente.", event_source_id="source-1", event_document_id="doc-1",
            )
        with self.assertRaisesRegex(RadarStoreError, "exige fonte"):
            self.store.record_claim_event(
                event_id="claim-event-no-source", claim_id="claim-1", event_type="content_confirmed",
                content_status="confirmed", occurred_at="2026-10-28T10:00:00+00:00",
                reason="Evento sem evidência.",
            )
        with closing(self.store.connect()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE radar_claim_events SET reason='overwrite' WHERE event_id='claim-event-contradiction'")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE radar_claims SET statement='overwrite' WHERE claim_id='claim-1'")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM radar_claim_sources WHERE claim_id='claim-1' AND source_id='source-1'")

    def test_personal_and_official_statements_require_public_matching_attribution(self) -> None:
        self.add_source("official-source")
        self.add_source("interview-source")
        self.add_document(document_id="official-doc", source_id="official-source", access_policy="allowed")
        self.add_document(document_id="interview-statement", source_id="interview-source", access_policy="allowed")
        self.store.register_entity(
            entity_id="company-1", entity_kind="company", canonical_name="Studio Público", language="pt-BR",
            source_document_id="official-doc", now=NOW,
        )
        self.store.register_entity(
            entity_id="person-statement", entity_kind="person", canonical_name="Diretora Exemplo", language="pt-BR",
            source_document_id="interview-statement", now=NOW,
        )
        self.add_topic()
        self.store.link_document_entity(document_id="official-doc", entity_id="company-1", relation_type="statement_by")
        self.store.link_document_entity(document_id="interview-statement", entity_id="person-statement", relation_type="statement_by")
        for claim_id, source_id, document_id, entity_id, status in (
            ("official-claim", "official-source", "official-doc", "company-1", "official_statement"),
            ("personal-claim", "interview-source", "interview-statement", "person-statement", "named_person_statement"),
        ):
            self.store.register_claim(
                claim_id=claim_id, topic_id="topic-1", statement=f"Declaração sintética {claim_id}.",
                epistemic_status=status, reported_by_source_id=source_id, source_document_id=document_id,
                asserted_by_entity_id=entity_id, first_seen_at=NOW, confidence_in_attribution=0.99,
            )
        self.assertEqual(self.store.get_row("radar_claims", "claim_id", "official-claim")["epistemic_status"], "official_statement")  # type: ignore[index]
        self.assertEqual(self.store.get_row("radar_claims", "claim_id", "personal-claim")["epistemic_status"], "named_person_statement")  # type: ignore[index]
        with self.assertRaisesRegex(RadarStoreError, "Declaração pessoal exige pessoa"):
            self.store.register_claim(
                claim_id="misattributed-claim", topic_id="topic-1", statement="Declaração atribuída incorretamente.",
                epistemic_status="named_person_statement", reported_by_source_id="official-source",
                source_document_id="official-doc", asserted_by_entity_id="company-1", first_seen_at=NOW,
                confidence_in_attribution=0.9,
            )

    def test_research_request_packet_hashes_versions_and_idempotency(self) -> None:
        request = make_request()
        self.assertEqual(self.store.save_research_request(request, now=NOW), request.request_id)
        self.assertEqual(self.store.save_research_request(request, now="2026-10-25T18:00:00+00:00"), request.request_id)
        stored = self.store.get_row("radar_research_requests", "request_id", request.request_id)
        self.assertEqual(stored["content_hash"], db.stable_hash(db.json_dumps(request.to_dict())))  # type: ignore[index]
        changed_request = make_request(request_id="research-2")
        with self.assertRaisesRegex(RadarStoreError, "Idempotency key"):
            self.store.save_research_request(changed_request, now=NOW)
        unsafe_data = request.to_dict()
        unsafe_data["versions_configurations"] = {"api_key": "fixture-only"}
        with self.assertRaisesRegex(ValueError, "Campo de credencial proibido"):
            ResearchRequest.from_mapping(unsafe_data)
        packet = ResearchPacket.create(
            request_id=request.request_id, status="partial", fetched_at=NOW,
            source_lineage=[{"source_id": "source-1", "origin_group_id": "origin-1"}],
            missing_evidence=["independent confirmation"], constraints=["offline fixture"],
        )
        packet_id = self.store.save_research_packet(packet, version=1)
        result = self.store.get_row("radar_research_packets", "packet_id", packet_id)
        self.assertEqual(result["version"], 1)  # type: ignore[index]
        self.assertEqual(result["content_hash"], packet.content_hash)  # type: ignore[index]
        with self.assertRaisesRegex(RadarStoreError, "version repetida"):
            self.store.save_research_packet(packet, version=1)
        with self.assertRaises(sqlite3.IntegrityError):
            with closing(self.store.connect()) as connection:
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute(
                    "INSERT INTO radar_research_packets (packet_id,request_id,version,status,packet_json,content_hash,fetched_at) VALUES ('bad','missing',1,'partial','{}',?,'2026-10-25T16:00:00+00:00')",
                    (packet.content_hash,),
                )

    def test_portfolio_candidate_lane_history_is_append_only(self) -> None:
        self.add_topic()
        self.store.create_candidate(
            candidate_id="candidate-1", topic_id="topic-1", queue_lane="principal", reason="Mudança material",
            depth_available="moderada", evidence_risk="rumor atribuído", now=NOW, edition_id="edition-1", priority=0.75,
        )
        self.store.record_candidate_event(
            event_id="candidate-event-1", candidate_id="candidate-1", from_lane=None, to_lane="principal",
            actor="fixture", reason="Entrada sintética", occurred_at=NOW,
        )
        self.store.record_candidate_event(
            event_id="candidate-event-2", candidate_id="candidate-1", from_lane="principal", to_lane="reserva",
            actor="fixture", reason="Prioridade recalculada", occurred_at="2026-10-25T17:00:00+00:00",
        )
        self.assertEqual(self.store.get_row("radar_candidates", "candidate_id", "candidate-1")["queue_lane"], "principal")  # type: ignore[index]
        history = self.store.list_rows("radar_candidate_events", where_column="candidate_id", where_value="candidate-1")
        self.assertEqual([event["to_lane"] for event in history], ["principal", "reserva"])
        with closing(self.store.connect()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM radar_candidate_events WHERE event_id='candidate-event-1'")


if __name__ == "__main__":
    unittest.main()
