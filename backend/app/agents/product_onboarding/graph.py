"""LangGraph StateGraph for the Product Onboarding agent (Phase 0.5).

Wraps the existing ProductOnboardingAgent._handle_onboard_product logic.
One graph instance runs per product track (dispatched as child workflows).
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict


async def _onboard_product_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Run the full product onboarding pipeline for one product."""
    from uuid import UUID

    from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType
    from app.agents.product_onboarding.product_onboarding_agent import ProductOnboardingAgent

    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")
    product_code: str = state.get("_product_code", "")

    if not case_id_str or not product_code:
        return {**state, "_product_track_status": "FAILED", "next_stage": None}

    agent = ProductOnboardingAgent()

    packet = TaskPacket(
        from_agent=AgentID.ORCHESTRATOR,
        to_agent=AgentID.PRODUCT_ONBOARDING,
        task_type=TaskType.ONBOARD_PRODUCT,
        case_id=UUID(case_id_str),
        client_id=UUID(client_id_str),
        priority="NORMAL",
        payload={
            "product_code": product_code,
            "selected_products": state.get("selected_products", []),
            "client_data": state.get("client_data", {}),
        },
    )
    response = await agent.timed_process(packet)

    track_status = "COMPLETE" if response.status == "SUCCESS" else response.result.get(
        "track_status", "FAILED"
    )

    tracks = dict(state.get("product_tracks") or {})
    tracks[product_code] = {
        "product_code": product_code,
        "stage": track_status,
        "step": response.result.get("steps_completed", 0),
        "total_steps": response.result.get("total_steps", 0),
    }

    return {**state, "product_tracks": tracks, "_product_track_status": track_status}


def build_product_onboarding_graph() -> Any:
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("onboard_product", _onboard_product_node)
    graph.add_edge("onboard_product", END)
    graph.set_entry_point("onboard_product")
    return graph.compile()
