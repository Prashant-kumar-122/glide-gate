"""LangGraph StateGraph for the KYC Compliance agent (Phase 0.5 / Phase 6).

Phase 6 change: _simulate_identity_verification() replaced by three
mcp_registry.invoke() calls (verify_identity, check_sanctions, score_aml_risk).
The EscalationSkill is wired via domain_agent_skills DB binding — it enriches
the checkpoint result with LLM-based reasoning but never overrides the
deterministic CheckpointRuleEngine decision for kyc_status routing.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict
from app.agents.kyc_compliance.verification_translation import (
    build_verification_dict as _build_verification_dict,
    parse_income as _parse_income,
)


async def _run_kyc_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Identity verification via MCP, risk scoring, checkpoint evaluation, and
    optional EscalationSkill enrichment from domain_agent_skills binding.
    """
    import time
    from uuid import UUID

    from loguru import logger

    from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType, TaskResponse
    from app.agents.kyc_compliance.checkpoint_rule_engine import CheckpointRuleEngine
    from app.agents.kyc_compliance.evidence_packet_builder import EvidencePacketBuilder
    from app.agents.kyc_compliance.kyc_compliance_agent import KYCComplianceAgent
    from app.agents.kyc_compliance.risk_scorer import RiskScorer
    import app.services.compliance.checkpoint_rule_repository as rule_repo
    from app.mcp.mcp_connector import mcp_registry
    from app.services.skills.skill_dispatcher import skill_dispatcher

    agent = KYCComplianceAgent()
    client_data: dict[str, Any] = state.get("client_data", {})
    selected_products: list[str] = state.get("selected_products", [])
    case_id_str: str = state.get("case_id", "")
    client_id_str: str = state.get("client_id", "")
    case_id = UUID(case_id_str) if case_id_str else None
    client_id = UUID(client_id_str) if client_id_str else None

    first = client_data.get("first_name", "")
    last = client_data.get("last_name", "")
    full_name: str = (
        client_data.get("full_name")
        or (f"{first} {last}".strip())
        or client_data.get("full_name_signature", "")
    )
    nationality: str = (
        client_data.get("country_of_citizenship")
        or client_data.get("nationality")
        or ""
    )

    start = time.monotonic()

    # ── MCP: identity verification, sanctions screening, AML scoring ──────────
    verify_result: dict[str, Any] = await mcp_registry.invoke(
        "identity_verification",
        "verify_identity",
        {
            "full_name": full_name,
            "document_type": (
                client_data.get("document_type")
                or client_data.get("id_type", "PASSPORT")
            ),
            "document_number": (
                client_data.get("document_number")
                or client_data.get("id_number", "")
            ),
            "nationality": nationality,
            "document_expiry": (
                client_data.get("document_expiry")
                or client_data.get("id_expiration_date", "2099-12-31")
            ),
        },
        case_id=case_id,
        agent_id="kyc_compliance",
    )

    sanctions_result: dict[str, Any] = await mcp_registry.invoke(
        "identity_verification",
        "check_sanctions",
        {
            "full_name": full_name,
            "nationality": nationality,
        },
        case_id=case_id,
        agent_id="kyc_compliance",
    )

    aml_result: dict[str, Any] = await mcp_registry.invoke(
        "identity_verification",
        "score_aml_risk",
        {
            "full_name": full_name,
            "nationality": nationality,
            "country_of_residence": client_data.get("country_of_residence", ""),
            "occupation": client_data.get("occupation", ""),
            "annual_income": _parse_income(client_data.get("annual_income", 0)),
            "source_of_wealth": client_data.get("source_of_funds", ""),
            "pep_status": bool(
                client_data.get("pep_status")
                or client_data.get("is_senior_political_figure") == "Yes"
            ),
        },
        case_id=case_id,
        agent_id="kyc_compliance",
    )

    verification = _build_verification_dict(
        verify_result, sanctions_result, aml_result, client_data
    )

    # ── Risk scoring and checkpoint evaluation ────────────────────────────────
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

    # ── EscalationSkill enrichment (via domain_agent_skills binding) ──────────
    # The skill result is advisory metadata — it does NOT override the
    # deterministic CheckpointRuleEngine decision for kyc_status routing.
    escalation_enrichment: dict[str, Any] | None = None
    try:
        bound = await skill_dispatcher.get_binding("kyc_compliance", "escalation")
        if bound is not None:
            escalation_enrichment = await skill_dispatcher.invoke_skill(
                "escalation",
                agent_id="kyc_compliance",
                risk_score=risk_score.composite_score / 100.0,
                risk_band=risk_score.risk_band,
                kyc_flags=checkpoint.escalation_reasons,
            )
    except Exception as exc:
        logger.warning(f"EscalationSkill enrichment failed (non-fatal): {exc}")

    # ── Determine final kyc_status from deterministic rules ───────────────────
    authentic = verification.get("document_authentic", True)
    if checkpoint.should_escalate:
        kyc_status = "ESCALATED"
    elif not authentic:
        kyc_status = "FAILED"
    else:
        kyc_status = "PASSED"

    next_stage: str = "PARALLEL_PRODUCTS" if kyc_status == "PASSED" else "ESCALATED"

    # ── Persist AgentTask (trace canvas visibility) ───────────────────────────
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

    extra = {
        **(state.get("extra") or {}),
        "kyc_status": kyc_status,
        "kyc_risk_score": float(risk_score.composite_score),
    }
    if escalation_enrichment:
        extra["kyc_escalation_enrichment"] = escalation_enrichment

    return {
        **state,
        "extra": extra,
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
