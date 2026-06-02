"""Seed: 4 institutional trading products (Prime Brokerage, DVP, FCM, IBCash)."""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.cases import Product
from seed_constants import (
    DVP_PRODUCT_ID,
    FCM_PRODUCT_ID,
    IBCASH_PRODUCT_ID,
    PB_PRODUCT_ID,
)

PRODUCTS = [
    {
        "id": str(PB_PRODUCT_ID),
        "product_code": "prime_brokerage",
        "name": "Prime Brokerage",
        "description": "Full-service prime brokerage for institutional clients including securities lending, margin financing, custody and settlement, and capital introduction services.",
        "is_active": True,
        "product_type": "institutional",
        "required_documents": [
            "legal_entity_documentation",
            "regulatory_registration",
            "aml_kyc_documentation",
            "authorised_signatory_list",
        ],
        "suitability_criteria": {
            "client_type": "institutional",
            "min_aum_usd": 50_000_000,
        },
        "step_sequence": [
            {"step": "applicant_review", "name": "Applicant Information Review"},
            {"step": "regulatory_check", "name": "Regulatory Compliance Check"},
            {"step": "financial_assessment", "name": "Financial Profile Assessment"},
            {"step": "services_setup", "name": "Services Configuration"},
            {"step": "account_activation", "name": "Account Activation"},
        ],
        "metadata": {"product_type": "Prime Brokerage", "product_family": "institutional_trading"},
    },
    {
        "id": str(DVP_PRODUCT_ID),
        "product_code": "dvp",
        "name": "DVP (Delivery vs. Payment)",
        "description": "Delivery versus payment settlement service for institutional counterparties, supporting multi-currency settlement across major CSDs including DTC, Euroclear, and Clearstream.",
        "is_active": True,
        "product_type": "institutional",
        "required_documents": [
            "legal_entity_documentation",
            "regulatory_registration",
            "custodian_details",
            "settlement_instructions",
        ],
        "suitability_criteria": {
            "client_type": "institutional",
        },
        "step_sequence": [
            {"step": "applicant_review", "name": "Applicant Information Review"},
            {"step": "regulatory_check", "name": "Regulatory Compliance Check"},
            {"step": "custodian_setup", "name": "Custodian Details Setup"},
            {"step": "settlement_config", "name": "Settlement Instructions Configuration"},
            {"step": "account_activation", "name": "Account Activation"},
        ],
        "metadata": {"product_type": "DVP", "product_family": "institutional_trading"},
    },
    {
        "id": str(FCM_PRODUCT_ID),
        "product_code": "fcm",
        "name": "FCM (Futures Commission Merchant)",
        "description": "Futures commission merchant services for individuals and entities wishing to trade futures and derivatives on regulated exchanges under CFTC / NFA oversight.",
        "is_active": True,
        "product_type": "institutional",
        "required_documents": [
            "identity_documentation",
            "nfa_cftc_registration",
            "risk_disclosure_acknowledgement",
            "margin_agreement",
        ],
        "suitability_criteria": {
            "client_type": "institutional",
            "eligible_contract_participant": True,
        },
        "step_sequence": [
            {"step": "applicant_review", "name": "Applicant Information Review"},
            {"step": "regulatory_check", "name": "Regulatory Compliance Check"},
            {"step": "financial_assessment", "name": "Financial Profile Assessment"},
            {"step": "trading_setup", "name": "Trading Services Setup"},
            {"step": "account_activation", "name": "Account Activation"},
        ],
        "metadata": {"product_type": "FCM", "product_family": "institutional_trading"},
    },
    {
        "id": str(IBCASH_PRODUCT_ID),
        "product_code": "ibcash",
        "name": "IBCash",
        "description": "Cash account onboarding product for clients introduced by Introducing Brokers, covering full KYC/AML, suitability assessment, and account setup under the IB's regulatory umbrella.",
        "is_active": True,
        "product_type": "institutional",
        "required_documents": [
            "identity_documentation",
            "proof_of_address",
            "ib_client_agreement",
            "suitability_questionnaire",
        ],
        "suitability_criteria": {
            "client_type": "institutional",
            "introduced_via_ib": True,
        },
        "step_sequence": [
            {"step": "ib_verification", "name": "IB Verification"},
            {"step": "client_kyc", "name": "End-Client KYC"},
            {"step": "suitability_check", "name": "Suitability Assessment"},
            {"step": "account_setup", "name": "Account Setup"},
            {"step": "account_activation", "name": "Account Activation"},
        ],
        "metadata": {"product_type": "IBCash", "product_family": "institutional_trading"},
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
