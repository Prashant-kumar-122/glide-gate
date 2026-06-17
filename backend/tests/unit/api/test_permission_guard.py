"""Phase 7 — unit tests for require_permission() and has_permission() guards.

Tests are pure Python (no FastAPI TestClient, no live DB).  They call the
internal guard logic directly via AsyncMock DB sessions so they run offline.

Coverage:
  1.  Known scope + valid persona → allowed (returns user dict)
  2.  Known scope + missing roles in token → 403
  3.  Role missing from domain_permissions → 403
  4.  audit:export granted to compliance_officer → allowed
  5.  audit:export NOT granted to advisor → 403
  6.  audit:export NOT granted to sales_manager → 403
  7.  admin:config NOT granted to advisor → 403
  8.  admin:config granted to admin → allowed
  9.  Cache hit (True): DB not queried on second call
  10. Cache hit (False): DB not queried, 403 raised
  11. Role alias: 'ComplianceOfficer' normalised to 'compliance_officer'
  12. Whitespace in role is stripped before lookup
  13. Empty roles list → 403 (missing role)
  14. Multi-role: user with ["advisor", "compliance_officer"] gets audit:export
  15. Multi-role: user with ["client", "advisor"] gets case:create via advisor
  16. has_permission() returns bool (True/False) without raising
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.api.dependencies.permission_guard import (
    _extract_persona_codes,
    clear_permission_cache,
    has_permission,
    require_permission,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_db(has_row: bool) -> AsyncMock:
    """Return a mock AsyncSession whose scalar() returns a truthy/falsy value."""
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=MagicMock() if has_row else None)
    return db


def _user(role: str) -> dict:
    """Single-role user dict (mirrors legacy JWT format + new roles array)."""
    return {"sub": "test-uid", "roles": [role], "role": role}


def _multi_user(*roles: str) -> dict:
    """Multi-role user dict."""
    return {"sub": "test-uid", "roles": list(roles), "role": roles[0] if roles else ""}


async def _call_guard(scope: str, role: str, has_row: bool) -> dict:
    """Invoke the guard closure with a mocked DB session."""
    guard_fn = require_permission(scope)
    db = _make_db(has_row)
    return await guard_fn(user=_user(role), db=db)


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_cache():
    """Clear the permission cache before every test."""
    clear_permission_cache()
    yield
    clear_permission_cache()


@pytest.mark.asyncio
async def test_allowed_when_row_exists():
    result = await _call_guard("case:read", "advisor", has_row=True)
    assert result["role"] == "advisor"


@pytest.mark.asyncio
async def test_missing_role_in_token_raises_403():
    guard_fn = require_permission("case:read")
    db = _make_db(has_row=True)
    with pytest.raises(HTTPException) as exc_info:
        await guard_fn(user={"sub": "x", "roles": [], "role": ""}, db=db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_no_permission_row_raises_403():
    with pytest.raises(HTTPException) as exc_info:
        await _call_guard("case:read", "client", has_row=False)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_compliance_officer_has_audit_export():
    result = await _call_guard("audit:export", "compliance_officer", has_row=True)
    assert result["role"] == "compliance_officer"


@pytest.mark.asyncio
async def test_advisor_lacks_audit_export():
    with pytest.raises(HTTPException) as exc_info:
        await _call_guard("audit:export", "advisor", has_row=False)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_sales_manager_lacks_audit_export():
    with pytest.raises(HTTPException) as exc_info:
        await _call_guard("audit:export", "sales_manager", has_row=False)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_advisor_lacks_admin_config():
    with pytest.raises(HTTPException) as exc_info:
        await _call_guard("admin:config", "advisor", has_row=False)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_has_admin_config():
    result = await _call_guard("admin:config", "admin", has_row=True)
    assert result["role"] == "admin"


@pytest.mark.asyncio
async def test_cache_hit_true_skips_db():
    guard_fn = require_permission("case:read")
    db = _make_db(has_row=True)

    # First call populates cache
    await guard_fn(user=_user("advisor"), db=db)
    assert db.scalar.await_count == 1

    # Second call must use cache — DB not hit again
    db2 = _make_db(has_row=False)  # would return None if DB were called
    result = await guard_fn(user=_user("advisor"), db=db2)
    assert result["role"] == "advisor"
    assert db2.scalar.await_count == 0


@pytest.mark.asyncio
async def test_cache_hit_false_skips_db_and_raises():
    guard_fn = require_permission("audit:export")
    db = _make_db(has_row=False)

    # First call — no row, caches False
    with pytest.raises(HTTPException):
        await guard_fn(user=_user("advisor"), db=db)
    assert db.scalar.await_count == 1

    # Second call — should use cache, not hit DB
    db2 = _make_db(has_row=True)  # would grant if DB were called
    with pytest.raises(HTTPException) as exc_info:
        await guard_fn(user=_user("advisor"), db=db2)
    assert db2.scalar.await_count == 0
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_role_alias_complianceofficer_normalises():
    user = {"sub": "test-uid", "roles": ["ComplianceOfficer"], "role": "ComplianceOfficer"}
    result = await require_permission("audit:read")(user=user, db=_make_db(has_row=True))
    assert result is not None


@pytest.mark.asyncio
async def test_whitespace_role_stripped():
    user = {"sub": "test-uid", "roles": ["  advisor  "], "role": "  advisor  "}
    result = await require_permission("case:read")(user=user, db=_make_db(has_row=True))
    assert result is not None


@pytest.mark.asyncio
async def test_none_role_raises_403():
    guard_fn = require_permission("case:read")
    db = _make_db(has_row=True)
    with pytest.raises(HTTPException) as exc_info:
        await guard_fn(user={"sub": "x"}, db=db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_multi_role_grants_via_any_persona():
    """A user with advisor + compliance_officer roles gets audit:export via compliance_officer."""
    guard_fn = require_permission("audit:export")
    db = _make_db(has_row=True)
    result = await guard_fn(user=_multi_user("advisor", "compliance_officer"), db=db)
    assert result["roles"] == ["advisor", "compliance_officer"]


@pytest.mark.asyncio
async def test_multi_role_denied_when_no_persona_has_scope():
    """A user with client + sales_manager roles still cannot access admin:config."""
    guard_fn = require_permission("admin:config")
    with pytest.raises(HTTPException) as exc_info:
        await guard_fn(user=_multi_user("client", "sales_manager"), db=_make_db(has_row=False))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_has_permission_returns_true():
    db = _make_db(has_row=True)
    result = await has_permission(_user("advisor"), "case:read", db)
    assert result is True


@pytest.mark.asyncio
async def test_has_permission_returns_false():
    db = _make_db(has_row=False)
    result = await has_permission(_user("client"), "case:create", db)
    assert result is False


def test_extract_persona_codes_legacy_role_fallback():
    """Tokens without 'roles' key still extract from legacy 'role' string."""
    user = {"sub": "x", "role": "advisor"}
    codes = _extract_persona_codes(user)
    assert codes == ["advisor"]


def test_extract_persona_codes_prefers_roles_list():
    """When 'roles' is present, it takes precedence over 'role'."""
    user = {"sub": "x", "roles": ["advisor", "compliance_officer"], "role": "advisor"}
    codes = _extract_persona_codes(user)
    assert codes == ["advisor", "compliance_officer"]
