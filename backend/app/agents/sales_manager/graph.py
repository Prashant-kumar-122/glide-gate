"""LangGraph StateGraph for the Sales Manager agent (Phase 0.5).

Kickoff node: persists the sales review request record and emits the
SALES_REVIEW WebSocket event so the sales manager's dashboard updates.
The human decision arrives later via OnboardingWorkflow.human_review_completed.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict


async def _sales_review_kickoff_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Create a SalesManagerReview record and notify via WebSocket."""
    from uuid import UUID

    from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType
    from app.agents.sales_manager.sales_manager_agent import SalesManagerAgent

    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")

    if not case_id_str:
        return state

    agent = SalesManagerAgent()
    agent._bus = None

    packet = TaskPacket(
        from_agent=AgentID.ORCHESTRATOR,
        to_agent=AgentID.SALES_MANAGER,
        task_type=TaskType.SALES_MANAGER_REVIEW,
        case_id=UUID(case_id_str),
        client_id=UUID(client_id_str),
        priority="HIGH",
        payload={
            "selected_products": state.get("selected_products", []),
            "client_data": state.get("client_data", {}),
        },
    )
    await agent.process(packet)
    return state


def build_sales_manager_kickoff_graph() -> Any:
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("sales_review_kickoff", _sales_review_kickoff_node)
    graph.add_edge("sales_review_kickoff", END)
    graph.set_entry_point("sales_review_kickoff")
    return graph.compile()
