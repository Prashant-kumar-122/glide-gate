"""Seed users for auth system.

Users (separate from onboarding clients):
  - admin@glide-gate.local              / Admin123!         / admin
  - advisor@glide-gate.local            / Advisor123!       / advisor
  - salesmanager@glide-gate.local       / Sales123!         / sales_manager
  - aarav.mehta@demo.glide-gate.local   / Client123!        / client
  - deposit.ops@glide-gate.local        / DepositOps123!    / deposit_ops     (retail_deposit domain)
  - branch.manager@glide-gate.local     / BranchManager123! / branch_manager  (retail_deposit domain)
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User, UserPersona
from app.services.auth.auth_service import hash_password

ADMIN_USER_ID         = UUID("b0000000-0001-0001-0001-000000000001")
ADVISOR_USER_ID       = UUID("b0000000-0002-0002-0002-000000000002")
SALES_MANAGER_USER_ID = UUID("b0000000-0003-0003-0003-000000000003")
# Must match the clients.id for Aarav Mehta so case lookups by user sub work
CLIENT_USER_ID        = UUID("d0000000-0001-0001-0001-000000000001")
DEPOSIT_OPS_USER_ID   = UUID("b0000000-0005-0005-0005-000000000005")
BRANCH_MANAGER_USER_ID = UUID("b0000000-0006-0006-0006-000000000006")

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
        "id": SALES_MANAGER_USER_ID,
        "email": "salesmanager@glide-gate.local",
        "first_name": "Demo",
        "last_name": "SalesManager",
        "password": "Sales123!",
        "role": "sales_manager",
    },
    {
        "id": CLIENT_USER_ID,
        "email": "aarav.mehta@demo.glide-gate.local",
        "first_name": "Aarav",
        "last_name": "Mehta",
        "password": "Client123!",
        "role": "client",
    },
    {
        "id": DEPOSIT_OPS_USER_ID,
        "email": "deposit.ops@glide-gate.local",
        "first_name": "Demo",
        "last_name": "DepositOps",
        "password": "DepositOps123!",
        "role": "deposit_ops",
    },
    {
        "id": BRANCH_MANAGER_USER_ID,
        "email": "branch.manager@glide-gate.local",
        "first_name": "Demo",
        "last_name": "BranchManager",
        "password": "BranchManager123!",
        "role": "branch_manager",
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
        )
        session.add(user)
        session.add(UserPersona(user_id=u["id"], persona_code=u["role"]))
        print(f"  seed  {u['email']}  [{u['role']}]")

    await session.commit()
    print("  Users seeded.")
