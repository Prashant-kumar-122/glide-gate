"""Phase 8 — unit tests for ContextStoreService stage validation.

These tests verify that the application-layer stage gate introduced in Phase 8
correctly replaces the dropped oc_stage_chk / oc_status_chk DB CHECK constraints.

All tests mock the DB layer so no real database is needed.

Scenarios:
  1. Valid domain stage → _validate_stage passes silently
  2. Stage not in domain_stages → ValueError raised
  3. update() with stage in patches → validation fires
  4. update() without stage key → validation is NOT called (no spurious DB hit)
  5. Unknown domain code → ValueError raised (domain row absent → count = 0)
  6. Stage valid in old CHECK enum but absent from domain_stages → still rejected
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.context_store.context_store_service import ContextStoreService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_session_count(count: int):
    """Return an async context-manager mock whose execute().scalar() returns `count`."""
    result_mock = MagicMock()
    result_mock.scalar.return_value = count

    session_mock = AsyncMock()
    session_mock.execute = AsyncMock(return_value=result_mock)

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ── _validate_stage tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_stage_valid():
    """Valid stage code → no exception."""
    svc = ContextStoreService()
    with patch(
        "app.services.context_store.context_store_service.AsyncSessionLocal",
        return_value=_mock_session_count(1),
    ):
        await svc._validate_stage("KYC")  # should not raise


@pytest.mark.asyncio
async def test_validate_stage_invalid_raises():
    """Stage absent from domain_stages → ValueError."""
    svc = ContextStoreService()
    with patch(
        "app.services.context_store.context_store_service.AsyncSessionLocal",
        return_value=_mock_session_count(0),
    ):
        with pytest.raises(ValueError, match="Invalid stage 'NONEXISTENT_STAGE'"):
            await svc._validate_stage("NONEXISTENT_STAGE")


@pytest.mark.asyncio
async def test_validate_stage_old_enum_value_rejected_if_not_in_domain():
    """A stage that was valid in the old DB CHECK but is absent from domain_stages
    is correctly rejected at the application layer (proves DB constraint removal
    did not widen the acceptance window)."""
    svc = ContextStoreService()
    # Simulate a domain that has dropped SALES_REVIEW from its configuration
    with patch(
        "app.services.context_store.context_store_service.AsyncSessionLocal",
        return_value=_mock_session_count(0),
    ):
        with pytest.raises(ValueError, match="SALES_REVIEW"):
            await svc._validate_stage("SALES_REVIEW")


@pytest.mark.asyncio
async def test_validate_stage_unknown_domain_raises():
    """Querying against a non-existent domain → count is 0 → ValueError."""
    svc = ContextStoreService()
    with patch(
        "app.services.context_store.context_store_service.AsyncSessionLocal",
        return_value=_mock_session_count(0),
    ):
        with pytest.raises(ValueError, match="retail_deposit"):
            await svc._validate_stage("INTAKE", domain_code="retail_deposit")


# ── update() integration ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_calls_validate_when_stage_in_patches():
    """update() triggers _validate_stage when 'stage' key is present in patches."""
    svc = ContextStoreService()
    case_id = uuid4()

    with patch.object(svc, "_validate_stage", new=AsyncMock()) as mock_validate, \
         patch.object(svc, "get", new=AsyncMock()), \
         patch.object(svc, "_get_lock", return_value=_noop_lock()), \
         patch.object(svc, "_persist_to_db", new=AsyncMock()):

        from app.agents.base.a2a_types import OnboardingState, OnboardingStage
        from datetime import datetime

        current = OnboardingState(
            case_id=case_id,
            client_id=uuid4(),
            stage=OnboardingStage.KYC,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        svc.get.return_value = current

        await svc.update(case_id, {"stage": "PARALLEL_PRODUCTS"})

        mock_validate.assert_awaited_once_with("PARALLEL_PRODUCTS")


@pytest.mark.asyncio
async def test_update_skips_validate_when_no_stage_in_patches():
    """update() does NOT call _validate_stage when 'stage' is absent from patches."""
    svc = ContextStoreService()
    case_id = uuid4()

    with patch.object(svc, "_validate_stage", new=AsyncMock()) as mock_validate, \
         patch.object(svc, "get", new=AsyncMock()), \
         patch.object(svc, "_get_lock", return_value=_noop_lock()), \
         patch.object(svc, "_persist_to_db", new=AsyncMock()):

        from app.agents.base.a2a_types import OnboardingState, OnboardingStage
        from datetime import datetime

        current = OnboardingState(
            case_id=case_id,
            client_id=uuid4(),
            stage=OnboardingStage.KYC,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        svc.get.return_value = current

        await svc.update(case_id, {"priority_tier": "sme"})  # no stage key

        mock_validate.assert_not_awaited()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _noop_lock():
    """Async context manager that acquires/releases immediately."""
    import asyncio

    lock = asyncio.Lock()

    class _Ctx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *_):
            return False

    return _Ctx()
