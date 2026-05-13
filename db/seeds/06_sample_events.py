"""Seed: Event log entries covering the full onboarding journey for Aarav Mehta.

Simulates the audit trail for demo scenario A (happy path).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.agents import EventLog

import importlib.util
from pathlib import Path

_sc = importlib.util.spec_from_file_location("seed_constants", Path(__file__).parent / "seed_constants.py")
_m = importlib.util.module_from_spec(_sc); _sc.loader.exec_module(_m)  # type: ignore
CASE_ID = _m.CASE_ID
CLIENT_ID = _m.CLIENT_ID

# Advisor UUID used in event logs
ADVISOR_ID = "f0000000-0001-0001-0001-000000000001"


def _event(
    event_type: str,
    event_category: str,
    agent_id: str | None,
    actor_id: str,
    actor_role: str,
    payload: dict,
    entity_type: str | None = None,
    entity_id=None,
    is_compliance: bool = False,
    offset_minutes: int = 0,
) -> EventLog:
    return EventLog(
        id=uuid4(),
        case_id=CASE_ID,
        client_id=CLIENT_ID,
        agent_id=agent_id,
        event_type=event_type,
        event_category=event_category,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        actor_role=actor_role,
        payload=payload,
        is_compliance_event=is_compliance,
        created_at=datetime.utcnow() - timedelta(minutes=60 - offset_minutes),
    )


EVENTS = [
    # Case initiated
    _event("CASE_INITIATED", "AGENT_ACTION", "orchestrator", ADVISOR_ID, "Advisor",
           {"stage": "INTAKE", "products": ["cash_account", "retirement_account"]}, "case", CASE_ID, offset_minutes=0),
    # Customer service starts data collection
    _event("DATA_COLLECTION_STARTED", "AGENT_ACTION", "customer_service", "customer_service", "system",
           {"section": "personal_information"}, "case", CASE_ID, offset_minutes=1),
    # Several answers collected
    _event("DATA_COLLECTED", "AGENT_ACTION", "customer_service", "customer_service", "system",
           {"fields_completed": 10, "total_fields": 30}, "case", CASE_ID, offset_minutes=5),
    # Data collection complete
    _event("DATA_COLLECTION_COMPLETE", "AGENT_ACTION", "customer_service", "customer_service", "system",
           {"fields_completed": 30, "total_fields": 30}, "case", CASE_ID, offset_minutes=12),
    # Stage advanced to KYC
    _event("STAGE_ADVANCED", "AGENT_ACTION", "orchestrator", "orchestrator", "system",
           {"from_stage": "INTAKE", "to_stage": "KYC"}, "case", CASE_ID, offset_minutes=12),
    # KYC check started
    _event("KYC_CHECK_STARTED", "KYC", "kyc_compliance", "kyc_compliance", "system",
           {"client_id": str(CLIENT_ID)}, "case", CASE_ID, is_compliance=True, offset_minutes=13),
    # Identity verification MCP call
    _event("MCP_TOOL_CALLED", "AGENT_ACTION", "kyc_compliance", "kyc_compliance", "system",
           {"connector": "identity_verification", "tool": "verify_identity", "is_simulated": True}, offset_minutes=14),
    # AML screening MCP call
    _event("MCP_TOOL_CALLED", "AGENT_ACTION", "kyc_compliance", "kyc_compliance", "system",
           {"connector": "identity_verification", "tool": "check_sanctions", "is_simulated": True}, offset_minutes=15),
    # Risk score computed — LOW risk (happy path)
    _event("KYC_RISK_SCORED", "KYC", "kyc_compliance", "kyc_compliance", "system",
           {"identity_score": 0.92, "aml_score": 0.95, "profile_score": 0.88, "composite_score": 0.923, "risk_band": "LOW"},
           "case", CASE_ID, is_compliance=True, offset_minutes=16),
    # KYC passed
    _event("KYC_PASSED", "KYC", "kyc_compliance", "kyc_compliance", "system",
           {"status": "PASSED", "risk_band": "LOW"}, "case", CASE_ID, is_compliance=True, offset_minutes=17),
    # Stage advanced to PARALLEL_PRODUCTS
    _event("STAGE_ADVANCED", "AGENT_ACTION", "orchestrator", "orchestrator", "system",
           {"from_stage": "KYC", "to_stage": "PARALLEL_PRODUCTS"}, "case", CASE_ID, offset_minutes=17),
    # Product onboarding started — cash
    _event("PRODUCT_ONBOARDING_STARTED", "AGENT_ACTION", "product_onboarding", "product_onboarding", "system",
           {"product_code": "cash_account"}, "case", CASE_ID, offset_minutes=18),
    # Product onboarding started — retirement
    _event("PRODUCT_ONBOARDING_STARTED", "AGENT_ACTION", "product_onboarding", "product_onboarding", "system",
           {"product_code": "retirement_account"}, "case", CASE_ID, offset_minutes=18),
    # Document uploaded
    _event("DOCUMENT_UPLOADED", "DOCUMENT", "document_intelligence", str(CLIENT_ID), "Client",
           {"document_type": "passport", "category": "identity", "filename": "aarav_passport.pdf"},
           "document", None, offset_minutes=20),
    # AI validation triggered
    _event("DOCUMENT_VALIDATION_STARTED", "DOCUMENT", "document_intelligence", "document_intelligence", "system",
           {"document_type": "passport", "prompt_version": "1.0"}, "document", None, offset_minutes=21),
    # AI validation result
    _event("DOCUMENT_VALIDATED", "DOCUMENT", "document_intelligence", "document_intelligence", "system",
           {"status": "APPROVED", "findings": [{"type": "pass", "message": "All required fields present"}]},
           "document", None, offset_minutes=23),
    # Cash account suitability passed
    _event("SUITABILITY_ASSESSED", "AGENT_ACTION", "product_onboarding", "product_onboarding", "system",
           {"product_code": "cash_account", "outcome": "SUITABLE", "score": 0.87}, "case", CASE_ID, offset_minutes=25),
    # Retirement suitability passed
    _event("SUITABILITY_ASSESSED", "AGENT_ACTION", "product_onboarding", "product_onboarding", "system",
           {"product_code": "retirement_account", "outcome": "SUITABLE", "score": 0.79}, "case", CASE_ID, offset_minutes=26),
    # Cash account activated
    _event("PRODUCT_ONBOARDING_COMPLETE", "AGENT_ACTION", "product_onboarding", "product_onboarding", "system",
           {"product_code": "cash_account", "account_number": "CA-2026-001001"}, "case", CASE_ID, offset_minutes=30),
    # Retirement account activated
    _event("PRODUCT_ONBOARDING_COMPLETE", "AGENT_ACTION", "product_onboarding", "product_onboarding", "system",
           {"product_code": "retirement_account", "account_number": "RA-2026-001001"}, "case", CASE_ID, offset_minutes=35),
    # Notification sent
    _event("NOTIFICATION_SENT", "NOTIFICATION", "notification", "notification", "system",
           {"template": "onboarding_complete", "channel": "email", "is_simulated": True}, "case", CASE_ID, offset_minutes=36),
    # Stage advanced to COMPLETE
    _event("STAGE_ADVANCED", "AGENT_ACTION", "orchestrator", "orchestrator", "system",
           {"from_stage": "PARALLEL_PRODUCTS", "to_stage": "COMPLETE"}, "case", CASE_ID, offset_minutes=36),
    # Case completed
    _event("CASE_COMPLETED", "AGENT_ACTION", "orchestrator", "orchestrator", "system",
           {"duration_minutes": 36, "products_onboarded": ["cash_account", "retirement_account"]},
           "case", CASE_ID, is_compliance=True, offset_minutes=36),
]


async def seed(session: AsyncSession) -> None:
    session.add_all(EVENTS)
    await session.commit()
    print(f"  [seed] {len(EVENTS)} event log entries")


if __name__ == "__main__":
    async def main() -> None:
        async with AsyncSessionLocal() as session:
            await seed(session)

    asyncio.run(main())
