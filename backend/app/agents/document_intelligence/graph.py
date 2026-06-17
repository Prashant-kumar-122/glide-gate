"""LangGraph StateGraph for the Document Intelligence agent (Phase 0.5).

The document-processing tasks (classify, OCR, validate, diff) are on-demand
operations triggered by the documents REST API. This graph wraps the agent for
Temporal activity invocation with explicit task-type routing via state.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict


async def _process_document_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Dispatch the document task described by state['_doc_task']."""
    from uuid import UUID

    from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType
    from app.agents.document_intelligence.document_intelligence_agent import (
        DocumentIntelligenceAgent,
    )

    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")
    doc_task: dict[str, Any] = state.get("_doc_task", {})

    if not case_id_str or not doc_task:
        return state

    task_type_str = doc_task.get("task_type", "classify_document")
    try:
        task_type = TaskType(task_type_str)
    except ValueError:
        task_type = TaskType.CLASSIFY_DOCUMENT

    agent = DocumentIntelligenceAgent()

    packet = TaskPacket(
        from_agent=AgentID.ORCHESTRATOR,
        to_agent=AgentID.DOCUMENT_INTELLIGENCE,
        task_type=task_type,
        case_id=UUID(case_id_str),
        client_id=UUID(client_id_str),
        priority="NORMAL",
        payload=doc_task.get("payload", {}),
    )
    response = await agent.process(packet)
    return {**state, "_doc_result": response.result}


def build_document_intelligence_graph() -> Any:
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("process_document", _process_document_node)
    graph.add_edge("process_document", END)
    graph.set_entry_point("process_document")
    return graph.compile()
