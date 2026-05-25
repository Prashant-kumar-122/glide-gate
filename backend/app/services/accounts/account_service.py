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


async def _unique_number(session: AsyncSession) -> str:
    for _ in range(5):
        number = _generate_number()
        conflict = await session.execute(
            select(ClientAccount.id).where(ClientAccount.account_number == number)
        )
        if conflict.scalar_one_or_none() is None:
            return number
    return _generate_number()


class AccountService:
    @staticmethod
    async def ensure_created(
        session: AsyncSession,
        case_id: UUID,
        client_id: UUID,
        products: list[str],
    ) -> list[ClientAccount]:
        """Idempotently create one ClientAccount per product for a completed case.

        Safe to call multiple times — skips products that already have an account.
        """
        result = await session.execute(
            select(ClientAccount).where(ClientAccount.case_id == case_id)
        )
        existing = {row.product: row for row in result.scalars().all()}

        accounts: list[ClientAccount] = []
        for product in products:
            if product in existing:
                accounts.append(existing[product])
                continue

            number = await _unique_number(session)
            account = ClientAccount(
                client_id=client_id,
                case_id=case_id,
                product=product,
                account_number=number,
            )
            session.add(account)
            accounts.append(account)

        return accounts
