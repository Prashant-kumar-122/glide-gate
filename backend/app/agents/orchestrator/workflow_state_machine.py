from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import UUID

from loguru import logger

from app.agents.base.a2a_types import OnboardingStage


class InvalidTransitionError(Exception):
    pass


def _load_transitions() -> dict[OnboardingStage, set[OnboardingStage]]:
    """Load FSM transitions from orchestrator.config.json at the project root."""
    config_path = Path(__file__).resolve().parents[4] / "configs" / "agents" / "orchestrator.config.json"
    with config_path.open() as f:
        config = json.load(f)
    raw: dict[str, list[str]] = config["fsm"]["transitions"]
    return {
        OnboardingStage(stage): {OnboardingStage(t) for t in targets}
        for stage, targets in raw.items()
    }


# Valid forward and backward transitions per stage — loaded from orchestrator.config.json.
#
# Institutional: INTAKE → REVIEW → SALES_REVIEW → KYC → PARALLEL_PRODUCTS → COMPLETE
# Retail:        INTAKE → REVIEW → KYC → PARALLEL_PRODUCTS → COMPLETE
# SM reject/info: SALES_REVIEW → REVIEW
# All docs must be approved before advancing from REVIEW.
_TRANSITIONS: dict[OnboardingStage, set[OnboardingStage]] = _load_transitions()


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
