from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from motor_editorial.radar_store import RadarStore, RadarStoreError


NOW = "2026-10-25T18:40:00+00:00"


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class RadarEntityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="revista-radar-e07-")
        self.store = RadarStore(Path(self.temp.name) / "radar.sqlite3")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_source(self, source_id: str, host: str, *, source_type: str = "publisher") -> None:
        self.store.register_source(
            source_id=source_id, display_name=f"Fonte {source_id}", canonical_url=f"https://{host}/",
            source_type=source_type, access_policy="allowed", rights_status="unknown", language="en", now=NOW,
        )

    def add_document(self, document_id: str, source_id: str, host: str, language: str, path: str) -> None:
        self.store.register_document(
            document_id=document_id, source_id=source_id, canonical_url=f"https://{host}/{path}",
            publisher=f"Fonte {source_id}", language=language, fetched_at=NOW,
            content_sha256=sha256(document_id), normalized_sha256=sha256(f"normalized {document_id}"),
            title=f"Material {document_id}", access_policy="allowed", fetch_status="observed",
        )

    def test_japanese_and_romanized_aliases_and_evidenced_homonyms(self) -> None:
        self.add_source("source-ja", "jp.example.invalid")
        self.add_source("source-en", "en.example.invalid")
        self.add_document("doc-ja", "source-ja", "jp.example.invalid", "ja", "interview")
        self.add_document("doc-en", "source-en", "en.example.invalid", "en", "profile")
        self.store.register_entity(
            entity_id="person-miyamoto", entity_kind="person", canonical_name="宮本 茂", language="ja",
            source_document_id="doc-ja", now=NOW,
        )
        self.store.add_entity_alias(
            alias_id="alias-miyamoto-ja", entity_id="person-miyamoto", alias="みやもと しげる",
            language="ja", source_document_id="doc-ja", created_at=NOW,
        )
        self.store.add_entity_alias(
            alias_id="alias-miyamoto-latin", entity_id="person-miyamoto", alias="Shigeru Miyamoto",
            language="JA-latn", source_document_id="doc-en", created_at=NOW,
        )
        self.store.register_entity(
            entity_id="project-jp", entity_kind="project", canonical_name="銀河計画", language="ja",
            source_document_id="doc-ja", now=NOW,
        )
        self.store.add_entity_alias(
            alias_id="project-alias-en", entity_id="project-jp", alias="Galaxy Project",
            language="en", source_document_id="doc-en", created_at=NOW,
        )
        aliases = self.store.list_rows("radar_entity_aliases", where_column="entity_id", where_value="person-miyamoto")
        self.assertEqual({alias["language"] for alias in aliases}, {"ja", "ja-Latn"})
        project_aliases = self.store.list_rows("radar_entity_aliases", where_column="entity_id", where_value="project-jp")
        self.assertEqual(project_aliases[0]["alias"], "Galaxy Project")
        with self.assertRaisesRegex(RadarStoreError, "contato pessoal"):
            self.store.add_entity_alias(
                alias_id="alias-private-phone", entity_id="person-miyamoto", alias="+1 (555) 123-4567",
                language="en", source_document_id="doc-en", created_at=NOW,
            )

        for entity_id, context in (
            ("alex-producer", "producer at Studio A"),
            ("alex-director", "director at Studio B"),
        ):
            self.store.register_entity(
                entity_id=entity_id, entity_kind="person", canonical_name="Alex Lee", language="en",
                source_document_id="doc-en", identity_context=context, now=NOW,
            )
        homonyms = self.store.list_rows("radar_entities", where_column="normalized_name", where_value="alex lee")
        self.assertEqual(len(homonyms), 2)
        self.assertEqual({item["identity_context"] for item in homonyms}, {"producer at studio a", "director at studio b"})
        with self.assertRaisesRegex(RadarStoreError, "Homônimo exige"):
            self.store.register_entity(
                entity_id="alex-ambiguous", entity_kind="person", canonical_name="Alex Lee", language="en",
                source_document_id="doc-en", now=NOW,
            )
        with self.assertRaisesRegex(RadarStoreError, "metadata"):
            self.store.register_entity(
                entity_id="person-private", entity_kind="person", canonical_name="Pessoa Pública", language="pt-BR",
                source_document_id="doc-en", metadata={"email": "private@example.invalid"}, now=NOW,
            )
        with self.assertRaisesRegex(RadarStoreError, "contato pessoal"):
            self.store.register_entity(
                entity_id="person-private-context", entity_kind="person", canonical_name="Taro Sato", language="ja",
                source_document_id="doc-ja", identity_context="public profile contact taro@example.invalid", now=NOW,
            )

    def test_role_interview_and_company_release_evidence_remain_distinct_over_time(self) -> None:
        self.add_source("source-interview", "interview.example.invalid")
        self.add_source("source-press", "press.example.invalid", source_type="official")
        self.add_document("interview-doc", "source-interview", "interview.example.invalid", "en", "producer-interview")
        self.add_document("press-doc", "source-press", "press.example.invalid", "en", "staff-announcement")
        self.store.register_entity(
            entity_id="studio", entity_kind="company", canonical_name="Example Studio", language="en",
            source_document_id="press-doc", now=NOW,
        )
        self.store.register_entity(
            entity_id="developer", entity_kind="person", canonical_name="Jordan Park", language="en",
            source_document_id="interview-doc", now=NOW,
        )
        self.store.register_interview(
            interview_id="interview-jordan", subject_entity_id="developer",
            original_document_id="interview-doc", original_language="EN", recorded_at=NOW,
        )
        self.store.link_document_entity(
            document_id="press-doc", entity_id="studio", relation_type="press_release_from",
        )
        self.store.add_entity_role(
            role_id="role-producer", entity_id="developer", role_kind="producer", role_title="Game Producer",
            organization_entity_id="studio", project_entity_id=None,
            valid_from="2021-01-01", valid_to="2023-12-31", source_document_id="interview-doc",
            evidence_context="interview_quote", recorded_at=NOW,
        )
        self.store.add_entity_role(
            role_id="role-director", entity_id="developer", role_kind="director", role_title="Creative Director",
            organization_entity_id="studio", project_entity_id=None,
            valid_from="2024-01-01", valid_to=None, source_document_id="press-doc",
            evidence_context="company_press_release", recorded_at=NOW,
        )
        with self.assertRaisesRegex(RadarStoreError, "Contexto de entrevista"):
            self.store.add_entity_role(
                role_id="role-mislabeled-interview", entity_id="developer", role_kind="producer",
                role_title="Game Producer", organization_entity_id="studio", source_document_id="press-doc",
                evidence_context="interview_quote", recorded_at=NOW,
            )
        with self.assertRaisesRegex(RadarStoreError, "Press release exige"):
            self.store.add_entity_role(
                role_id="role-mislabeled-release", entity_id="developer", role_kind="producer",
                role_title="Game Producer", organization_entity_id="studio", source_document_id="interview-doc",
                evidence_context="company_press_release", recorded_at=NOW,
            )
        roles = self.store.list_entity_roles(entity_id="developer")
        self.assertEqual(len(roles), 2)
        self.assertEqual({role["evidence_context"] for role in roles}, {"interview_quote", "company_press_release"})
        self.assertEqual({role["role_kind"] for role in roles}, {"producer", "director"})
        self.assertEqual({role["valid_to"] for role in roles}, {"2023-12-31", None})
        with self.assertRaisesRegex(RadarStoreError, "termina antes"):
            self.store.add_entity_role(
                role_id="role-invalid-range", entity_id="developer", role_kind="director", role_title="Director",
                source_document_id="press-doc", evidence_context="company_press_release", recorded_at=NOW,
                valid_from="2025-01-01", valid_to="2024-01-01",
            )
        with self.assertRaisesRegex(RadarStoreError, "contato pessoal"):
            self.store.add_entity_role(
                role_id="role-private-contact", entity_id="developer", role_kind="producer",
                role_title="Producer +1 555 123 4567", source_document_id="interview-doc",
                evidence_context="interview_quote", recorded_at=NOW,
            )

    def test_interview_original_and_translation_keep_explicit_lineage(self) -> None:
        self.add_source("source-original", "jp.example.invalid")
        self.add_source("source-translation", "pt.example.invalid")
        self.add_document("interview-ja", "source-original", "jp.example.invalid", "ja", "interview-original")
        self.add_document("interview-pt", "source-translation", "pt.example.invalid", "pt-BR", "interview-translation")
        self.store.register_entity(
            entity_id="interview-subject", entity_kind="person", canonical_name="開発者", language="ja",
            source_document_id="interview-ja", now=NOW,
        )
        self.store.register_interview(
            interview_id="interview-1", subject_entity_id="interview-subject",
            original_document_id="interview-ja", original_language="JA", recorded_at=NOW,
        )
        self.store.add_interview_variant(
            interview_id="interview-1", document_id="interview-pt", relation_type="translation",
            based_on_document_id="interview-ja", language="PT-br", recorded_at=NOW,
        )
        original = self.store.get_row("radar_interviews", "interview_id", "interview-1")
        variant = self.store.list_rows("radar_interview_variants", where_column="interview_id", where_value="interview-1")[0]
        self.assertEqual(original["original_document_id"], "interview-ja")  # type: ignore[index]
        self.assertEqual(variant["based_on_document_id"], "interview-ja")
        self.assertEqual(variant["language"], "pt-BR")
        with self.assertRaisesRegex(RadarStoreError, "Idioma declarado"):
            self.store.add_interview_variant(
                interview_id="interview-1", document_id="interview-pt", relation_type="translation",
                based_on_document_id="interview-ja", language="en", recorded_at=NOW,
            )


if __name__ == "__main__":
    unittest.main()
