from __future__ import annotations

import re
import secrets
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func, select

from app.api.dependencies.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.users import User, UserPersona
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_MIN_PASSWORD_LEN = 8
_DIGIT_RE = re.compile(r"\d")


def _validate_password(v: str) -> str:
    if len(v) < _MIN_PASSWORD_LEN:
        raise ValueError(f"Password must be at least {_MIN_PASSWORD_LEN} characters")
    if not _DIGIT_RE.search(v):
        raise ValueError("Password must contain at least one digit")
    return v


def _set_auth_cookies(response: Response, token: str) -> None:
    max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    csrf_token = secrets.token_hex(32)
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=max_age,
        path="/",
    )
    # Non-httpOnly so the frontend JS can read and echo it as X-CSRF-Token
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=max_age,
        path="/",
    )


# Pydantic schemas

class SignupRequest(BaseModel):
    email: str = Field(max_length=254)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info: Any) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class ProfileUpdateRequest(BaseModel):
    email: str | None = Field(default=None, max_length=254)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    confirm_password: str | None = Field(default=None, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_password(v)
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str | None, info: Any) -> str | None:
        pw = info.data.get("password")
        if pw is not None and v != pw:
            raise ValueError("Passwords do not match")
        return v


class UserOut(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    roles: list[str]
    role: str  # primary persona, kept for API backwards compat

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# Endpoints

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    async with db.begin():
        token, user = await auth_service.signup(
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            password=body.password,
            db=db,
        )
    _set_auth_cookies(response, token)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    async with db.begin():
        token, user = await auth_service.login(email=body.email, password=body.password, db=db)
    _set_auth_cookies(response, token)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout")
async def logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/")
    return response


@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user_id = UUID(current_user["sub"])
    async with db.begin():
        user = await auth_service.get_profile(user_id, db)
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    if body.password is not None and body.confirm_password is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="confirm_password is required when changing password",
        )
    user_id = UUID(current_user["sub"])
    async with db.begin():
        user = await auth_service.update_profile(
            user_id,
            db,
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            password=body.password,
        )
    return UserOut.model_validate(user)


@router.get("/advisors", response_model=list[UserOut])
async def list_advisors(
    _current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    result = await db.execute(
        select(User)
        .join(UserPersona, User.id == UserPersona.user_id)
        .where(UserPersona.persona_code == "advisor", User.is_active.is_(True))
        .order_by(User.first_name)
    )
    return [UserOut.model_validate(u) for u in result.scalars().all()]


@router.get("/lookup-client", response_model=UserOut)
async def lookup_client(
    email: str,
    _current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    result = await db.execute(
        select(User).where(func.lower(User.email) == email.strip().lower(), User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no_account_found")
    if user.role != "client":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="not_a_client")
    return UserOut.model_validate(user)
