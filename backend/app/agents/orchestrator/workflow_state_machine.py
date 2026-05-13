from __future__ import annotations

from datetime import datetime
from typing import Callable
from uuid import UUID

from loguru import logger

from app.agents.base.a2a_types import OnboardingStage


class InvalidTransitionError(Exception):
    pass


# Valid forward and backward transitions per stage
_TRANSITIONS: dict[OnboardingStage, set[OnboardingStage]] = {
    OnboardingStage.INTAKE: {OnboardingStage.KYC},
    OnboardingStage.KYC: {
        OnboardingStage.PARALLEL_PRODUCTS,
        OnboardingStage.ESCALATED,
    },
    OnboardingStage.PARALLEL_PRODUCTS: {
        OnboardingStage.REVIEW,
        OnboardingStage.COMPLETE,
        OnboardingStage.ESCALATED,
    },
    OnboardingStage.REVIEW: {
        OnboardingStage.COMPLETE,
        OnboardingStage.ESCALATED,
        OnboardingStage.KYC,  # re-KYC after human approves more info
    },
    OnboardingStage.COMPLETE: set(),
    OnboardingStage.ESCALATED: {
        OnboardingStage.REVIEW,
        OnboardingStage.KYC,  # resume after human approval
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
