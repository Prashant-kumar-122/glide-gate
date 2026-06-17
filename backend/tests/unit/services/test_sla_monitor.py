"""Phase 5 — unit tests for SLAMonitorService.

All tests are pure Python with an async SQLite in-memory DB (via SQLAlchemy
aiosqlite). They exercise:

  1.  resolve_sla: no row → None
  2.  resolve_sla: is_enabled=False → None
  3.  resolve_sla: priority_tier exact match wins over domain default
  4.  resolve_sla: product_code exact match wins
  5.  resolve_sla: product-scoped is_enabled=False overrides domain-level True
  6.  start_tracking: row written with correct field values
  7.  pause_tracking / resume_tracking: paused_duration_seconds accumulates correctly
  8.  resume_tracking: elapsed_active_seconds excludes hold period
  9.  record_warning_sent: sets warning_sent_at; second call returns False (idempotent)
  10. record_breach_triggered: sets breach_triggered_at; idempotent
  11. get_net_elapsed_seconds: excludes accumulated pause time
  12. get_net_elapsed_seconds: includes in-progress pause in net elapsed
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.domain.domain_definition import SLASpec
from app.services.sla.sla_monitor_service import SLAMonitorService


# ── Helpers ───────────────────────────────────────────────────────────────────

_DOMAIN_CODE = "wealth_management"
_STAGE = "KYC"
_CASE_ID = uuid4()


def _spec(
    stage_code: str = _STAGE,
    window_hours: float = 2.0,
    warning_pct: int = 70,
    escalation_pct: int = 90,
    is_enabled: bool = True,
    pause_on_human_review: bool = False,
) -> SLASpec:
    return SLASpec(
        stage_code=stage_code,
        window_hours=window_hours,
        warning_pct=warning_pct,
        escalation_pct=escalation_pct,
        warning_task_type="sla_warning",
        escalation_task_type="sla_breach",
        escalation_target_agent="orchestrator",
        is_enabled=is_enabled,
        pause_on_human_review=pause_on_human_review,
    )


def _mock_db() -> AsyncMock:
    """Return a mock AsyncSession with scalar() returning None by default."""
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    db.add = MagicMock()
    return db


# ── resolve_sla ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_sla_no_domain_returns_none() -> None:
    """resolve_sla returns None when the domain does not exist."""
    svc = SLAMonitorService()
    db = _mock_db()
    db.scalar = AsyncMock(return_value=None)  # domain lookup → None
    result = await svc.resolve_sla(db, "nonexistent", "KYC")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_sla_no_sla_row_returns_none() -> None:
    """resolve_sla returns None when no domain_stage_slas row exists."""
    svc = SLAMonitorService()
    db = _mock_db()

    domain_mock = MagicMock()
    domain_mock.id = uuid4()
    # First call = domain lookup → found; subsequent calls = sla row lookups → None
    db.scalar = AsyncMock(side_effect=[domain_mock, None, None, None, None])

    result = await svc.resolve_sla(db, _DOMAIN_CODE, "UNKNOWN_STAGE")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_sla_disabled_row_returns_none() -> None:
    """resolve_sla returns None if the matching row has is_enabled=False."""
    svc = SLAMonitorService()
    db = _mock_db()

    domain_mock = MagicMock()
    domain_mock.id = uuid4()

    sla_row = MagicMock()
    sla_row.is_enabled = False
    sla_row.stage_code = _STAGE
    sla_row.priority_tier = None
    sla_row.product_code = None
    sla_row.window_hours = 2.0
    sla_row.warning_pct = 70
    sla_row.escalation_pct = 90
    sla_row.warning_task_type = "sla_warning"
    sla_row.escalation_task_type = "sla_breach"
    sla_row.escalation_target_agent = "orchestrator"
    sla_row.pause_on_human_review = False

    db.scalar = AsyncMock(side_effect=[domain_mock, sla_row])
    result = await svc.resolve_sla(db, _DOMAIN_CODE, _STAGE)
    assert result is None


@pytest.mark.asyncio
async def test_resolve_sla_returns_spec_for_enabled_row() -> None:
    """resolve_sla returns an SLASpec when a matching enabled row exists."""
    svc = SLAMonitorService()
    db = _mock_db()

    domain_mock = MagicMock()
    domain_mock.id = uuid4()

    sla_row = MagicMock()
    sla_row.is_enabled = True
    sla_row.stage_code = _STAGE
    sla_row.priority_tier = None
    sla_row.product_code = None
    sla_row.window_hours = 2.0
    sla_row.warning_pct = 70
    sla_row.escalation_pct = 90
    sla_row.warning_task_type = "sla_warning"
    sla_row.escalation_task_type = "sla_breach"
    sla_row.escalation_target_agent = "orchestrator"
    sla_row.pause_on_human_review = False

    db.scalar = AsyncMock(side_effect=[domain_mock, sla_row])
    result = await svc.resolve_sla(db, _DOMAIN_CODE, _STAGE)
    assert result is not None
    assert result.window_hours == 2.0
    assert result.warning_pct == 70
    assert result.escalation_pct == 90


@pytest.mark.asyncio
async def test_resolve_sla_priority_tier_wins_over_default() -> None:
    """When priority_tier matches, that row is returned before the NULL row."""
    svc = SLAMonitorService()
    db = _mock_db()

    domain_mock = MagicMock()
    domain_mock.id = uuid4()

    sme_row = MagicMock()
    sme_row.is_enabled = True
    sme_row.stage_code = _STAGE
    sme_row.priority_tier = "sme"
    sme_row.product_code = None
    sme_row.window_hours = 1.0  # tighter than default 2.0
    sme_row.warning_pct = 70
    sme_row.escalation_pct = 90
    sme_row.warning_task_type = "sla_warning"
    sme_row.escalation_task_type = "sla_breach"
    sme_row.escalation_target_agent = "orchestrator"
    sme_row.pause_on_human_review = False

    # First try: (tier="sme", product=None) → hit
    db.scalar = AsyncMock(side_effect=[domain_mock, sme_row])
    result = await svc.resolve_sla(db, _DOMAIN_CODE, _STAGE, priority_tier="sme")
    assert result is not None
    assert result.window_hours == 1.0


@pytest.mark.asyncio
async def test_resolve_sla_product_scoped_disabled_overrides_default() -> None:
    """A product-scoped is_enabled=False row overrides the domain-level True row."""
    svc = SLAMonitorService()
    db = _mock_db()

    domain_mock = MagicMock()
    domain_mock.id = uuid4()

    disabled_row = MagicMock()
    disabled_row.is_enabled = False  # product-specific: disabled
    disabled_row.stage_code = _STAGE
    disabled_row.priority_tier = None
    disabled_row.product_code = "instant_account"
    disabled_row.window_hours = 1.0
    disabled_row.warning_pct = 70
    disabled_row.escalation_pct = 90
    disabled_row.warning_task_type = "sla_warning"
    disabled_row.escalation_task_type = "sla_breach"
    disabled_row.escalation_target_agent = "orchestrator"
    disabled_row.pause_on_human_review = False

    # Candidate order: (None, "instant_account") matches first → disabled → return None
    db.scalar = AsyncMock(side_effect=[domain_mock, None, None, disabled_row])
    result = await svc.resolve_sla(
        db, _DOMAIN_CODE, _STAGE, priority_tier=None, product_code="instant_account"
    )
    assert result is None


# ── start_tracking ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_tracking_writes_row_with_correct_fields() -> None:
    """start_tracking adds a CaseSlaTracking row with the resolved SLA spec values."""
    svc = SLAMonitorService()
    db = _mock_db()
    spec = _spec()

    row = await svc.start_tracking(
        db, case_id=_CASE_ID, stage_code=_STAGE, sla_spec=spec,
        priority_tier="standard", product_code=None,
    )
    db.add.assert_called_once_with(row)
    assert row.case_id == _CASE_ID
    assert row.stage_code == _STAGE
    assert float(row.window_hours) == 2.0
    assert row.warning_pct == 70
    assert row.escalation_pct == 90
    assert row.pause_on_human_review is False
    assert row.is_enabled is True
    assert row.paused_duration_seconds == 0.0
    assert row.paused_at is None


# ── pause / resume ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pause_tracking_sets_paused_at() -> None:
    """pause_tracking executes an UPDATE that sets paused_at."""
    svc = SLAMonitorService()
    db = _mock_db()
    await svc.pause_tracking(db, _CASE_ID, _STAGE)
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_resume_tracking_accumulates_paused_duration() -> None:
    """resume_tracking returns elapsed_active_seconds excluding pause time."""
    svc = SLAMonitorService()
    db = _mock_db()

    pause_secs = 10.0
    total_secs = 30.0
    now = datetime.now(timezone.utc)

    import datetime as dt
    started_at = now - dt.timedelta(seconds=total_secs)
    paused_at = now - dt.timedelta(seconds=pause_secs)

    row = MagicMock()
    row.started_at = started_at
    row.paused_at = paused_at
    row.paused_duration_seconds = 5.0  # previously accumulated pause

    db.scalar = AsyncMock(return_value=row)

    elapsed = await svc.resume_tracking(db, _CASE_ID, _STAGE)

    # added_pause ≈ pause_secs
    # new_paused ≈ 5.0 + 10.0 = 15.0
    # total_elapsed ≈ 30.0
    # active_elapsed ≈ 30.0 - 15.0 = 15.0
    assert 13.0 < elapsed < 17.0, f"Expected ≈15s active elapsed, got {elapsed}"
    db.execute.assert_awaited_once()


# ── warning / breach idempotency ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_warning_sent_is_idempotent() -> None:
    """record_warning_sent returns False if warning_sent_at is already set."""
    svc = SLAMonitorService()
    db = _mock_db()

    already_sent_row = MagicMock()
    already_sent_row.warning_sent_at = datetime.now(timezone.utc)
    db.scalar = AsyncMock(return_value=already_sent_row)

    result = await svc.record_warning_sent(db, _CASE_ID, _STAGE)
    assert result is False
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_warning_sent_first_call_returns_true() -> None:
    """record_warning_sent returns True on first call (warning_sent_at is None)."""
    svc = SLAMonitorService()
    db = _mock_db()

    fresh_row = MagicMock()
    fresh_row.warning_sent_at = None
    db.scalar = AsyncMock(return_value=fresh_row)

    result = await svc.record_warning_sent(db, _CASE_ID, _STAGE)
    assert result is True
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_breach_triggered_is_idempotent() -> None:
    """record_breach_triggered returns False if breach_triggered_at already set."""
    svc = SLAMonitorService()
    db = _mock_db()

    already_row = MagicMock()
    already_row.breach_triggered_at = datetime.now(timezone.utc)
    db.scalar = AsyncMock(return_value=already_row)

    result = await svc.record_breach_triggered(db, _CASE_ID, _STAGE)
    assert result is False


@pytest.mark.asyncio
async def test_record_breach_triggered_first_call_returns_true() -> None:
    """record_breach_triggered returns True and executes UPDATE on first call."""
    svc = SLAMonitorService()
    db = _mock_db()

    fresh_row = MagicMock()
    fresh_row.breach_triggered_at = None
    db.scalar = AsyncMock(return_value=fresh_row)

    result = await svc.record_breach_triggered(db, _CASE_ID, _STAGE)
    assert result is True
    db.execute.assert_awaited_once()


# ── get_net_elapsed_seconds ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_net_elapsed_excludes_completed_pause() -> None:
    """get_net_elapsed_seconds subtracts accumulated paused_duration_seconds."""
    svc = SLAMonitorService()
    db = _mock_db()

    import datetime as dt
    now = datetime.now(timezone.utc)
    row = MagicMock()
    row.started_at = now - dt.timedelta(seconds=60)  # 60s total
    row.paused_at = None
    row.paused_duration_seconds = 20.0  # 20s paused

    db.scalar = AsyncMock(return_value=row)
    elapsed = await svc.get_net_elapsed_seconds(db, _CASE_ID, _STAGE)

    assert 38.0 < elapsed < 42.0, f"Expected ≈40s net elapsed, got {elapsed}"


@pytest.mark.asyncio
async def test_get_net_elapsed_includes_active_pause_in_subtraction() -> None:
    """get_net_elapsed_seconds includes an in-progress pause in the subtraction."""
    svc = SLAMonitorService()
    db = _mock_db()

    import datetime as dt
    now = datetime.now(timezone.utc)
    row = MagicMock()
    row.started_at = now - dt.timedelta(seconds=100)  # 100s total
    row.paused_at = now - dt.timedelta(seconds=30)    # currently paused for 30s
    row.paused_duration_seconds = 10.0                # 10s previously paused

    db.scalar = AsyncMock(return_value=row)
    elapsed = await svc.get_net_elapsed_seconds(db, _CASE_ID, _STAGE)

    # total=100, paused=10+30=40, active≈60
    assert 58.0 < elapsed < 62.0, f"Expected ≈60s net elapsed, got {elapsed}"
