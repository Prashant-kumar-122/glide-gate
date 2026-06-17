"""Phase 9 — unit tests for admin portal domain validation logic.

Tests are pure Python (no FastAPI TestClient, no live DB).  They cover:

  DomainCreate pydantic model:
  1.  Valid domain_code (lowercase alpha+underscore) is accepted
  2.  Invalid domain_code (uppercase / spaces) rejected by pattern
  3.  Empty domain_code rejected by min_length

  SLACreate model validator (warning_pct / escalation_pct ordering):
  4.  warning_pct < escalation_pct is accepted
  5.  warning_pct == escalation_pct raises ValueError
  6.  warning_pct > escalation_pct raises ValueError

  SLAUpdate model validator (partial update — only fires when both are present):
  7.  Both present and warning < escalation → accepted
  8.  Both present and warning >= escalation → ValueError
  9.  Only warning_pct present (no escalation_pct) → accepted (no cross-check)
  10. Only escalation_pct present (no warning_pct) → accepted

  AgentStatusUpdate pattern guard:
  11. APPROVED is accepted
  12. DEPRECATED is accepted
  13. ACTIVE (unrecognised) is rejected by pattern
  14. empty string rejected

  _REGULATED_STAGES set (white-box coverage):
  15. All four regulated stage codes are members of the set
  16. A non-regulated code is NOT a member

  validate_domain route helper: DomainValidationResult shape
  17. valid=True → errors list is empty
  18. valid=False → errors list is non-empty

  activate_domain guard: DomainValidationError triggers UnprocessableError
  19. Route raises UnprocessableError when DomainDefinitionLoader.load raises DomainValidationError
  20. Route sets is_active=True and commits when validation passes
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routers.admin.domains import (
    DomainCreate,
    DomainValidationResult,
    activate_domain,
)
from app.api.routers.admin.sla import (
    SLACreate,
    SLAUpdate,
    _REGULATED_STAGES,
)
from app.api.routers.admin.agents import AgentStatusUpdate
from app.api.error_handlers import UnprocessableError
from app.domain.domain_definition import DomainValidationError


# ── DomainCreate ──────────────────────────────────────────────────────────────

def test_domain_create_valid_code():
    m = DomainCreate(domain_code="wealth_management", display_name="Wealth")
    assert m.domain_code == "wealth_management"


def test_domain_create_uppercase_rejected():
    with pytest.raises(ValidationError) as exc_info:
        DomainCreate(domain_code="WealthManagement", display_name="Wealth")
    assert "domain_code" in str(exc_info.value) or "pattern" in str(exc_info.value).lower()


def test_domain_create_spaces_rejected():
    with pytest.raises(ValidationError):
        DomainCreate(domain_code="wealth management", display_name="Wealth")


def test_domain_create_empty_code_rejected():
    with pytest.raises(ValidationError):
        DomainCreate(domain_code="", display_name="Wealth")


# ── SLACreate model validator ─────────────────────────────────────────────────

def test_sla_create_valid_pcts():
    sla = SLACreate(stage_code="KYC", window_hours=24, warning_pct=80, escalation_pct=100)
    assert sla.warning_pct == 80
    assert sla.escalation_pct == 100


def test_sla_create_equal_pcts_rejected():
    with pytest.raises(ValidationError) as exc_info:
        SLACreate(stage_code="KYC", window_hours=24, warning_pct=80, escalation_pct=80)
    assert "warning_pct" in str(exc_info.value)


def test_sla_create_inverted_pcts_rejected():
    with pytest.raises(ValidationError):
        SLACreate(stage_code="KYC", window_hours=24, warning_pct=95, escalation_pct=80)


# ── SLAUpdate model validator ─────────────────────────────────────────────────

def test_sla_update_both_valid():
    u = SLAUpdate(warning_pct=70, escalation_pct=90)
    assert u.warning_pct == 70


def test_sla_update_both_equal_rejected():
    with pytest.raises(ValidationError):
        SLAUpdate(warning_pct=80, escalation_pct=80)


def test_sla_update_only_warning_pct_accepted():
    u = SLAUpdate(warning_pct=75)
    assert u.warning_pct == 75
    assert u.escalation_pct is None


def test_sla_update_only_escalation_pct_accepted():
    u = SLAUpdate(escalation_pct=110)
    assert u.escalation_pct == 110
    assert u.warning_pct is None


# ── AgentStatusUpdate ─────────────────────────────────────────────────────────

def test_agent_status_approved():
    m = AgentStatusUpdate(status="APPROVED")
    assert m.status == "APPROVED"


def test_agent_status_deprecated():
    m = AgentStatusUpdate(status="DEPRECATED")
    assert m.status == "DEPRECATED"


def test_agent_status_unrecognised_rejected():
    with pytest.raises(ValidationError):
        AgentStatusUpdate(status="ACTIVE")


def test_agent_status_empty_rejected():
    with pytest.raises(ValidationError):
        AgentStatusUpdate(status="")


# ── _REGULATED_STAGES ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("stage", ["KYC", "REVIEW", "SALES_REVIEW", "ESCALATED"])
def test_regulated_stage_membership(stage: str):
    assert stage in _REGULATED_STAGES


def test_non_regulated_stage_not_member():
    assert "ONBOARDING" not in _REGULATED_STAGES


# ── DomainValidationResult shape ──────────────────────────────────────────────

def test_validation_result_valid():
    r = DomainValidationResult(valid=True, errors=[])
    assert r.valid is True
    assert r.errors == []


def test_validation_result_invalid():
    r = DomainValidationResult(valid=False, errors=["dangling transition: FOO→BAR"])
    assert r.valid is False
    assert len(r.errors) == 1


# ── activate_domain route (async, mocked DB) ──────────────────────────────────

def _make_domain_mock(domain_id_str: str) -> MagicMock:
    """Return a mock Domain ORM object."""
    from uuid import UUID
    d = MagicMock()
    d.id = UUID(domain_id_str)
    d.domain_code = "test_domain"
    d.display_name = "Test Domain"
    d.is_active = False
    d.created_at = MagicMock()
    d.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    d.updated_at = MagicMock()
    d.updated_at.isoformat.return_value = "2026-01-01T00:00:00"
    return d


def _make_db_returning(domain_mock) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = domain_mock
    db.execute = AsyncMock(return_value=result)
    return db


_DOMAIN_UUID = "00000000-0000-0000-0000-000000000042"


@pytest.mark.asyncio
async def test_activate_raises_unprocessable_on_validation_error():
    """activate_domain must raise UnprocessableError when loader raises DomainValidationError."""
    from uuid import UUID

    domain_mock = _make_domain_mock(_DOMAIN_UUID)
    db = _make_db_returning(domain_mock)
    user = {"sub": "admin", "roles": ["admin"], "role": "admin"}

    with patch(
        "app.api.routers.admin.domains.DomainDefinitionLoader.load",
        new_callable=AsyncMock,
        side_effect=DomainValidationError("dangling transition"),
    ):
        with pytest.raises(UnprocessableError):
            await activate_domain(
                domain_id=UUID(_DOMAIN_UUID),
                _user=user,
                db=db,
            )


@pytest.mark.asyncio
async def test_activate_sets_is_active_when_valid():
    """activate_domain sets is_active=True and calls db.commit when validation passes."""
    from uuid import UUID

    domain_mock = _make_domain_mock(_DOMAIN_UUID)
    db = _make_db_returning(domain_mock)
    user = {"sub": "admin", "roles": ["admin"], "role": "admin"}

    with patch(
        "app.api.routers.admin.domains.DomainDefinitionLoader.load",
        new_callable=AsyncMock,
        return_value=MagicMock(),
    ):
        with patch(
            "app.api.routers.admin.domains.decision_log_service.append",
            new_callable=AsyncMock,
        ):
            await activate_domain(
                domain_id=UUID(_DOMAIN_UUID),
                _user=user,
                db=db,
            )

    assert domain_mock.is_active is True
    db.commit.assert_awaited_once()
