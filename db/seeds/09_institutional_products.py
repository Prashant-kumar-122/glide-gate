"""Seed: 4 institutional trading products (GCF, ECM, DCM, TFE)."""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.cases import Product
from seed_constants import (
    DCM_PRODUCT_ID,
    DVP_PRODUCT_ID,
    ECM_PRODUCT_ID,
    FCM_PRODUCT_ID,
    GCF_PRODUCT_ID,
    IBCASH_PRODUCT_ID,
    PB_PRODUCT_ID,
    TFE_PRODUCT_ID,
)

PRODUCTS = [
    {
        "id": str(GCF_PRODUCT_ID),
        "product_code": "GCF",
        "name": "Global Custody Facility",
        "description": "Institutional global custody and settlement services.",
        "is_active": True,
        "product_type": "institutional",
        "required_documents": [
            "legal_entity_documentation",
            "regulatory_registration",
            "custodian_details",
            "aml_kyc_documentation",
        ],
        "suitability_criteria": {
            "client_type": "institutional",
        },
        "step_sequence": [
            {"step": "applicant_review", "name": "Applicant Information Review"},
            {"step": "regulatory_check", "name": "Regulatory Compliance Check"},
            {"step": "financial_assessment", "name": "Financial Profile Assessment"},
            {"step": "custodian_setup", "name": "Custodian Details Setup"},
            {"step": "account_activation", "name": "Account Activation"},
        ],
        "metadata": {"product_type": "GCF", "product_family": "institutional_trading"},
    },
    {
        "id": str(ECM_PRODUCT_ID),
        "product_code": "ECM",
        "name": "Equity Capital Markets",
        "description": "Equity capital markets access for institutional clients.",
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
        "metadata": {"product_type": "ECM", "product_family": "institutional_trading"},
    },
    {
        "id": str(DCM_PRODUCT_ID),
        "product_code": "DCM",
        "name": "Debt Capital Markets",
        "description": "Debt capital markets services for institutional issuers.",
        "is_active": True,
        "product_type": "institutional",
        "required_documents": [
            "legal_entity_documentation",
            "regulatory_registration",
            "aml_kyc_documentation",
            "authorised_contacts",
        ],
        "suitability_criteria": {
            "client_type": "institutional",
        },
        "step_sequence": [
            {"step": "applicant_review", "name": "Applicant Information Review"},
            {"step": "regulatory_check", "name": "Regulatory Compliance Check"},
            {"step": "financial_assessment", "name": "Financial Profile Assessment"},
            {"step": "authorised_contacts", "name": "Authorised Contacts"},
            {"step": "account_activation", "name": "Account Activation"},
        ],
        "metadata": {"product_type": "DCM", "product_family": "institutional_trading"},
    },
    {
        "id": str(TFE_PRODUCT_ID),
        "product_code": "TFE",
        "name": "Trade Finance Exchange",
        "description": "Trade finance exchange platform for institutional participants.",
        "is_active": True,
        "product_type": "institutional",
        "required_documents": [
            "legal_entity_documentation",
            "regulatory_registration",
            "aml_kyc_documentation",
        ],
        "suitability_criteria": {
            "client_type": "institutional",
        },
        "step_sequence": [
            {"step": "applicant_review", "name": "Applicant Information Review"},
            {"step": "regulatory_check", "name": "Regulatory Compliance Check"},
            {"step": "financial_assessment", "name": "Financial Profile Assessment"},
            {"step": "services_setup", "name": "Services Configuration"},
            {"step": "account_activation", "name": "Account Activation"},
        ],
        "metadata": {"product_type": "TFE", "product_family": "institutional_trading"},
    },
    # Legacy products — inactive, retained for questionnaire FK references
    {
        "id": str(PB_PRODUCT_ID),
        "product_code": "PB",
        "name": "Prime Brokerage",
        "description": "Prime brokerage services for institutional hedge funds and asset managers.",
        "is_active": False,
        "product_type": "institutional",
        "required_documents": [
            "legal_entity_documentation",
            "regulatory_registration",
            "aml_kyc_documentation",
            "authorised_signatory_list",
        ],
        "suitability_criteria": {"client_type": "institutional"},
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
        "product_code": "DVP",
        "name": "DVP Settlement",
        "description": "Delivery-versus-payment settlement services for institutional clients.",
        "is_active": False,
        "product_type": "institutional",
        "required_documents": [
            "legal_entity_documentation",
            "regulatory_registration",
            "aml_kyc_documentation",
        ],
        "suitability_criteria": {"client_type": "institutional"},
        "step_sequence": [
            {"step": "applicant_review", "name": "Applicant Information Review"},
            {"step": "regulatory_check", "name": "Regulatory Compliance Check"},
            {"step": "custodian_setup", "name": "Custodian Details Setup"},
            {"step": "account_activation", "name": "Account Activation"},
        ],
        "metadata": {"product_type": "DVP", "product_family": "institutional_trading"},
    },
    {
        "id": str(FCM_PRODUCT_ID),
        "product_code": "FCM",
        "name": "FCM Futures",
        "description": "Futures commission merchant clearing services for institutional clients.",
        "is_active": False,
        "product_type": "institutional",
        "required_documents": [
            "legal_entity_documentation",
            "regulatory_registration",
            "aml_kyc_documentation",
        ],
        "suitability_criteria": {"client_type": "institutional"},
        "step_sequence": [
            {"step": "applicant_review", "name": "Applicant Information Review"},
            {"step": "regulatory_check", "name": "Regulatory Compliance Check"},
            {"step": "financial_assessment", "name": "Financial Profile Assessment"},
            {"step": "account_activation", "name": "Account Activation"},
        ],
        "metadata": {"product_type": "FCM", "product_family": "institutional_trading"},
    },
    {
        "id": str(IBCASH_PRODUCT_ID),
        "product_code": "IBCash",
        "name": "IB-Introduced Cash Account",
        "description": "Cash account for clients introduced through introducing brokers.",
        "is_active": False,
        "product_type": "institutional",
        "required_documents": [
            "legal_entity_documentation",
            "aml_kyc_documentation",
        ],
        "suitability_criteria": {"client_type": "institutional"},
        "step_sequence": [
            {"step": "applicant_review", "name": "Applicant Information Review"},
            {"step": "regulatory_check", "name": "Regulatory Compliance Check"},
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
