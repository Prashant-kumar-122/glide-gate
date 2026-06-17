"""Permission guard — require_permission() FastAPI dependency (Phase 7).

Replaces require_role() across all routers.  Checks that at least one of the
user's persona_codes has the requested permission scope in domain_permissions.

JWT carries both "roles" (list, authoritative) and "role" (primary, backwards compat).
Cache key is (frozenset(persona_codes), scope) so multi-role lookups collapse correctly.

The permission catalog (15 scopes) is defined in
docs/specs/permission-model-security-review.md.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.database import get_db

# (frozenset[persona_codes], scope) → bool.  Cleared on startup; invalidated by admin portal (Phase 9).
_perm_cache: dict[tuple[frozenset[str], str], bool] = {}

# Legacy camel-case or run-together role strings that need mapping.
_ROLE_ALIAS: dict[str, str] = {
    "complianceofficer": "compliance_officer",
    "ccrep": "cc_rep",
}


def _normalize_role(role: str) -> str:
    normalized = role.lower().strip()
    return _ROLE_ALIAS.get(normalized, normalized)


def _extract_persona_codes(user: dict[str, Any]) -> list[str]:
    """Return normalized persona codes from the JWT user dict.

    Reads "roles" (list, Phase 7+ tokens) and falls back to "role" (string,
    legacy tokens and DEMO_USER that hasn't been regenerated).
    """
    raw = user.get("roles") or [user.get("role", "")]
    return [_normalize_role(r) for r in raw if r]


def clear_permission_cache() -> None:
    """Clear the in-process permission cache (call after bulk permission updates)."""
    _perm_cache.clear()


async def has_permission(user: dict[str, Any], scope: str, db: AsyncSession) -> bool:
    """Return True if any of the user's personas have *scope* in domain_permissions.

    Uses the same cache as require_permission() so results are shared.
    Does NOT raise — callers decide what to do on False.
    """
    from app.models.domain import DomainPermission  # local import avoids circular

    persona_codes = _extract_persona_codes(user)
    if not persona_codes:
        return False

    cache_key = (frozenset(persona_codes), scope)
    cached = _perm_cache.get(cache_key)
    if cached is not None:
        return cached

    row = await db.scalar(
        select(DomainPermission)
        .where(
            DomainPermission.persona_code.in_(persona_codes),
            DomainPermission.permission_scope == scope,
        )
        .limit(1)
    )
    granted = row is not None
    _perm_cache[cache_key] = granted
    return granted


def require_permission(scope: str) -> Callable[..., Any]:
    """FastAPI dependency: 403 if none of the user's personas have *scope* in domain_permissions."""

    async def _guard(
        user: dict[str, Any] = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        persona_codes = _extract_persona_codes(user)
        if not persona_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing role in token",
            )

        granted = await has_permission(user, scope, db)
        if not granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{scope}' not granted to persona(s) {sorted(persona_codes)!r}",
            )
        return user

    return _guard
