"""Deterministic editorial candidate portfolio over the shared Radar ledger.

The service ranks only supplied candidate priorities. It does not create story
drafts, decide editorial merit, or invoke agents. Existing story-linked edition
members and explicitly authorized lane overrides stay pinned until an auditable
human swap is recorded.
"""

from __future__ import annotations

import json
import math
import uuid
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from typing import Any

from .radar_store import RadarStore, RadarStoreError, _json, _text, _timestamp


_EVALUATION_STATES = {"eligible", "blocked", "needs_evaluation"}
_MATERIAL_OBSERVATION_TYPES = {
    "first_seen", "title_changed", "body_changed", "corrected", "removed", "url_changed", "origin_linked",
}
_MATERIAL_CLAIM_TYPES = {
    "evidence_added", "origin_traced", "content_confirmed", "content_partially_confirmed",
    "content_contradicted", "content_withdrawn", "correction_recorded", "dispute_recorded", "superseded",
}


@dataclass(frozen=True)
class RadarPortfolioPolicy:
    """Default first-edition capacity, with smaller fixture policies for tests."""

    principal_limit: int = 10
    reserve_limit: int = 10
    version: str = "radar-portfolio-v1"

    def __post_init__(self) -> None:
        for name, value in (("principal_limit", self.principal_limit), ("reserve_limit", self.reserve_limit)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} precisa ser inteiro positivo.")
        if not isinstance(self.version, str) or not self.version.strip() or len(self.version) > 64:
            raise ValueError("version precisa ser texto curto.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "principal_limit": self.principal_limit,
            "reserve_limit": self.reserve_limit,
            "ranking": "priority_desc_then_created_at_then_candidate_id",
            "priority_is_supplied_not_editorially_inferred": True,
        }


@dataclass(frozen=True)
class RadarPortfolio:
    edition_id: str
    principal: tuple[Mapping[str, Any], ...]
    reserve: tuple[Mapping[str, Any], ...]
    monitoring: tuple[Mapping[str, Any], ...]
    discarded: tuple[Mapping[str, Any], ...]
    policy: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "edition_id": self.edition_id,
            "principal": [dict(row) for row in self.principal],
            "reserve": [dict(row) for row in self.reserve],
            "monitoring": [dict(row) for row in self.monitoring],
            "discarded": [dict(row) for row in self.discarded],
            "policy": dict(self.policy),
            "story_drafts_created": 0,
        }


