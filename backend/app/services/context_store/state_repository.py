from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base.a2a_types import OnboardingState, OnboardingStage
from app.models.cases import OnboardingCase

# Fixed percentage floor per stage — the minimum progress when entering each stage.
# INTAKE is handled incrementally by _persist_field; other stages snap to these values.
_STAGE_PERCENTAGE: dict[str, float] = {
    OnboardingStage.KYC.value: 70.0,
    OnboardingStage.PARALLEL_PRODUCTS.value: 70.0,  # docs update it further
    OnboardingStage.REVIEW.value: 95.0,
    OnboardingStage.COMPLETE.value: 100.0,
    OnboardingStage.ESCALATED.value: 75.0,
}


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
        values: dict = {
            "shared_context": payload,
            "current_stage": state.stage.value,
            "status": state.stage.value,
        }
        stage_pct = _STAGE_PERCENTAGE.get(state.stage.value)
        if stage_pct is not None:
            values["percentage"] = stage_pct
        await session.execute(
            update(OnboardingCase)
            .where(OnboardingCase.id == case_id)
            .values(**values)
        )

        if state.stage == OnboardingStage.COMPLETE:
            from app.services.accounts.account_service import AccountService
            await AccountService.ensure_created(
                session=session,
                case_id=case_id,
                client_id=state.client_id,
                products=list(state.selected_products),
            )

    @staticmethod
    async def exists(session: AsyncSession, case_id: UUID) -> bool:
        result = await session.execute(
            select(OnboardingCase.id).where(OnboardingCase.id == case_id)
        )
        return result.scalar_one_or_none() is not None
