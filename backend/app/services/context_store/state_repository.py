from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base.a2a_types import OnboardingState
from app.models.cases import OnboardingCase


class StateRepository:
    """Async SQLAlchemy queries for persisting OnboardingState to the DB."""

    @staticmethod
    async def load(session: AsyncSession, case_id: UUID) -> OnboardingState | None:
        """Load shared_context from the DB and deserialise into OnboardingState.

        Returns None if the case does not exist or has no shared_context yet.
        """
        result = await session.execute(
            select(OnboardingCase.shared_context).where(OnboardingCase.id == case_id)
        )
        row = result.scalar_one_or_none()
        if row is None or not row:
            return None
        return OnboardingState.model_validate(row)

    @staticmethod
    async def persist(
        session: AsyncSession, case_id: UUID, state: OnboardingState
    ) -> None:
        """Serialise OnboardingState and write it to onboarding_cases.shared_context."""
        payload = state.model_dump(mode="json")
        await session.execute(
            update(OnboardingCase)
            .where(OnboardingCase.id == case_id)
            .values(shared_context=payload, current_stage=state.stage.value)
        )

    @staticmethod
    async def exists(session: AsyncSession, case_id: UUID) -> bool:
        result = await session.execute(
            select(OnboardingCase.id).where(OnboardingCase.id == case_id)
        )
        return result.scalar_one_or_none() is not None
