from __future__ import annotations

from typing import Any

import httpx
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

# Cached Keycloak JWKS keys — refreshed on first request
_keycloak_jwks: dict[str, Any] | None = None


def _keycloak_jwks_url() -> str:
    return (
        f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/certs"
    )


async def _get_keycloak_jwks() -> dict[str, Any]:
    global _keycloak_jwks
    if _keycloak_jwks is None:
        async with httpx.AsyncClient() as client:
            response = await client.get(_keycloak_jwks_url())
            response.raise_for_status()
            _keycloak_jwks = response.json()
    return _keycloak_jwks


def _decode_jwt_local(token: str) -> dict[str, Any]:
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


async def _decode_jwt_keycloak(token: str) -> dict[str, Any]:
    global _keycloak_jwks
    try:
        jwks = await _get_keycloak_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.KEYCLOAK_CLIENT_ID,
        )
        if payload.get("sub") is None:
            raise ValueError("Missing sub claim")
        # Map Keycloak realm roles to app role field
        realm_roles: list[str] = payload.get("realm_access", {}).get("roles", [])
        app_roles = {"client", "advisor", "admin", "sales_manager"}
        matched = next((r for r in realm_roles if r in app_roles), None)
        if matched:
            payload["role"] = matched
        return payload
    except (JWTError, ValueError):
        # Force JWKS refresh on next request in case keys were rotated
        _keycloak_jwks = None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def _decode_jwt(token: str) -> dict[str, Any]:
    if settings.AUTH_PROVIDER == "keycloak":
        return await _decode_jwt_keycloak(token)
    return _decode_jwt_local(token)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    # Bearer header takes precedence (API clients, demo mode, service tests)
    if credentials is not None:
        return await _decode_jwt(credentials.credentials)

    # HttpOnly cookie (browser sessions — primary path)
    cookie_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if cookie_token:
        return await _decode_jwt(cookie_token)

    if settings.DEMO_MODE:
        return DEMO_USER

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authorization",
        headers={"WWW-Authenticate": "Bearer"},
    )
