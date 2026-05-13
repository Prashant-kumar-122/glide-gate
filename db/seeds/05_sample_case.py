"""Seed: Sample onboarding case for Aarav Mehta — 2 products (cash + retirement)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.cases import CaseProduct, CaseProductStep, OnboardingCase
from app.models.questionnaire import OnboardingAnswer, OnboardingQuestionSession

import importlib.util, sys
from pathlib import Path

_sc = importlib.util.spec_from_file_location("seed_constants", Path(__file__).parent / "seed_constants.py")
_m = importlib.util.module_from_spec(_sc); _sc.loader.exec_module(_m)  # type: ignore
CASH_PRODUCT_ID = _m.CASH_PRODUCT_ID
CLIENT_ID = _m.CLIENT_ID
QUESTIONNAIRE_ID = _m.QUESTIONNAIRE_ID
RETIREMENT_PRODUCT_ID = _m.RETIREMENT_PRODUCT_ID

CASE_ID = UUID("e0000000-0001-0001-0001-000000000001")
CASE_PRODUCT_CASH_ID = UUID("e0000000-0002-0002-0002-000000000002")
CASE_PRODUCT_RETIREMENT_ID = UUID("e0000000-0003-0003-0003-000000000003")
QUESTION_SESSION_ID = UUID("e0000000-0004-0004-0004-000000000004")


async def seed(session: AsyncSession) -> None:
    existing = await session.get(OnboardingCase, CASE_ID)
    if existing:
        print("  [skip] sample case already exists")
        return

    now = datetime.utcnow()
    sla = now + timedelta(days=3)

    case = OnboardingCase(
        id=CASE_ID,
        client_id=CLIENT_ID,
        status="INTAKE",
        current_stage="INTAKE",
        selected_products=["cash_account", "retirement_account"],
        shared_context={
            "case_id": str(CASE_ID),
            "client_id": str(CLIENT_ID),
            "stage": "INTAKE",
            "selected_products": ["cash_account", "retirement_account"],
            "product_tracks": {},
            "client_data": {},
            "documents_required": [],
            "documents_received": [],
            "kyc_status": "PENDING",
            "kyc_risk_score": None,
            "version": 0,
        },
        assigned_advisor_id=UUID("f0000000-0001-0001-0001-000000000001"),
        sla_deadline=sla,
        metadata={"demo_case": True, "scenario": "scenario_a"},
    )
    session.add(case)
    print(f"  [seed] onboarding case {CASE_ID}")

    # Cash Account product track
    cp_cash = CaseProduct(
        id=CASE_PRODUCT_CASH_ID,
        case_id=CASE_ID,
        product_id=CASH_PRODUCT_ID,
        product_code="cash_account",
        status="PENDING",
        suitability_outcome={},
        metadata={},
    )
    session.add(cp_cash)
    print("  [seed] case_product cash_account")

    for i, step_name in enumerate(["suitability_check", "account_setup", "kyc_link", "account_activation", "welcome_notification"]):
        session.add(CaseProductStep(
            case_product_id=CASE_PRODUCT_CASH_ID,
            step_name=step_name,
            step_index=i,
            status="PENDING",
        ))

    # Retirement Account product track
    cp_retirement = CaseProduct(
        id=CASE_PRODUCT_RETIREMENT_ID,
        case_id=CASE_ID,
        product_id=RETIREMENT_PRODUCT_ID,
        product_code="retirement_account",
        status="PENDING",
        suitability_outcome={},
        metadata={},
    )
    session.add(cp_retirement)
    print("  [seed] case_product retirement_account")

    for i, step_name in enumerate(["suitability_check", "retirement_profile", "investment_selection", "contribution_setup", "beneficiary_nomination", "account_activation", "welcome_notification"]):
        session.add(CaseProductStep(
            case_product_id=CASE_PRODUCT_RETIREMENT_ID,
            step_name=step_name,
            step_index=i,
            status="PENDING",
        ))

    # Questionnaire session (IN_PROGRESS — captures the paused-journey resumption scenario)
    session.add(OnboardingQuestionSession(
        id=QUESTION_SESSION_ID,
        case_id=CASE_ID,
        client_id=CLIENT_ID,
        questionnaire_id=QUESTIONNAIRE_ID,
        status="IN_PROGRESS",
        current_section="personal_information",
        current_question_index=0,
        completed_sections=[],
        session_data={},
    ))
    print("  [seed] questionnaire session")

    await session.commit()


if __name__ == "__main__":
    async def main() -> None:
        async with AsyncSessionLocal() as session:
            await seed(session)

    asyncio.run(main())
