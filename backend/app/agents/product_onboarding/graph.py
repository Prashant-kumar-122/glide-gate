"""LangGraph StateGraph for the Product Onboarding agent (Phase 0.5 / Phase 4).

Phase 4 additions:
  - Entry capability validation: checks that ONBOARD_PRODUCT is declared in
    domain_agent_capabilities.subscribed_task_types for the product_onboarding
    agent.  Non-fatal — logs a warning if the DB check cannot be satisfied.
  - Named agent trace: to_agent is written as "product_onboarding[{product_code}]"
    so each product track is individually identifiable in the trace canvas.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict


async def _validate_agent_entry(task_type: str, domain_code: str = "wealth_management") -> None:
    """Soft capability check: warn if task_type is not subscribed by product_onboarding."""
    try:
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models.domain import Domain, DomainAgentCapabilities

        async with AsyncSessionLocal() as db:
            domain_id = await db.scalar(
                select(Domain.id).where(Domain.domain_code == domain_code)
            )
            if domain_id is None:
                return

            caps = await db.scalar(
                select(DomainAgentCapabilities).where(
                    DomainAgentCapabilities.domain_id == domain_id,
                    DomainAgentCapabilities.agent_id == "product_onboarding",
                )
            )
            if caps is None:
                return

            subscribed = list(caps.subscribed_task_types or [])
            if task_type not in subscribed:
                from loguru import logger as _log
                _log.warning(
                    f"Capability contract violation: task_type={task_type!r} not in "
                    f"product_onboarding.subscribed_task_types={subscribed}"
                )
    except Exception:
        pass  # Non-fatal — validation is best-effort


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

    # Phase 4: entry capability validation — soft check, never blocks execution.
    await _validate_agent_entry(TaskType.ONBOARD_PRODUCT)

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

    # Phase 4: named agent identifier includes product_code for per-product traceability.
    _named_agent = f"product_onboarding[{product_code}]"

    await socket_emitter.agent_message(case_id, {
        "from_agent": "orchestrator",
        "to_agent": _named_agent,
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
    # types.  Phase 4: to_agent uses the named identifier so each product track is
    # independently visible in the trace canvas.
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
                to_agent=_named_agent,
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
            f"{_named_agent} trace written: case={case_id} "
            f"status={response.status} track={track_status}"
        )
    except Exception as _exc:
        from loguru import logger as _log
        _log.warning(f"{_named_agent} trace write FAILED case={case_id}: {_exc}")

    await socket_emitter.task_complete(case_id, {
        "from_agent": _named_agent,
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
