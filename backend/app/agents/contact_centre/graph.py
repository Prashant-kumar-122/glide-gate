"""LangGraph StateGraph for the Contact Centre agent (Phase 0.5).

Wraps ContactCentreAgent logic for generating client status summaries.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict


async def _summarise_status_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Generate and store a current-status summary for contact centre agents."""
    from uuid import UUID

    from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType
    from app.agents.contact_centre.contact_centre_agent import ContactCentreAgent

    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")

    if not case_id_str:
        return state

    agent = ContactCentreAgent()

    task_type = TaskType.GET_CLIENT_STATUS
    payload: dict[str, Any] = {
        "onboarding_state": {"stage": state.get("stage", "")},
        "client_data": state.get("client_data", {}),
    }
    # Use SUMMARISE_CALL on escalation
    if state.get("escalation_reason"):
        task_type = TaskType.SUMMARISE_CALL
        payload["onboarding_state"]["escalation_reason"] = state.get("escalation_reason")

    packet = TaskPacket(
        from_agent=AgentID.ORCHESTRATOR,
        to_agent=AgentID.CONTACT_CENTRE,
        task_type=task_type,
        case_id=UUID(case_id_str),
        client_id=UUID(client_id_str),
        priority="LOW",
        payload=payload,
    )
    await agent.process(packet)
    return state


def build_contact_centre_graph() -> Any:
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("summarise_status", _summarise_status_node)
    graph.add_edge("summarise_status", END)
    graph.set_entry_point("summarise_status")
    return graph.compile()
