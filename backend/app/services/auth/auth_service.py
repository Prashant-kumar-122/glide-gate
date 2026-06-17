from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.clients import Client
from app.models.users import User, UserPersona


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    roles = user.roles  # list[str] from personas relationship (must be loaded)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "roles": roles,
        "role": roles[0] if roles else "client",  # primary role for backwards compat
        "name": user.full_name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


class AuthService:
    async def signup(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        db: AsyncSession,
    ) -> tuple[str, User]:
        existing = await db.execute(select(User).where(User.email == email.lower()))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )
        user = User(
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            password_hash=hash_password(password),
        )
        db.add(user)
        await db.flush()

        # Assign default "client" persona
        db.add(UserPersona(user_id=user.id, persona_code="client"))

        # Mirror into clients table — client_id == user.id so cases can be
        # looked up directly by the authenticated user's sub claim.
        client_exists = await db.execute(select(Client).where(Client.id == user.id))
        if client_exists.scalar_one_or_none() is None:
            client = Client(
                id=user.id,
                email=user.email,
                first_name=first_name,
                last_name=last_name,
            )
            db.add(client)

        await db.flush()
        await db.refresh(user, ["personas"])
        token = create_access_token(user)
        return token, user

    async def login(self, email: str, password: str, db: AsyncSession) -> tuple[str, User]:
        result = await db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )
        await db.refresh(user, ["personas"])
        token = create_access_token(user)
        return token, user

    async def get_profile(self, user_id: UUID, db: AsyncSession) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def update_profile(
        self,
        user_id: UUID,
        db: AsyncSession,
        *,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        password: str | None = None,
    ) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if email is not None:
            lowered = email.lower()
            if lowered != user.email:
                conflict = await db.execute(select(User).where(User.email == lowered))
                if conflict.scalar_one_or_none() is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Email is already in use",
                    )
            user.email = lowered

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if password is not None:
            user.password_hash = hash_password(password)

        user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.flush()
        return user


auth_service = AuthService()
