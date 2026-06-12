"""LangGraph StateGraph for the KYC Compliance agent (Phase 0.5).

Each node wraps existing KYCComplianceAgent logic unchanged. The graph runs
end-to-end as a Temporal Activity and returns the updated OnboardingStateDict.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict


async def _run_kyc_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Identity verification, risk scoring, and checkpoint evaluation."""
    import time
    from app.agents.kyc_compliance.checkpoint_rule_engine import CheckpointRuleEngine
    from app.agents.kyc_compliance.evidence_packet_builder import EvidencePacketBuilder
    from app.agents.kyc_compliance.risk_scorer import RiskScorer
    import app.services.compliance.checkpoint_rule_repository as rule_repo

    from uuid import UUID
    from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType, TaskResponse
    from app.agents.kyc_compliance.kyc_compliance_agent import KYCComplianceAgent

    agent = KYCComplianceAgent()
    client_data: dict[str, Any] = state.get("client_data", {})
    selected_products: list[str] = state.get("selected_products", [])
    case_id_str: str = state.get("case_id", "")
    client_id_str: str = state.get("client_id", "")
    case_id = UUID(case_id_str) if case_id_str else None
    client_id = UUID(client_id_str) if client_id_str else None

    start = time.monotonic()
    verification = await agent._simulate_identity_verification(client_data, case_id=case_id)
    risk_score = RiskScorer().compute(client_data, verification)
    checkpoint = CheckpointRuleEngine(rules=rule_repo.get_all()).evaluate(
        risk_score=risk_score.model_dump(),
        client_data=client_data,
        verification_result=verification,
        selected_products=selected_products,
    )
    evidence = EvidencePacketBuilder().build(
        case_id=case_id,
        client_id=client_id,
        client_data=client_data,
        verification_result=verification,
        risk_score=risk_score.model_dump(),
        checkpoint_decisions=[d.model_dump() for d in checkpoint.decisions],
    )
    duration_ms = int((time.monotonic() - start) * 1000)

    authentic = verification.get("document_authentic", True)
    if checkpoint.should_escalate:
        kyc_status = "ESCALATED"
    elif not authentic:
        kyc_status = "FAILED"
    else:
        kyc_status = "PASSED"

    next_stage: str = "PARALLEL_PRODUCTS" if kyc_status == "PASSED" else "ESCALATED"

    # Persist AgentTask so the KYC agent appears in the trace canvas.
    if case_id and client_id:
        task_packet = TaskPacket(
            from_agent=AgentID.ORCHESTRATOR,
            to_agent=AgentID.KYC_COMPLIANCE,
            task_type=TaskType.RUN_KYC_CHECK,
            case_id=case_id,
            client_id=client_id,
            priority="HIGH",
            payload={"selected_products": selected_products},
        )
        response = TaskResponse(
            task_id=task_packet.id,
            from_agent=AgentID.KYC_COMPLIANCE,
            status="SUCCESS" if kyc_status in ("PASSED", "ESCALATED") else "FAILED",
            result={"kyc_status": kyc_status, "risk_band": risk_score.risk_band},
            duration_ms=duration_ms,
        )
        await agent._persist_agent_task(task_packet, response, duration_ms)

    return {
        **state,
        "kyc_status": kyc_status,
        "kyc_risk_score": float(risk_score.composite_score),
        "next_stage": next_stage,
        "_kyc_evidence_packet_id": str(evidence.packet_id),
        "_kyc_escalation_reasons": checkpoint.escalation_reasons,
        "_kyc_required_documents": checkpoint.required_documents,
        "_kyc_risk_band": risk_score.risk_band,
    }


def build_kyc_graph() -> Any:
    """Return a compiled LangGraph StateGraph for KYC compliance."""
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("run_kyc", _run_kyc_node)
    graph.add_edge("run_kyc", END)
    graph.set_entry_point("run_kyc")
    return graph.compile()
