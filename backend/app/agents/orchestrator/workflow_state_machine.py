from __future__ import annotations

from datetime import datetime
from typing import Callable
from uuid import UUID

from loguru import logger

from app.agents.base.a2a_types import OnboardingStage


class InvalidTransitionError(Exception):
    pass


# Valid forward and backward transitions per stage
#
# Institutional: INTAKE → REVIEW → SALES_REVIEW → KYC → PARALLEL_PRODUCTS → COMPLETE
# Retail:        INTAKE → REVIEW → KYC → PARALLEL_PRODUCTS → COMPLETE
# SM reject/info: SALES_REVIEW → REVIEW
# All docs must be approved before advancing from REVIEW.
_TRANSITIONS: dict[OnboardingStage, set[OnboardingStage]] = {
    OnboardingStage.INTAKE: {
        OnboardingStage.REVIEW,  # all cases enter Advisor Review after intake
    },
    OnboardingStage.REVIEW: {
        OnboardingStage.SALES_REVIEW,  # institutional, all docs approved → SM review
        OnboardingStage.KYC,           # retail, all docs approved → KYC
        OnboardingStage.COMPLETE,
        OnboardingStage.ESCALATED,
    },
    OnboardingStage.SALES_REVIEW: {
        OnboardingStage.KYC,     # SM approved → proceed to KYC
        OnboardingStage.REVIEW,  # SM rejected / requested info → back to Advisor Review
    },
    OnboardingStage.KYC: {
        OnboardingStage.PARALLEL_PRODUCTS,
        OnboardingStage.ESCALATED,
    },
    OnboardingStage.PARALLEL_PRODUCTS: {
        OnboardingStage.REVIEW,
        OnboardingStage.COMPLETE,
        OnboardingStage.ESCALATED,
    },
    OnboardingStage.COMPLETE: set(),
    OnboardingStage.ESCALATED: {
        OnboardingStage.REVIEW,
        OnboardingStage.KYC,
        OnboardingStage.COMPLETE,
    },
}


class WorkflowStateMachine:
    def __init__(
        self,
        case_id: UUID,
        initial_stage: OnboardingStage = OnboardingStage.INTAKE,
    ) -> None:
        self.case_id = case_id
        self._stage = initial_stage
        self._history: list[tuple[OnboardingStage, datetime]] = [
            (initial_stage, datetime.utcnow())
        ]
        self._on_transition_callbacks: list[Callable[[OnboardingStage], None]] = []

    @property
    def stage(self) -> OnboardingStage:
        return self._stage

    def can_transition(self, to: OnboardingStage) -> bool:
        return to in _TRANSITIONS.get(self._stage, set())

    def transition(self, to: OnboardingStage) -> None:
        if not self.can_transition(to):
            raise InvalidTransitionError(
                f"Cannot transition {self._stage} → {to} for case {self.case_id}"
            )
        logger.info(f"[FSM] case={self.case_id} {self._stage} → {to}")
        self._stage = to
        self._history.append((to, datetime.utcnow()))
        for cb in self._on_transition_callbacks:
            cb(to)

    def on_transition(self, callback: Callable[[OnboardingStage], None]) -> None:
        self._on_transition_callbacks.append(callback)

    def restore(self, stage: OnboardingStage) -> None:
        """Restore to a persisted stage without validation (used by journey resumption)."""
        logger.info(f"[FSM] case={self.case_id} restored → {stage}")
        self._stage = stage
        self._history.append((stage, datetime.utcnow()))

    @property
    def history(self) -> list[tuple[OnboardingStage, datetime]]:
        return list(self._history)

    def is_terminal(self) -> bool:
        return self._stage in (OnboardingStage.COMPLETE, OnboardingStage.ESCALATED)

    def is_human_pending(self) -> bool:
        return self._stage in (OnboardingStage.SALES_REVIEW, OnboardingStage.REVIEW)
