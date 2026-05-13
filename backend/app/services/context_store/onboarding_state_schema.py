from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.agents.base.a2a_types import OnboardingState


class ContextSnapshot(BaseModel):
    """Immutable point-in-time copy of OnboardingState for pause/restore."""

    case_id: UUID
    version: int
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    state: OnboardingState


class OptimisticLockError(Exception):
    """Raised when an update is attempted against a stale version."""

    def __init__(self, case_id: UUID, expected: int, actual: int) -> None:
        self.case_id = case_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Optimistic lock conflict for case {case_id}: "
            f"expected version {expected}, found {actual}"
        )


__all__ = [
    "OnboardingState",
    "ContextSnapshot",
    "OptimisticLockError",
]
