"""LangGraph StateGraph for the Customer Service agent (Phase 0.5).

The kickoff node initialises the data-collection conversation in the DB and
emits the initial WebSocket event. The actual multi-turn conversation continues
via the REST API; when data collection is complete the CustomerServiceAgent
signals the OnboardingWorkflow via advance_stage.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict


async def _kickoff_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Persist the initial conversation context and emit INTAKE_STARTED event."""
    from uuid import UUID

    from app.database import AsyncSessionLocal
    from app.websocket.socket_emitter import socket_emitter

    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")
    selected_products = state.get("selected_products", [])

    if case_id_str:
        case_id = UUID(case_id_str)
        await socket_emitter.case_stage_changed(
            case_id,
            {
                "case_id": case_id_str,
                "stage": "INTAKE",
                "event": "INTAKE_STARTED",
                "selected_products": selected_products,
            },
        )

    return {**state, "next_stage": None}


def build_customer_service_kickoff_graph() -> Any:
    """Return a compiled LangGraph graph for the CustomerService kickoff."""
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("kickoff", _kickoff_node)
    graph.add_edge("kickoff", END)
    graph.set_entry_point("kickoff")
    return graph.compile()
