from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status

from app.api.dependencies.auth import get_current_user


def require_role(*roles: str) -> Callable[..., Any]:
    """Return a FastAPI dependency that 403s if the token role is not in *roles*."""

    allowed = {r.lower() for r in roles}

    async def _guard(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if (user.get("role") or "").lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.get('role')}' is not authorised for this operation",
            )
        return user

    return _guard
