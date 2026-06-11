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
    from app.agents.kyc_compliance.checkpoint_rule_engine import CheckpointRuleEngine
    from app.agents.kyc_compliance.evidence_packet_builder import EvidencePacketBuilder
    from app.agents.kyc_compliance.risk_scorer import RiskScorer
    import app.services.compliance.checkpoint_rule_repository as rule_repo

    from uuid import UUID
    from app.agents.kyc_compliance.kyc_compliance_agent import KYCComplianceAgent

    agent = KYCComplianceAgent()
    client_data: dict[str, Any] = state.get("client_data", {})
    selected_products: list[str] = state.get("selected_products", [])
    case_id_str: str = state.get("case_id", "")
    case_id = UUID(case_id_str) if case_id_str else None

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
        client_id=None,
        client_data=client_data,
        verification_result=verification,
        risk_score=risk_score.model_dump(),
        checkpoint_decisions=[d.model_dump() for d in checkpoint.decisions],
    )

    authentic = verification.get("document_authentic", True)
    if checkpoint.should_escalate:
        kyc_status = "ESCALATED"
    elif not authentic:
        kyc_status = "FAILED"
    else:
        kyc_status = "PASSED"

    next_stage: str
    if kyc_status == "PASSED":
        next_stage = "PARALLEL_PRODUCTS"
    else:
        next_stage = "ESCALATED"

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
