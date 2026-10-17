"""Domain rules and status labels for Motor Editorial v0.1."""

from __future__ import annotations


class MotorError(Exception):
    """Base exception shown to local operators."""


class InvalidTransition(MotorError):
    """Raised when a workflow state change violates the state machine."""


class InvalidApproval(MotorError):
    """Raised when an internal approval is missing its explicit safeguards."""


class RecoverableStepError(MotorError):
    """A simulated transient failure that may be retried safely."""


class InterventionRequired(MotorError):
    """Raised after the finite retry limit has been reached."""


STORY_TRANSITIONS: dict[str, set[str]] = {
    "selected": {"researched"},
    "researched": {"drafted"},
    "drafted": {"blocked_by_review", "reviewed"},
    "blocked_by_review": {"corrected"},
    "corrected": {"blocked_by_review", "reviewed"},
    "reviewed": {"media_checked"},
    "media_checked": {"awaiting_human_approval"},
    "awaiting_human_approval": {"approved_internally"},
    "approved_internally": set(),
}


STORY_LABELS = {
    "selected": "Selecionada",
    "researched": "Apurada (simulação)",
    "drafted": "Rascunho v1",
    "blocked_by_review": "Bloqueada pela revisão",
    "corrected": "Corrigida; aguarda nova revisão",
    "reviewed": "Revisão aprovada",
    "media_checked": "Mídia verificada",
    "awaiting_human_approval": "Aguardando aprovação humana",
    "approved_internally": "Aprovada internamente",
}


EDITION_LABELS = {
    "awaiting_human_approval": "Aguardando aprovação humana",
    "approved_internally": "Aprovada internamente",
}
