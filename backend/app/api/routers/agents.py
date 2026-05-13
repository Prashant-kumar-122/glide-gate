from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.error_handlers import NotFoundError
from app.database import get_db
from app.models.agents import Agent, AgentTask

router = APIRouter(prefix="/agents", tags=["agents"])


# ── Response models ───────────────────────────────────────────────────────────

class AgentOut(BaseModel):
    id: UUID
    agent_id: str
    name: str
    description: str | None
    agent_type: str
    is_active: bool
    capabilities: list[str]
    llm_provider: str | None
    llm_model: str | None

    model_config = {"from_attributes": True}


class AgentTaskOut(BaseModel):
    id: UUID
    from_agent: str
    to_agent: str
    task_type: str
    case_id: UUID
    client_id: UUID
    priority: str
    status: str
    result: dict[str, Any]
    errors: list[Any]
    duration_ms: int | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class AgentTraceOut(BaseModel):
    case_id: UUID
    tasks: list[AgentTaskOut]
    total: int


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[AgentOut])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> list[AgentOut]:
    result = await db.execute(select(Agent).order_by(Agent.name))
    agents = result.scalars().all()
    return [AgentOut.model_validate(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> AgentOut:
    result = await db.execute(select(Agent).where(Agent.agent_id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise NotFoundError("Agent", agent_id)
    return AgentOut.model_validate(agent)


@router.get("/trace/{case_id}", response_model=AgentTraceOut)
async def get_agent_trace(
    case_id: UUID,
    task_type: str | None = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> AgentTraceOut:
    query = (
        select(AgentTask)
        .where(AgentTask.case_id == case_id)
        .order_by(AgentTask.created_at)
        .limit(limit)
    )
    if task_type:
        query = query.where(AgentTask.task_type == task_type)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return AgentTraceOut(
        case_id=case_id,
        tasks=[AgentTaskOut.model_validate(t) for t in tasks],
        total=len(tasks),
    )
