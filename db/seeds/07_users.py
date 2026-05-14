"""Seed users for auth system.

Users (separate from onboarding clients):
  - admin@glide-gate.local       / Admin123!    / admin
  - advisor@glide-gate.local     / Advisor123!  / advisor
  - aarav.mehta@demo.glide-gate.local / Client123! / client
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.services.auth.auth_service import hash_password

ADMIN_USER_ID   = UUID("b0000000-0001-0001-0001-000000000001")
ADVISOR_USER_ID = UUID("b0000000-0002-0002-0002-000000000002")
CLIENT_USER_ID  = UUID("b0000000-0003-0003-0003-000000000003")

_USERS = [
    {
        "id": ADMIN_USER_ID,
        "email": "admin@glide-gate.local",
        "first_name": "Admin",
        "last_name": "User",
        "password": "Admin123!",
        "role": "admin",
    },
    {
        "id": ADVISOR_USER_ID,
        "email": "advisor@glide-gate.local",
        "first_name": "Demo",
        "last_name": "Advisor",
        "password": "Advisor123!",
        "role": "advisor",
    },
    {
        "id": CLIENT_USER_ID,
        "email": "aarav.mehta@demo.glide-gate.local",
        "first_name": "Aarav",
        "last_name": "Mehta",
        "password": "Client123!",
        "role": "client",
    },
]


async def seed(session: AsyncSession) -> None:
    for u in _USERS:
        exists = await session.execute(
            text("SELECT 1 FROM users WHERE id = :id"), {"id": str(u["id"])}
        )
        if exists.scalar_one_or_none() is not None:
            print(f"  skip  {u['email']} (already exists)")
            continue

        user = User(
            id=u["id"],
            email=u["email"],
            first_name=u["first_name"],
            last_name=u["last_name"],
            password_hash=hash_password(u["password"]),
            role=u["role"],
        )
        session.add(user)
        print(f"  seed  {u['email']}  [{u['role']}]")

    await session.commit()
    print("  Users seeded.")
