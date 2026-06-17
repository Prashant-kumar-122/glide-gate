from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

security = HTTPBearer(auto_error=False)

DEMO_USER: dict[str, Any] = {
    "sub": "00000000-0000-0000-0000-000000000001",
    "email": "advisor@demo.glide-gate.local",
    "roles": ["advisor"],
    "role": "advisor",
    "name": "Demo Advisor",
}


def _decode_jwt(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("sub") is None:
            raise ValueError("Missing sub claim")
        return payload
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    # Bearer header takes precedence (API clients, demo mode, service tests)
    if credentials is not None:
        return _decode_jwt(credentials.credentials)

    # httpOnly cookie (browser sessions — the primary path after Phase 0)
    cookie_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if cookie_token:
        return _decode_jwt(cookie_token)

    if settings.DEMO_MODE:
        return DEMO_USER

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authorization",
        headers={"WWW-Authenticate": "Bearer"},
    )
