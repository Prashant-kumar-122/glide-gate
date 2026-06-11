"""LangGraph StateGraph for the Collaboration agent (Phase 0.5).

Wraps CollaborationAgent.CREATE_COLLABORATION_ROOM to create the advisor
collaboration room when a case enters the REVIEW stage.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict


async def _create_collaboration_room_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Create an advisor collaboration room for human review."""
    from uuid import UUID

    from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType
    from app.agents.collaboration.collaboration_agent import CollaborationAgent

    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")

    if not case_id_str:
        return state

    agent = CollaborationAgent()
    agent._bus = None

    packet = TaskPacket(
        from_agent=AgentID.ORCHESTRATOR,
        to_agent=AgentID.COLLABORATION,
        task_type=TaskType.CREATE_COLLABORATION_ROOM,
        case_id=UUID(case_id_str),
        client_id=UUID(client_id_str),
        priority="NORMAL",
        payload={
            "selected_products": state.get("selected_products", []),
            "client_data": state.get("client_data", {}),
            "product_tracks": state.get("product_tracks", {}),
        },
    )
    await agent.process(packet)
    return state


def build_collaboration_graph() -> Any:
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("create_room", _create_collaboration_room_node)
    graph.add_edge("create_room", END)
    graph.set_entry_point("create_room")
    return graph.compile()