class RadarPortfolioService:
    """Maintain a dynamic 10 + 10 topic portfolio without writing stories."""

    def __init__(self, *, store: RadarStore, policy: RadarPortfolioPolicy | None = None):
        if not isinstance(store, RadarStore):
            raise ValueError("store precisa ser RadarStore.")
        self.store = store
        self.policy = policy or RadarPortfolioPolicy()

    def upsert_candidate(
        self,
        *,
        topic_id: str,
        edition_id: str,
        priority: float,
        reason: str,
        depth_available: str,
        evidence_risk: str,
        now: str,
        source_packet_id: str | None = None,
        actor: str = "radar.portfolio",
    ) -> RadarPortfolio:
        """Create or update one topic/edition candidate and rebalance its queue."""
        topic_id = _text(topic_id, "topic_id", maximum=256)  # type: ignore[assignment]
        edition_id = _text(edition_id, "edition_id", maximum=256)  # type: ignore[assignment]
        reason = _text(reason, "reason", maximum=2_000)  # type: ignore[assignment]
        depth_available = _text(depth_available, "depth_available", maximum=256)  # type: ignore[assignment]
        evidence_risk = _text(evidence_risk, "evidence_risk", maximum=256)  # type: ignore[assignment]
        now = _timestamp(now, "now")  # type: ignore[assignment]
        actor = _text(actor, "actor", maximum=256)  # type: ignore[assignment]
        source_packet_id = _text(source_packet_id, "source_packet_id", maximum=256, optional=True)
        if isinstance(priority, bool) or not isinstance(priority, (int, float)) or not math.isfinite(float(priority)):
            raise RadarStoreError("priority precisa ser numérica e finita.")

        with closing(self.store.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                topic = connection.execute("SELECT topic_id FROM radar_topics WHERE topic_id=?", (topic_id,)).fetchone()
                if topic is None:
                    raise RadarStoreError("Candidate exige topic_id já registrado no Radar.")
                row = connection.execute(
                    "SELECT * FROM radar_candidates WHERE topic_id=? AND edition_id=?",
                    (topic_id, edition_id),
                ).fetchone()
                if row is None:
                    candidate_id = str(uuid.uuid4())
                    connection.execute(
                        """INSERT INTO radar_candidates
                           (candidate_id, topic_id, edition_id, queue_lane, reason, depth_available, evidence_risk,
                            priority, source_packet_id, human_override_json, created_at, updated_at, evaluation_state)
                           VALUES (?, ?, ?, 'monitoramento', ?, ?, ?, ?, ?, '{}', ?, ?, 'eligible')""",
                        (candidate_id, topic_id, edition_id, reason, depth_available, evidence_risk,
                         float(priority), source_packet_id, now, now),
                    )
                    self._write_event(
                        connection, candidate_id=candidate_id, from_lane=None, to_lane="monitoramento",
                        from_state=None, to_state="eligible", event_kind="candidate_created", actor=actor,
                        reason="Candidato de tópico registrado para edição.", occurred_at=now,
                        evidence={"topic_id": topic_id, "edition_id": edition_id, "priority": float(priority)},
                    )
                else:
                    candidate_id = row["candidate_id"]
                    new_values = {
                        "reason": reason,
                        "depth_available": depth_available,
                        "evidence_risk": evidence_risk,
                        "priority": float(priority),
                        "source_packet_id": source_packet_id,
                    }
                    changed = {
                        key: {"from": row[key], "to": value}
                        for key, value in new_values.items()
                        if row[key] != value
                    }
                    if changed:
                        connection.execute(
                            """UPDATE radar_candidates
                               SET reason=?, depth_available=?, evidence_risk=?, priority=?, source_packet_id=?, updated_at=?
                               WHERE candidate_id=?""",
                            (reason, depth_available, evidence_risk, float(priority), source_packet_id, now, candidate_id),
                        )
                        self._write_event(
                            connection, candidate_id=candidate_id, from_lane=row["queue_lane"],
                            to_lane=row["queue_lane"], from_state=row["evaluation_state"],
                            to_state=row["evaluation_state"], event_kind="candidate_updated", actor=actor,
                            reason="Dados de candidato atualizados; prioridade será reavaliada.", occurred_at=now,
                            evidence={"topic_id": topic_id, "edition_id": edition_id, "changes": changed},
                        )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        self.rebalance(edition_id=edition_id, now=now)
        return self.get_portfolio(edition_id)

    def rebalance(self, *, edition_id: str, now: str, actor: str = "radar.portfolio") -> RadarPortfolio:
        """Re-rank eligible unassigned candidates; never move pinned edition members."""
        edition_id = _text(edition_id, "edition_id", maximum=256)  # type: ignore[assignment]
        now = _timestamp(now, "now")  # type: ignore[assignment]
        actor = _text(actor, "actor", maximum=256)  # type: ignore[assignment]
        with closing(self.store.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                rows = [dict(row) for row in connection.execute(
                    "SELECT * FROM radar_candidates WHERE edition_id=? ORDER BY created_at, candidate_id",
                    (edition_id,),
                ).fetchall()]
                locked: list[dict[str, Any]] = []
                movable: list[dict[str, Any]] = []
                discarded: list[dict[str, Any]] = []
                for row in rows:
                    override = self._override(row["human_override_json"])
                    is_locked = bool(row.get("membership_locked")) or row["story_id"] is not None or override.get("portfolio_lane_lock") in {
                        "principal", "reserva", "monitoramento",
                    }
                    if row["queue_lane"] == "descartada":
                        discarded.append(row)
                    elif is_locked:
                        locked.append(row)
                    elif row["evaluation_state"] == "eligible":
                        movable.append(row)
                fixed_principal = sum(row["queue_lane"] == "principal" for row in locked)
                fixed_reserve = sum(row["queue_lane"] == "reserva" for row in locked)
                if fixed_principal > self.policy.principal_limit or fixed_reserve > self.policy.reserve_limit:
                    raise RadarStoreError(
                        "Membros fixos excedem a capacidade; a carteira exige decisão humana auditada."
                    )
                movable.sort(key=lambda row: (-float(row["priority"]), row["created_at"], row["candidate_id"]))
                main_slots = self.policy.principal_limit - fixed_principal
                reserve_slots = self.policy.reserve_limit - fixed_reserve
                desired: dict[str, str] = {}
                for rank, row in enumerate(movable):
                    if rank < main_slots:
                        desired[row["candidate_id"]] = "principal"
                    elif rank < main_slots + reserve_slots:
                        desired[row["candidate_id"]] = "reserva"
                    else:
                        desired[row["candidate_id"]] = "monitoramento"
                for row in rows:
                    candidate_id = row["candidate_id"]
                    if row["queue_lane"] == "descartada" or any(item["candidate_id"] == candidate_id for item in locked):
                        continue
                    target_lane = desired.get(candidate_id, "monitoramento")
                    if target_lane == row["queue_lane"]:
                        continue
                    connection.execute(
                        "UPDATE radar_candidates SET queue_lane=?, updated_at=? WHERE candidate_id=?",
                        (target_lane, now, candidate_id),
                    )
                    self._write_event(
                        connection, candidate_id=candidate_id, from_lane=row["queue_lane"], to_lane=target_lane,
                        from_state=row["evaluation_state"], to_state=row["evaluation_state"],
                        event_kind="lane_changed", actor=actor,
                        reason="Rebalanceamento determinístico da carteira por prioridade informada.",
                        occurred_at=now,
                        evidence={"edition_id": edition_id, "priority": row["priority"],
                                  "policy": self.policy.to_dict()},
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return self.get_portfolio(edition_id)

    def reactivate_for_material_evidence(
        self,
        *,
        topic_id: str,
        evidence_kind: str,
        evidence_event_id: str,
        now: str,
        actor: str = "radar.evidence",
    ) -> tuple[str, ...]:
        """Mark matching candidates for reassessment from a persisted Radar event."""
        topic_id = _text(topic_id, "topic_id", maximum=256)  # type: ignore[assignment]
        evidence_event_id = _text(evidence_event_id, "evidence_event_id", maximum=256)  # type: ignore[assignment]
        now = _timestamp(now, "now")  # type: ignore[assignment]
        actor = _text(actor, "actor", maximum=256)  # type: ignore[assignment]
        material = self._validate_material_evidence(topic_id, evidence_kind, evidence_event_id)
        candidates = self.store.list_rows("radar_candidates", where_column="topic_id", where_value=topic_id)
        candidate_ids: list[str] = []
        editions: set[str] = set()
        for candidate in candidates:
            evidence = {
                "topic_id": topic_id,
                "evidence_kind": evidence_kind,
                "evidence_event_id": evidence_event_id,
                "evidence_event_type": material["event_type"],
            }
            if self._has_reactivation(candidate["candidate_id"], evidence):
                candidate_ids.append(candidate["candidate_id"])
                editions.add(candidate["edition_id"])
                continue
            self._set_evaluation_state(
                candidate_id=candidate["candidate_id"], new_state="needs_evaluation", now=now,
                actor=actor, event_kind="evaluation_reactivated",
                reason="Mudança material de rumor/fonte reabre avaliação; histórico preservado.", evidence=evidence,
            )
            candidate_ids.append(candidate["candidate_id"])
            editions.add(candidate["edition_id"])
        for edition_id in sorted(editions):
            self.rebalance(edition_id=edition_id, now=now, actor=actor)
        return tuple(candidate_ids)

    def resolve_evaluation(
        self,
        *,
        candidate_id: str,
        outcome: str,
        evaluation_ref: str,
        reason: str,
        now: str,
        actor: str,
    ) -> RadarPortfolio:
        """Record an external evaluation outcome, then update only that edition."""
        if outcome not in {"eligible", "blocked"}:
            raise RadarStoreError("outcome precisa ser eligible ou blocked.")
        candidate_id = _text(candidate_id, "candidate_id", maximum=256)  # type: ignore[assignment]
        evaluation_ref = _text(evaluation_ref, "evaluation_ref", maximum=256)  # type: ignore[assignment]
        reason = _text(reason, "reason", maximum=2_000)  # type: ignore[assignment]
        now = _timestamp(now, "now")  # type: ignore[assignment]
        actor = _text(actor, "actor", maximum=256)  # type: ignore[assignment]
        row = self.store.get_row("radar_candidates", "candidate_id", candidate_id)
        if row is None:
            raise RadarStoreError("Candidate inexistente.")
        self._set_evaluation_state(
            candidate_id=candidate_id, new_state=outcome, now=now, actor=actor,
            event_kind="evaluation_resolved", reason=reason,
            evidence={"evaluation_ref": evaluation_ref, "outcome": outcome},
        )
        return self.rebalance(edition_id=row["edition_id"], now=now, actor=actor)

    def authorize_swap(
        self,
        *,
        principal_candidate_id: str,
        reserve_candidate_id: str,
        authorization: Mapping[str, str],
        actor: str,
        reason: str,
        now: str,
    ) -> RadarPortfolio:
        """Swap main/reserve candidates only with an auditable human approval record.

        This validates the caller-provided approval evidence; it is not an
        authentication provider. Production authorization remains a separate gate.
        """
        principal_candidate_id = _text(principal_candidate_id, "principal_candidate_id", maximum=256)  # type: ignore[assignment]
        reserve_candidate_id = _text(reserve_candidate_id, "reserve_candidate_id", maximum=256)  # type: ignore[assignment]
        actor = _text(actor, "actor", maximum=256)  # type: ignore[assignment]
        reason = _text(reason, "reason", maximum=2_000)  # type: ignore[assignment]
        now = _timestamp(now, "now")  # type: ignore[assignment]
        if not isinstance(authorization, Mapping):
            raise RadarStoreError("Swap exige aprovação humana auditável.")
        decision = _text(authorization.get("decision"), "authorization.decision", maximum=32)
        scope = _text(authorization.get("scope"), "authorization.scope", maximum=64)
        reference = _text(authorization.get("reference"), "authorization.reference", maximum=256)
        approved_by = _text(authorization.get("approved_by"), "authorization.approved_by", maximum=256)
        if decision != "approved" or scope != "edition_membership_change":
            raise RadarStoreError("Swap exige decisão approved no escopo edition_membership_change.")
        approval = {"reference": reference, "approved_by": approved_by, "scope": scope}
        with closing(self.store.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                pair = connection.execute(
                    "SELECT * FROM radar_candidates WHERE candidate_id IN (?, ?) ORDER BY candidate_id",
                    (principal_candidate_id, reserve_candidate_id),
                ).fetchall()
                if len(pair) != 2:
                    raise RadarStoreError("Swap exige dois candidates existentes e distintos.")
                by_id = {row["candidate_id"]: dict(row) for row in pair}
                main = by_id[principal_candidate_id]
                reserve = by_id[reserve_candidate_id]
                if main["edition_id"] != reserve["edition_id"]:
                    raise RadarStoreError("Swap exige candidates da mesma edição.")
                if main["queue_lane"] != "principal" or reserve["queue_lane"] != "reserva":
                    raise RadarStoreError("Swap exige um candidate principal e um reserva.")
                if reserve["evaluation_state"] != "eligible":
                    raise RadarStoreError("A pauta reserva precisa estar elegível para promoção.")
                swap_id = str(uuid.uuid4())
                for row, target, peer in ((main, "reserva", reserve), (reserve, "principal", main)):
                    override = self._override(row["human_override_json"])
                    override["portfolio_lane_lock"] = target
                    override["last_authorized_swap"] = {"swap_id": swap_id, **approval}
                    connection.execute(
                        "UPDATE radar_candidates SET queue_lane=?, human_override_json=?, membership_locked=1, updated_at=? WHERE candidate_id=?",
                        (target, _json(override, "human_override"), now, row["candidate_id"]),
                    )
                    self._write_event(
                        connection, candidate_id=row["candidate_id"], from_lane=row["queue_lane"],
                        to_lane=target, from_state=row["evaluation_state"], to_state=row["evaluation_state"],
                        event_kind="manual_swap", actor=actor, reason=reason, occurred_at=now,
                        evidence={"swap_id": swap_id, "counterpart_candidate_id": peer["candidate_id"],
                                  "story_id": row["story_id"], "approval_record": approval},
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return self.rebalance(edition_id=main["edition_id"], now=now, actor=actor)

    def get_portfolio(self, edition_id: str) -> RadarPortfolio:
        edition_id = _text(edition_id, "edition_id", maximum=256)  # type: ignore[assignment]
        rows = self.store.list_rows("radar_candidates", where_column="edition_id", where_value=edition_id)
        rows.sort(key=lambda row: (-float(row["priority"]), row["created_at"], row["candidate_id"]))
        grouped: dict[str, list[Mapping[str, Any]]] = {
            "principal": [], "reserva": [], "monitoramento": [], "descartada": [],
        }
        for row in rows:
            grouped[row["queue_lane"]].append(row)
        return RadarPortfolio(
            edition_id=edition_id,
            principal=tuple(grouped["principal"]),
            reserve=tuple(grouped["reserva"]),
            monitoring=tuple(grouped["monitoramento"]),
            discarded=tuple(grouped["descartada"]),
            policy=self.policy.to_dict(),
        )

    def _set_evaluation_state(
        self,
        *,
        candidate_id: str,
        new_state: str,
        now: str,
        actor: str,
        event_kind: str,
        reason: str,
        evidence: Mapping[str, Any],
    ) -> None:
        if new_state not in _EVALUATION_STATES:
            raise RadarStoreError("evaluation_state inválido.")
        with closing(self.store.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT * FROM radar_candidates WHERE candidate_id=?", (candidate_id,),
                ).fetchone()
                if row is None:
                    raise RadarStoreError("Candidate inexistente.")
                override = self._override(row["human_override_json"])
                protected = bool(row["membership_locked"]) or row["story_id"] is not None or override.get("portfolio_lane_lock") in {
                    "principal", "reserva", "monitoramento",
                }
                new_lane = row["queue_lane"]
                if new_state != "eligible" and not protected and new_lane != "descartada":
                    new_lane = "monitoramento"
                if row["evaluation_state"] != new_state or row["queue_lane"] != new_lane:
                    connection.execute(
                        """UPDATE radar_candidates SET evaluation_state=?, queue_lane=?, updated_at=?,
                           last_material_change=CASE WHEN ?='needs_evaluation' THEN ? ELSE last_material_change END
                           WHERE candidate_id=?""",
                        (new_state, new_lane, now, new_state, now, candidate_id),
                    )
                    self._write_event(
                        connection, candidate_id=candidate_id, from_lane=row["queue_lane"], to_lane=new_lane,
                        from_state=row["evaluation_state"], to_state=new_state, event_kind=event_kind,
                        actor=actor, reason=reason, occurred_at=now, evidence=dict(evidence),
                    )
                else:
                    # A distinct material event must remain visible even when reassessment is already pending.
                    if event_kind == "evaluation_reactivated":
                        prior = connection.execute(
                            "SELECT evidence_json FROM radar_candidate_events WHERE candidate_id=? AND event_kind=?",
                            (candidate_id, event_kind),
                        ).fetchall()
                        target = _json(dict(evidence), "candidate_event_evidence")
                        if not any(item["evidence_json"] == target for item in prior):
                            connection.execute(
                                "UPDATE radar_candidates SET updated_at=?, last_material_change=? WHERE candidate_id=?",
                                (now, now, candidate_id),
                            )
                            self._write_event(
                                connection, candidate_id=candidate_id, from_lane=row["queue_lane"],
                                to_lane=row["queue_lane"], from_state=row["evaluation_state"],
                                to_state=new_state, event_kind=event_kind, actor=actor, reason=reason,
                                occurred_at=now, evidence=dict(evidence),
                            )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def _validate_material_evidence(self, topic_id: str, evidence_kind: str, event_id: str) -> dict[str, str]:
        if evidence_kind == "claim_event":
            rows = self.store.list_rows("radar_claim_events", where_column="event_id", where_value=event_id)
            if len(rows) != 1 or rows[0]["event_type"] not in _MATERIAL_CLAIM_TYPES:
                raise RadarStoreError("Evento de alegação ausente ou sem mudança material elegível.")
            claim_rows = self.store.list_rows("radar_claims", where_column="claim_id", where_value=rows[0]["claim_id"])
            if len(claim_rows) != 1 or claim_rows[0]["topic_id"] != topic_id:
                raise RadarStoreError("Evento de alegação não pertence ao tópico informado.")
            return {"event_type": rows[0]["event_type"]}
        if evidence_kind == "observation_event":
            rows = self.store.list_rows("radar_observation_events", where_column="event_id", where_value=event_id)
            if len(rows) != 1 or rows[0]["event_type"] not in _MATERIAL_OBSERVATION_TYPES:
                raise RadarStoreError("Evento de fonte ausente ou sem mudança material elegível.")
            links = self.store.list_rows("radar_document_topics", where_column="topic_id", where_value=topic_id)
            if not any(link["document_id"] == rows[0]["document_id"] for link in links):
                raise RadarStoreError("Evento de fonte não está vinculado ao tópico informado.")
            return {"event_type": rows[0]["event_type"]}
        raise RadarStoreError("evidence_kind precisa ser claim_event ou observation_event.")

    def _has_reactivation(self, candidate_id: str, evidence: Mapping[str, Any]) -> bool:
        events = self.store.list_rows("radar_candidate_events", where_column="candidate_id", where_value=candidate_id)
        for event in events:
            if event["event_kind"] != "evaluation_reactivated":
                continue
            try:
                if json.loads(event["evidence_json"]) == dict(evidence):
                    return True
            except (TypeError, json.JSONDecodeError):
                continue
        return False

    @staticmethod
    def _override(raw: str) -> dict[str, Any]:
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise RadarStoreError("human_override_json inválido; carteira não será alterada.") from error
        if not isinstance(value, dict):
            raise RadarStoreError("human_override_json precisa ser objeto.")
        return value

    @staticmethod
    def _write_event(
        connection: Any,
        *,
        candidate_id: str,
        from_lane: str | None,
        to_lane: str,
        from_state: str | None,
        to_state: str | None,
        event_kind: str,
        actor: str,
        reason: str,
        occurred_at: str,
        evidence: Mapping[str, Any],
    ) -> None:
        connection.execute(
            """INSERT INTO radar_candidate_events
               (event_id, candidate_id, from_lane, to_lane, actor, reason, occurred_at, evidence_json,
                event_kind, from_evaluation_state, to_evaluation_state)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), candidate_id, from_lane, to_lane, actor, reason, occurred_at,
             _json(dict(evidence), "candidate_event_evidence"), event_kind, from_state, to_state),
        )
