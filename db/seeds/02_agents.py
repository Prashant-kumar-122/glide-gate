"""Seed: 8 CADF agents matching AgentID enum."""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.agents import Agent


AGENTS = [
    {
        "id": "b0000000-0001-0001-0001-000000000001",
        "agent_id": "orchestrator",
        "name": "Orchestrator Agent",
        "description": "Central workflow controller. Drives the onboarding FSM: INTAKE → KYC → PARALLEL_PRODUCTS → REVIEW → COMPLETE | ESCALATED.",
        "agent_type": "orchestrator",
        "is_active": True,
        "capabilities": ["workflow_control", "stage_transitions", "agent_routing", "escalation_management"],
        "llm_provider": None,
        "llm_model": None,
        "extra_metadata": {"brd_ref": "Section 6.1, FR-03"},
    },
    {
        "id": "b0000000-0002-0002-0002-000000000002",
        "agent_id": "customer_service",
        "name": "Customer Service Agent",
        "description": "Conversational front door for client data collection via dynamic questionnaire sequencing.",
        "agent_type": "conversational",
        "is_active": True,
        "capabilities": ["conversation_management", "data_collection", "intent_classification", "questionnaire_sequencing"],
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-6",
        "extra_metadata": {"brd_ref": "Section 8.1 stages 1–2, FR-02, FR-12"},
    },
    {
        "id": "b0000000-0003-0003-0003-000000000003",
        "agent_id": "kyc_compliance",
        "name": "KYC & Compliance Agent",
        "description": "Risk scoring (identity×0.4 + AML×0.4 + profile×0.2), evidence packet building, and checkpoint rule enforcement.",
        "agent_type": "compliance",
        "is_active": True,
        "capabilities": ["risk_scoring", "identity_verification", "aml_screening", "sanctions_check", "evidence_assembly"],
        "llm_provider": None,
        "llm_model": None,
        "extra_metadata": {"brd_ref": "FR-04, FR-13, FR-14, FR-15"},
    },
    {
        "id": "b0000000-0004-0004-0004-000000000004",
        "agent_id": "document_intelligence",
        "name": "Document Intelligence Agent",
        "description": "OCR extraction, AI completeness validation, version diff detection, and document classification.",
        "agent_type": "document_processing",
        "is_active": True,
        "capabilities": ["ocr_extraction", "document_classification", "ai_validation", "version_diff"],
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-6",
        "extra_metadata": {"brd_ref": "FR-06, FR-08, FR-09, Section 5.1.10–5.1.11"},
    },
    {
        "id": "b0000000-0005-0005-0005-000000000005",
        "agent_id": "product_onboarding",
        "name": "Product Onboarding Agent",
        "description": "Parameterised by product_code. Runs in parallel (one per product). Drives per-product step sequences with suitability assessment.",
        "agent_type": "product",
        "is_active": True,
        "capabilities": ["suitability_assessment", "account_setup", "product_step_execution"],
        "llm_provider": None,
        "llm_model": None,
        "extra_metadata": {"brd_ref": "FR-05, Section 8.1 stages 5–8"},
    },
    {
        "id": "b0000000-0006-0006-0006-000000000006",
        "agent_id": "collaboration",
        "name": "Collaboration Agent",
        "description": "Creates collaboration rooms, manages comments with role-based visibility, coordinates advisor/client/compliance interactions.",
        "agent_type": "collaboration",
        "is_active": True,
        "capabilities": ["room_management", "comment_threading", "visibility_control", "participant_management"],
        "llm_provider": None,
        "llm_model": None,
        "extra_metadata": {"brd_ref": "Section 7.4"},
    },
    {
        "id": "b0000000-0007-0007-0007-000000000007",
        "agent_id": "contact_centre",
        "name": "Contact Centre Agent",
        "description": "Generates AI-enhanced call summaries and provides real-time client status for contact centre representatives.",
        "agent_type": "contact_centre",
        "is_active": True,
        "capabilities": ["call_summarisation", "status_reporting", "recommended_actions"],
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-6",
        "extra_metadata": {"brd_ref": "Section 7.3, FR-05, Criterion #6"},
    },
    {
        "id": "b0000000-0008-0008-0008-000000000008",
        "agent_id": "notification",
        "name": "Notification Agent",
        "description": "Dispatches notifications (email, SMS, in-app) using 11 templates. Simulated dispatch with configurable latency.",
        "agent_type": "notification",
        "is_active": True,
        "capabilities": ["email_dispatch", "sms_dispatch", "in_app_notification", "template_rendering"],
        "llm_provider": None,
        "llm_model": None,
        "extra_metadata": {"brd_ref": "Section 8.1 stage 8"},
    },
]


async def seed(session: AsyncSession) -> None:
    for data in AGENTS:
        existing = await session.get(Agent, data["id"])
        if existing:
            print(f"  [skip] agent {data['agent_id']} already exists")
            continue
        agent = Agent(**data)
        session.add(agent)
        print(f"  [seed] agent {data['agent_id']}")
    await session.commit()


if __name__ == "__main__":
    async def main() -> None:
        async with AsyncSessionLocal() as session:
            await seed(session)

    asyncio.run(main())
