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
    from app.websocket.socket_emitter import socket_emitter

    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")
    product_code: str = state.get("_product_code", "")

    # Fallback: if Temporal stripped _product_code during TypedDict deserialization,
    # recover it from the child workflow ID (onboarding-{case_id}-product-{product_code}).
    if not product_code:
        try:
            from temporalio import activity as _ta
            _wid = _ta.info().workflow_id
            if "-product-" in _wid:
                product_code = _wid.split("-product-", 1)[-1]
        except Exception:
            pass

    if not case_id_str or not client_id_str or not product_code:
        return {**state, "_product_track_status": "FAILED", "next_stage": None}

    case_id = UUID(case_id_str)
    client_id = UUID(client_id_str)
    agent = ProductOnboardingAgent()

    packet = TaskPacket(
        from_agent=AgentID.ORCHESTRATOR,
        to_agent=AgentID.PRODUCT_ONBOARDING,
        task_type=TaskType.ONBOARD_PRODUCT,
        case_id=case_id,
        client_id=client_id,
        priority="NORMAL",
        payload={
            "product_code": product_code,
            "selected_products": state.get("selected_products", []),
            "client_data": state.get("client_data", {}),
        },
    )

    await socket_emitter.agent_message(case_id, {
        "from_agent": "orchestrator",
        "to_agent": "product_onboarding",
        "task_type": "onboard_product",
        "product_code": product_code,
        "status": "IN_PROGRESS",
    })

    response = await agent.timed_process(packet)

    track_status = "COMPLETE" if response.status == "SUCCESS" else response.result.get(
        "track_status", "FAILED"
    )

    # Direct trace write with minimal payload — timed_process's _persist_agent_task
    # silently fails when client_data in the packet payload contains non-JSON-serializable
    # types. This direct write uses a separate UUID and a stripped payload so the
    # product_onboarding node always appears in the trace canvas.
    try:
        from datetime import datetime, timezone
        from uuid import uuid4
        from loguru import logger as _log
        from app.database import AsyncSessionLocal
        from app.models.agents import AgentTask

        trace_id = uuid4()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with AsyncSessionLocal() as db:
            db.add(AgentTask(
                id=trace_id,
                from_agent="orchestrator",
                to_agent="product_onboarding",
                task_type="onboard_product",
                case_id=case_id,
                client_id=client_id,
                priority="NORMAL",
                payload={"product_code": product_code},
                status=response.status,
                result={"track_status": track_status},
                errors=response.errors or [],
                duration_ms=response.duration_ms,
                ttl=300,
                started_at=now,
                completed_at=now,
            ))
            await db.commit()
        _log.info(
            f"product_onboarding trace written: case={case_id} product={product_code} "
            f"status={response.status} track={track_status}"
        )
    except Exception as _exc:
        from loguru import logger as _log
        _log.warning(f"product_onboarding trace write FAILED case={case_id} product={product_code}: {_exc}")

    await socket_emitter.task_complete(case_id, {
        "from_agent": "product_onboarding",
        "to_agent": "orchestrator",
        "task_type": "onboard_product",
        "product_code": product_code,
        "status": "SUCCESS" if track_status == "COMPLETE" else "FAILED",
    })

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
