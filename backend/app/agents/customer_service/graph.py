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

    from app.websocket.socket_emitter import socket_emitter

    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")
    selected_products = state.get("selected_products", [])

    if not case_id_str:
        return {**state, "next_stage": None}

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

    # Persist an AgentTask so the customer_service node appears in the trace canvas.
    # Wrapped in try/except so a trace failure never brings down the kickoff activity.
    if client_id_str:
        try:
            from datetime import datetime, timezone
            from uuid import uuid4
            from app.database import AsyncSessionLocal
            from app.models.agents import AgentTask

            task_id = uuid4()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            async with AsyncSessionLocal() as db:
                db.add(AgentTask(
                    id=task_id,
                    from_agent="orchestrator",
                    to_agent="customer_service",
                    task_type="collect_client_data",
                    case_id=UUID(case_id_str),
                    client_id=UUID(client_id_str),
                    priority="NORMAL",
                    payload={"selected_products": selected_products},
                    status="SUCCESS",
                    result={"event": "INTAKE_STARTED"},
                    errors=[],
                    duration_ms=0,
                    ttl=300,
                    started_at=now,
                    completed_at=now,
                ))
                await db.commit()
            await socket_emitter.agent_message(case_id, {
                "from_agent": "orchestrator",
                "to_agent": "customer_service",
                "task_type": "collect_client_data",
                "task_id": str(task_id),
                "status": "IN_PROGRESS",
            })
        except Exception:
            pass

    return {**state, "next_stage": None}


def build_customer_service_kickoff_graph() -> Any:
    """Return a compiled LangGraph graph for the CustomerService kickoff."""
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("kickoff", _kickoff_node)
    graph.add_edge("kickoff", END)
    graph.set_entry_point("kickoff")
    return graph.compile()
