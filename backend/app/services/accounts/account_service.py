from __future__ import annotations

import random
import string
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounts import ClientAccount


def _generate_number() -> str:
    date_part = datetime.utcnow().strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"GG-{date_part}-{rand_part}"


class AccountService:
    @staticmethod
    async def ensure_created(
        session: AsyncSession,
        case_id: UUID,
        client_id: UUID,
        products: list[str],
    ) -> ClientAccount:
        """Idempotently create a ClientAccount for a completed case.

        Safe to call multiple times — returns the existing record if one already exists.
        """
        result = await session.execute(
            select(ClientAccount).where(ClientAccount.case_id == case_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Retry up to 5 times to avoid the rare collision on account_number
        number = _generate_number()
        for _ in range(4):
            conflict = await session.execute(
                select(ClientAccount.id).where(ClientAccount.account_number == number)
            )
            if conflict.scalar_one_or_none() is None:
                break
            number = _generate_number()

        account = ClientAccount(
            client_id=client_id,
            case_id=case_id,
            products=products,
            account_number=number,
        )
        session.add(account)
        return account
