"""LangGraph StateGraph for the Notification agent (Phase 0.5).

Notification dispatch is a side-effect: the node calls the existing
NotificationAgent logic and returns state unchanged.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict


async def _send_notification_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Dispatch the notification described by state['_notification_payload']."""
    from uuid import UUID

    from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType
    from app.agents.notification.notification_agent import NotificationAgent

    payload: dict[str, Any] = state.get("_notification_payload", {})
    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")

    if not payload or not case_id_str:
        return state

    agent = NotificationAgent()
    packet = TaskPacket(
        from_agent=AgentID.ORCHESTRATOR,
        to_agent=AgentID.NOTIFICATION,
        task_type=TaskType.SEND_NOTIFICATION,
        case_id=UUID(case_id_str),
        client_id=UUID(client_id_str),
        priority=payload.get("priority", "NORMAL"),
        payload=payload,
    )
    await agent.process(packet)
    return state


async def _send_escalation_alert_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Dispatch an escalation alert described by state['_notification_payload']."""
    from uuid import UUID

    from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType
    from app.agents.notification.notification_agent import NotificationAgent

    payload: dict[str, Any] = state.get("_notification_payload", {})
    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")

    if not payload or not case_id_str:
        return state

    agent = NotificationAgent()
    packet = TaskPacket(
        from_agent=AgentID.ORCHESTRATOR,
        to_agent=AgentID.NOTIFICATION,
        task_type=TaskType.SEND_ESCALATION_ALERT,
        case_id=UUID(case_id_str),
        client_id=UUID(client_id_str),
        priority="CRITICAL",
        payload=payload,
    )
    await agent.process(packet)
    return state


def build_notification_graph() -> Any:
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("send_notification", _send_notification_node)
    graph.add_edge("send_notification", END)
    graph.set_entry_point("send_notification")
    return graph.compile()


def build_escalation_alert_graph() -> Any:
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("send_escalation_alert", _send_escalation_alert_node)
    graph.add_edge("send_escalation_alert", END)
    graph.set_entry_point("send_escalation_alert")
    return graph.compile()
