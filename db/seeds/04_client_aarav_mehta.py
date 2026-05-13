"""Seed: Sample client Aarav Mehta — used in demo scenarios A and B."""
from __future__ import annotations

import asyncio
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.clients import Client, ClientAddress, ClientProfile

CLIENT_ID = UUID("d0000000-0001-0001-0001-000000000001")
PROFILE_ID = UUID("d0000000-0002-0002-0002-000000000002")
ADDRESS_ID = UUID("d0000000-0003-0003-0003-000000000003")


async def seed(session: AsyncSession) -> None:
    existing = await session.get(Client, CLIENT_ID)
    if existing:
        print("  [skip] client Aarav Mehta already exists")
        return

    client = Client(
        id=CLIENT_ID,
        email="aarav.mehta@example.com",
        phone="+65-9123-4567",
        first_name="Aarav",
        last_name="Mehta",
        date_of_birth=date(1985, 3, 22),
        nationality="Indian",
        tax_residency="Singapore",
        employment_status="employed",
        annual_income=185000,
        source_of_wealth="salary_income",
        risk_appetite="moderate",
        investment_experience="moderate",
        investment_horizon="long",
        kyc_status="PENDING",
        extra_metadata={
            "demo_client": True,
            "scenario": ["scenario_a", "scenario_b"],
        },
    )
    session.add(client)
    print("  [seed] client Aarav Mehta")

    profile = ClientProfile(
        id=PROFILE_ID,
        client_id=CLIENT_ID,
        profile_data={
            "employer_name": "Nexus Capital Pte Ltd",
            "occupation": "Senior Portfolio Analyst",
        },
        consent_marketing=False,
        consent_data_processing=True,
        preferred_communication_channel="email",
        language_preference="en",
    )
    session.add(profile)
    print("  [seed] client profile")

    address = ClientAddress(
        id=ADDRESS_ID,
        client_id=CLIENT_ID,
        address_type="residential",
        line1="12 Marina Boulevard",
        line2="Unit 08-22",
        city="Singapore",
        state=None,
        postal_code="018982",
        country="Singapore",
        is_primary=True,
    )
    session.add(address)
    print("  [seed] client address")

    await session.commit()


if __name__ == "__main__":
    async def main() -> None:
        async with AsyncSessionLocal() as session:
            await seed(session)

    asyncio.run(main())
