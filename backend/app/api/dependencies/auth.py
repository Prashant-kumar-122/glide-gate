from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

security = HTTPBearer(auto_error=False)

DEMO_USER: dict[str, Any] = {
    "sub": "00000000-0000-0000-0000-000000000001",
    "email": "advisor@demo.glide-gate.local",
    "role": "advisor",
    "name": "Demo Advisor",
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    # If a real Bearer token is present, always decode it — demo mode is only a
    # fallback for unauthenticated requests so the frontend can browse without logging in.
    if credentials is not None:
        try:
            payload = jwt.decode(
                credentials.credentials,
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

    if settings.DEMO_MODE:
        return DEMO_USER

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authorization header",
        headers={"WWW-Authenticate": "Bearer"},
    )
