"""Seed: 2 products — Cash Account and Retirement Account."""
from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.cases import Product


PRODUCTS = [
    {
        "id": "a1b2c3d4-0001-0001-0001-000000000001",
        "product_code": "cash_account",
        "name": "Cash Management Account",
        "description": "A flexible cash account for managing day-to-day wealth with competitive interest rates.",
        "is_active": True,
        "required_documents": [
            "passport_or_id",
            "proof_of_address",
            "source_of_funds",
        ],
        "suitability_criteria": {
            "min_age": 18,
            "min_annual_income": 0,
            "risk_appetite": ["conservative", "moderate", "aggressive"],
            "investment_experience": ["none", "limited", "moderate", "extensive"],
        },
        "step_sequence": [
            {"step": "suitability_check", "name": "Suitability Assessment"},
            {"step": "account_setup", "name": "Account Configuration"},
            {"step": "kyc_link", "name": "KYC Linkage"},
            {"step": "account_activation", "name": "Account Activation"},
            {"step": "welcome_notification", "name": "Welcome Communication"},
        ],
        "metadata": {"product_family": "banking", "regulatory_category": "deposit"},
    },
    {
        "id": "a1b2c3d4-0002-0002-0002-000000000002",
        "product_code": "retirement_account",
        "name": "Retirement Savings Plan",
        "description": "A long-term retirement savings account with tax-advantaged growth and investment options.",
        "is_active": True,
        "required_documents": [
            "passport_or_id",
            "proof_of_address",
            "source_of_funds",
            "employment_contract",
            "tax_declaration",
        ],
        "suitability_criteria": {
            "min_age": 21,
            "max_age": 65,
            "min_annual_income": 30000,
            "risk_appetite": ["moderate", "aggressive"],
            "investment_experience": ["limited", "moderate", "extensive"],
            "investment_horizon": ["long"],
        },
        "step_sequence": [
            {"step": "suitability_check", "name": "Suitability Assessment"},
            {"step": "retirement_profile", "name": "Retirement Goal Setup"},
            {"step": "investment_selection", "name": "Investment Option Selection"},
            {"step": "contribution_setup", "name": "Contribution Schedule"},
            {"step": "beneficiary_nomination", "name": "Beneficiary Nomination"},
            {"step": "account_activation", "name": "Account Activation"},
            {"step": "welcome_notification", "name": "Welcome Communication"},
        ],
        "metadata": {"product_family": "retirement", "regulatory_category": "pension"},
    },
]


async def seed(session: AsyncSession) -> None:
    for data in PRODUCTS:
        existing = await session.get(Product, data["id"])
        if existing:
            print(f"  [skip] product {data['product_code']} already exists")
            continue
        product = Product(**data)
        session.add(product)
        print(f"  [seed] product {data['product_code']}")
    await session.commit()


if __name__ == "__main__":
    async def main() -> None:
        async with AsyncSessionLocal() as session:
            await seed(session)

    asyncio.run(main())
