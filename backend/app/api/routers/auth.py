from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.api.dependencies.auth import get_current_user
from app.database import get_db
from app.models.users import User
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


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    password: str
    confirm_password: str

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
    email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = None
    confirm_password: str | None = None

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
    role: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    async with db.begin():
        token, user = await auth_service.signup(
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            password=body.password,
            db=db,
        )
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    async with db.begin():
        token, user = await auth_service.login(email=body.email, password=body.password, db=db)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


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
        select(User).where(User.role == "advisor", User.is_active.is_(True)).order_by(User.first_name)
    )
    return [UserOut.model_validate(u) for u in result.scalars().all()]
