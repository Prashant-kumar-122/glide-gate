from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import text

from app.agents.base.a2a_types import OnboardingState, OnboardingStage
from app.database import AsyncSessionLocal
from app.services.context_store.onboarding_state_schema import (
    ContextSnapshot,
    OptimisticLockError,
)
from app.services.context_store.state_repository import StateRepository


class ContextStoreService:
    """In-memory + DB-backed shared state bus for all CADF agents.

    One singleton instance is shared across the process. Each case gets its own
    asyncio.Lock so parallel agent writes are serialised without blocking each other.

    Optimistic locking: every mutation increments `state.version`. Callers that
    hold a stale copy (older version) receive OptimisticLockError and must re-fetch.
    """

    def __init__(self) -> None:
        self._cache: dict[UUID, OnboardingState] = {}
        self._locks: dict[UUID, asyncio.Lock] = {}

    # ── Internal helpers ────────────────────────────────────────────────────

    def _get_lock(self, case_id: UUID) -> asyncio.Lock:
        if case_id not in self._locks:
            self._locks[case_id] = asyncio.Lock()
        return self._locks[case_id]

    async def _load_from_db(self, case_id: UUID) -> OnboardingState | None:
        async with AsyncSessionLocal() as session:
            return await StateRepository.load(session, case_id)

    async def _persist_to_db(self, case_id: UUID, state: OnboardingState) -> None:
        async with AsyncSessionLocal() as session:
            await StateRepository.persist(session, case_id, state)
            await session.commit()

    async def _validate_stage(
        self, stage_value: str, domain_code: str = "wealth_management"
    ) -> None:
        """Validate stage_value against domain_stages rows for the given domain.

        Replaces the dropped oc_stage_chk / oc_status_chk DB CHECK constraints.
        Raises ValueError for any stage code not defined in domain_stages.
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) FROM domain_stages ds "
                    "JOIN domains d ON d.id = ds.domain_id "
                    "WHERE d.domain_code = :domain_code "
                    "  AND ds.stage_code = :stage_code"
                ),
                {"domain_code": domain_code, "stage_code": stage_value},
            )
            if (result.scalar() or 0) == 0:
                raise ValueError(
                    f"Invalid stage {stage_value!r}: not defined in domain_stages "
                    f"for domain {domain_code!r}"
                )

    # ── Public API ──────────────────────────────────────────────────────────

    async def initialise(
        self,
        case_id: UUID,
        client_id: UUID,
        selected_products: list[str],
    ) -> OnboardingState:
        """Create fresh OnboardingState for a new case and persist it."""
        async with self.lock(case_id):
            state = OnboardingState(
                case_id=case_id,
                client_id=client_id,
                stage=OnboardingStage.INTAKE,
                selected_products=selected_products,
                version=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self._cache[case_id] = state
            await self._persist_to_db(case_id, state)
            logger.info(f"ContextStore: initialised case {case_id}")
            return state

    async def get(self, case_id: UUID) -> OnboardingState:
        """Return current state from cache, falling back to DB.

        Raises KeyError if the case does not exist at all.
        """
        if case_id in self._cache:
            return self._cache[case_id]

        state = await self._load_from_db(case_id)
        if state is None:
            raise KeyError(f"No OnboardingState found for case {case_id}")

        self._cache[case_id] = state
        return state

    async def update(
        self,
        case_id: UUID,
        patches: dict[str, Any],
        expected_version: int | None = None,
    ) -> OnboardingState:
        """Apply patches to the state with optimistic locking and persist.

        Args:
            case_id: The onboarding case to update.
            patches: Field-level updates (merged into current state dict).
            expected_version: If provided, raises OptimisticLockError when the
                stored version does not match (stale-write protection for parallel
                agents that fetched an older snapshot).

        Returns:
            The updated OnboardingState (version incremented).
        """
        if "stage" in patches:
            await self._validate_stage(patches["stage"])

        async with self.lock(case_id):
            current = await self.get(case_id)

            if expected_version is not None and current.version != expected_version:
                raise OptimisticLockError(case_id, expected_version, current.version)

            updated_data = current.model_dump()
            updated_data.update(patches)
            updated_data["version"] = current.version + 1
            updated_data["updated_at"] = datetime.utcnow()

            new_state = OnboardingState.model_validate(updated_data)
            self._cache[case_id] = new_state
            await self._persist_to_db(case_id, new_state)

            logger.debug(
                f"ContextStore: updated case {case_id} → version {new_state.version} "
                f"stage={new_state.stage}"
            )
            return new_state

    @asynccontextmanager
    async def lock(self, case_id: UUID) -> AsyncGenerator[None, None]:
        """Async context manager that acquires the per-case lock.

        Usage::

            async with context_store.lock(case_id):
                state = await context_store.get(case_id)
                ...
        """
        async with self._get_lock(case_id):
            yield

    async def snapshot(self, case_id: UUID) -> ContextSnapshot:
        """Capture a point-in-time immutable copy of the current state."""
        state = await self.get(case_id)
        snap = ContextSnapshot(
            case_id=case_id,
            version=state.version,
            captured_at=datetime.utcnow(),
            state=state.model_copy(deep=True),
        )
        logger.debug(f"ContextStore: snapshot case {case_id} at version {state.version}")
        return snap

    async def restore(self, case_id: UUID, snapshot: ContextSnapshot) -> OnboardingState:
        """Restore a previously captured snapshot, bumping the version.

        The restored state gets version = snapshot.version + 1 so that any
        concurrent writers that fetched after the snapshot will get an
        OptimisticLockError rather than silently overwriting the restore.
        """
        async with self.lock(case_id):
            restored = snapshot.state.model_copy(deep=True)
            restored.version = snapshot.version + 1
            restored.updated_at = datetime.utcnow()

            self._cache[case_id] = restored
            await self._persist_to_db(case_id, restored)

            logger.info(
                f"ContextStore: restored case {case_id} from snapshot "
                f"v{snapshot.version} → v{restored.version}"
            )
            return restored

    def evict(self, case_id: UUID) -> None:
        """Remove a case from the in-memory cache (forces next get() to hit DB)."""
        self._cache.pop(case_id, None)
        self._locks.pop(case_id, None)


# Process-level singleton — imported by agents and services.
context_store = ContextStoreService()
