from __future__ import annotations

import time
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

# ── Local JWT (HS256) ─────────────────────────────────────────────────────────

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


# ── Keycloak JWT (RS256 via JWKS) ─────────────────────────────────────────────

_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 3600  # re-fetch public keys every hour

_APP_ROLES = {"advisor", "client", "admin", "sales_manager"}


async def _get_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = time.time()
    if _jwks_cache is None or (now - _jwks_fetched_at) > _JWKS_TTL:
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.keycloak_jwks_url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = now
    return _jwks_cache


async def _decode_keycloak_jwt(token: str) -> dict[str, Any]:
    try:
        jwks = await _get_jwks()
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        # Match the signing key by kid; fall back to first key if kid absent
        key = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == kid),
            jwks.get("keys", [{}])[0] if jwks.get("keys") else None,
        )
        if not key:
            raise ValueError("No matching JWKS key found")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        if payload.get("sub") is None:
            raise ValueError("Missing sub claim")

        # Keycloak stores realm roles under realm_access.roles
        realm_roles: list[str] = payload.get("realm_access", {}).get("roles", [])
        role = next((r for r in realm_roles if r in _APP_ROLES), "client")

        return {
            "sub": payload["sub"],
            "email": payload.get("email", ""),
            "role": role,
            "name": payload.get("name", payload.get("preferred_username", "")),
        }
    except (JWTError, ValueError, httpx.HTTPError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Unified dependency ────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    token: str | None = None

    if credentials is not None:
        token = credentials.credentials
    else:
        token = request.cookies.get(settings.AUTH_COOKIE_NAME)

    if token:
        # Auto-detect by algorithm: RS256 = Keycloak JWKS, HS256 = local DB users
        try:
            alg = jwt.get_unverified_header(token).get("alg", "HS256")
        except Exception:
            alg = "HS256"

        if alg == "RS256":
            return await _decode_keycloak_jwt(token)
        return _decode_jwt(token)

    if settings.DEMO_MODE:
        return DEMO_USER

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authorization",
        headers={"WWW-Authenticate": "Bearer"},
    )
