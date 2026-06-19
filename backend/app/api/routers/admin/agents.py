from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.permission_guard import require_permission
from app.api.error_handlers import ConflictError, NotFoundError, UnprocessableError
from app.database import get_db
from app.models.domain import (
    Domain,
    DomainAgentCapabilities,
    DomainAgentPrompt,
    DomainAgentRoster,
    DomainAgentSkill,
    DomainAgentToolGrant,
)
from app.services.audit.audit_event_types import AuditEventType
from app.services.audit.decision_log_service import DecisionLogEntry, decision_log_service

router = APIRouter(prefix="/admin/domains", tags=["admin"])

_VALID_STATUSES = {"APPROVED", "DEPRECATED"}


async def _get_domain_or_404(domain_id: UUID, db: AsyncSession) -> Domain:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    if not domain:
        raise NotFoundError(f"Domain {domain_id} not found")
    return domain


async def _log(action: str, payload: dict[str, Any]) -> None:
    await decision_log_service.append(
        DecisionLogEntry(
            agent_id="admin_portal",
            event_type=AuditEventType.CONFIG_CHANGE,
            payload={"action": action, **payload},
        )
    )


# ── Roster models ─────────────────────────────────────────────────────────────

class AgentRosterOut(BaseModel):
    id: str
    domain_id: str
    agent_id: str
    agent_class: str
    status: str


class AgentRosterCreate(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=100)
    agent_class: str = Field(..., min_length=1, max_length=255)
    status: str = "APPROVED"


class AgentStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(APPROVED|DEPRECATED)$")


# ── Capabilities models ───────────────────────────────────────────────────────

class AgentCapabilitiesOut(BaseModel):
    id: str
    domain_id: str
    agent_id: str
    subscribed_task_types: list[str]
    emitted_task_types: list[str]
    allowed_handoff_targets: list[str]


class AgentCapabilitiesUpsert(BaseModel):
    subscribed_task_types: list[str] = []
    emitted_task_types: list[str] = []
    allowed_handoff_targets: list[str] = []


# ── Prompt models ─────────────────────────────────────────────────────────────

class AgentPromptOut(BaseModel):
    id: str
    domain_id: str
    agent_id: str
    prompt_role: str
    prompt_text: str


class AgentPromptUpsert(BaseModel):
    prompt_role: str = Field(..., min_length=1, max_length=100)
    prompt_text: str = Field(..., min_length=1)


# ── Skill binding models ──────────────────────────────────────────────────────

class AgentSkillOut(BaseModel):
    id: str
    domain_id: str
    agent_id: str
    skill_id: str
    bound_parameters: dict[str, Any]


class AgentSkillUpsert(BaseModel):
    skill_id: str = Field(..., min_length=1, max_length=100)
    bound_parameters: dict[str, Any] = {}


# ── Tool grant models ─────────────────────────────────────────────────────────

class AgentToolGrantOut(BaseModel):
    id: str
    domain_id: str
    agent_id: str
    connector_id: str
    tool_name: str


class AgentToolGrantCreate(BaseModel):
    connector_id: str = Field(..., min_length=1, max_length=100)
    tool_name: str = Field(..., min_length=1, max_length=100)


# ── Roster routes ─────────────────────────────────────────────────────────────

@router.get("/{domain_id}/agents", response_model=list[AgentRosterOut])
async def list_agents(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[AgentRosterOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentRoster)
        .where(DomainAgentRoster.domain_id == domain_id)
        .order_by(DomainAgentRoster.agent_id)
    )
    return [
        AgentRosterOut(
            id=str(r.id), domain_id=str(r.domain_id),
            agent_id=r.agent_id, agent_class=r.agent_class, status=r.status,
        )
        for r in result.scalars().all()
    ]


@router.post("/{domain_id}/agents", response_model=AgentRosterOut, status_code=201)
async def add_agent(
    domain_id: UUID,
    body: AgentRosterCreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> AgentRosterOut:
    await _get_domain_or_404(domain_id, db)
    if body.status not in _VALID_STATUSES:
        raise UnprocessableError(f"status must be one of {_VALID_STATUSES}")
    existing = await db.execute(
        select(DomainAgentRoster).where(
            DomainAgentRoster.domain_id == domain_id,
            DomainAgentRoster.agent_id == body.agent_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Agent '{body.agent_id}' already in roster")

    row = DomainAgentRoster(
        domain_id=domain_id,
        agent_id=body.agent_id,
        agent_class=body.agent_class,
        status=body.status,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    out = AgentRosterOut(
        id=str(row.id), domain_id=str(row.domain_id),
        agent_id=row.agent_id, agent_class=row.agent_class, status=row.status,
    )
    await db.commit()
    await _log("agent_added", {"domain_id": str(domain_id), "agent_id": body.agent_id})
    return out


@router.patch("/{domain_id}/agents/{agent_id}/status", response_model=AgentRosterOut)
async def update_agent_status(
    domain_id: UUID,
    agent_id: str,
    body: AgentStatusUpdate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> AgentRosterOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentRoster).where(
            DomainAgentRoster.domain_id == domain_id,
            DomainAgentRoster.agent_id == agent_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError(f"Agent '{agent_id}' not in roster for domain {domain_id}")

    row.status = body.status
    await db.flush()
    await db.refresh(row)
    out = AgentRosterOut(
        id=str(row.id), domain_id=str(row.domain_id),
        agent_id=row.agent_id, agent_class=row.agent_class, status=row.status,
    )
    await db.commit()
    await _log("agent_status_updated", {"domain_id": str(domain_id), "agent_id": agent_id, "status": body.status})
    return out


@router.delete("/{domain_id}/agents/{agent_id}", status_code=204)
async def remove_agent(
    domain_id: UUID,
    agent_id: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentRoster).where(
            DomainAgentRoster.domain_id == domain_id,
            DomainAgentRoster.agent_id == agent_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError(f"Agent '{agent_id}' not in roster for domain {domain_id}")
    await db.delete(row)
    await db.commit()
    await _log("agent_removed", {"domain_id": str(domain_id), "agent_id": agent_id})
    return Response(status_code=204)


# ── Capabilities routes ───────────────────────────────────────────────────────

@router.get("/{domain_id}/agents/{agent_id}/capabilities", response_model=AgentCapabilitiesOut)
async def get_capabilities(
    domain_id: UUID,
    agent_id: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> AgentCapabilitiesOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentCapabilities).where(
            DomainAgentCapabilities.domain_id == domain_id,
            DomainAgentCapabilities.agent_id == agent_id,
        )
    )
    cap = result.scalar_one_or_none()
    if not cap:
        raise NotFoundError(f"No capabilities row for agent '{agent_id}' in domain {domain_id}")
    return AgentCapabilitiesOut(
        id=str(cap.id), domain_id=str(cap.domain_id), agent_id=cap.agent_id,
        subscribed_task_types=cap.subscribed_task_types,
        emitted_task_types=cap.emitted_task_types,
        allowed_handoff_targets=cap.allowed_handoff_targets,
    )


@router.put("/{domain_id}/agents/{agent_id}/capabilities", response_model=AgentCapabilitiesOut)
async def upsert_capabilities(
    domain_id: UUID,
    agent_id: str,
    body: AgentCapabilitiesUpsert,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> AgentCapabilitiesOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentCapabilities).where(
            DomainAgentCapabilities.domain_id == domain_id,
            DomainAgentCapabilities.agent_id == agent_id,
        )
    )
    cap = result.scalar_one_or_none()
    if cap:
        cap.subscribed_task_types = body.subscribed_task_types
        cap.emitted_task_types = body.emitted_task_types
        cap.allowed_handoff_targets = body.allowed_handoff_targets
    else:
        cap = DomainAgentCapabilities(
            domain_id=domain_id,
            agent_id=agent_id,
            subscribed_task_types=body.subscribed_task_types,
            emitted_task_types=body.emitted_task_types,
            allowed_handoff_targets=body.allowed_handoff_targets,
        )
        db.add(cap)

    await db.flush()
    await db.refresh(cap)
    out = AgentCapabilitiesOut(
        id=str(cap.id), domain_id=str(cap.domain_id), agent_id=cap.agent_id,
        subscribed_task_types=cap.subscribed_task_types,
        emitted_task_types=cap.emitted_task_types,
        allowed_handoff_targets=cap.allowed_handoff_targets,
    )
    await db.commit()
    await _log("agent_capabilities_updated", {"domain_id": str(domain_id), "agent_id": agent_id})
    return out


# ── Prompt routes ─────────────────────────────────────────────────────────────

@router.get("/{domain_id}/agents/{agent_id}/prompts", response_model=list[AgentPromptOut])
async def list_prompts(
    domain_id: UUID,
    agent_id: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[AgentPromptOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentPrompt).where(
            DomainAgentPrompt.domain_id == domain_id,
            DomainAgentPrompt.agent_id == agent_id,
        ).order_by(DomainAgentPrompt.prompt_role)
    )
    return [
        AgentPromptOut(
            id=str(p.id), domain_id=str(p.domain_id),
            agent_id=p.agent_id, prompt_role=p.prompt_role, prompt_text=p.prompt_text,
        )
        for p in result.scalars().all()
    ]


@router.put("/{domain_id}/agents/{agent_id}/prompts/{prompt_role}", response_model=AgentPromptOut)
async def upsert_prompt(
    domain_id: UUID,
    agent_id: str,
    prompt_role: str,
    body: AgentPromptUpsert,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> AgentPromptOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentPrompt).where(
            DomainAgentPrompt.domain_id == domain_id,
            DomainAgentPrompt.agent_id == agent_id,
            DomainAgentPrompt.prompt_role == prompt_role,
        )
    )
    prompt = result.scalar_one_or_none()
    if prompt:
        prompt.prompt_text = body.prompt_text
    else:
        prompt = DomainAgentPrompt(
            domain_id=domain_id,
            agent_id=agent_id,
            prompt_role=prompt_role,
            prompt_text=body.prompt_text,
        )
        db.add(prompt)

    await db.flush()
    await db.refresh(prompt)
    out = AgentPromptOut(
        id=str(prompt.id), domain_id=str(prompt.domain_id),
        agent_id=prompt.agent_id, prompt_role=prompt.prompt_role, prompt_text=prompt.prompt_text,
    )
    await db.commit()
    await _log("agent_prompt_upserted", {"domain_id": str(domain_id), "agent_id": agent_id, "prompt_role": prompt_role})
    return out


@router.delete("/{domain_id}/agents/{agent_id}/prompts/{prompt_role}", status_code=204)
async def delete_prompt(
    domain_id: UUID,
    agent_id: str,
    prompt_role: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentPrompt).where(
            DomainAgentPrompt.domain_id == domain_id,
            DomainAgentPrompt.agent_id == agent_id,
            DomainAgentPrompt.prompt_role == prompt_role,
        )
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise NotFoundError(f"Prompt '{prompt_role}' not found for agent '{agent_id}'")
    await db.delete(prompt)
    await db.commit()
    await _log("agent_prompt_deleted", {"domain_id": str(domain_id), "agent_id": agent_id, "prompt_role": prompt_role})
    return Response(status_code=204)


# ── Skill binding routes ──────────────────────────────────────────────────────

@router.get("/{domain_id}/agents/{agent_id}/skills", response_model=list[AgentSkillOut])
async def list_skills(
    domain_id: UUID,
    agent_id: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[AgentSkillOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentSkill).where(
            DomainAgentSkill.domain_id == domain_id,
            DomainAgentSkill.agent_id == agent_id,
        ).order_by(DomainAgentSkill.skill_id)
    )
    return [
        AgentSkillOut(
            id=str(s.id), domain_id=str(s.domain_id),
            agent_id=s.agent_id, skill_id=s.skill_id, bound_parameters=s.bound_parameters,
        )
        for s in result.scalars().all()
    ]


@router.put("/{domain_id}/agents/{agent_id}/skills/{skill_id}", response_model=AgentSkillOut)
async def upsert_skill(
    domain_id: UUID,
    agent_id: str,
    skill_id: str,
    body: AgentSkillUpsert,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> AgentSkillOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentSkill).where(
            DomainAgentSkill.domain_id == domain_id,
            DomainAgentSkill.agent_id == agent_id,
            DomainAgentSkill.skill_id == skill_id,
        )
    )
    skill = result.scalar_one_or_none()
    if skill:
        skill.bound_parameters = body.bound_parameters
    else:
        skill = DomainAgentSkill(
            domain_id=domain_id,
            agent_id=agent_id,
            skill_id=skill_id,
            bound_parameters=body.bound_parameters,
        )
        db.add(skill)

    await db.flush()
    await db.refresh(skill)
    out = AgentSkillOut(
        id=str(skill.id), domain_id=str(skill.domain_id),
        agent_id=skill.agent_id, skill_id=skill.skill_id, bound_parameters=skill.bound_parameters,
    )
    await db.commit()
    await _log("agent_skill_upserted", {"domain_id": str(domain_id), "agent_id": agent_id, "skill_id": skill_id})
    return out


@router.delete("/{domain_id}/agents/{agent_id}/skills/{skill_id}", status_code=204)
async def delete_skill(
    domain_id: UUID,
    agent_id: str,
    skill_id: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentSkill).where(
            DomainAgentSkill.domain_id == domain_id,
            DomainAgentSkill.agent_id == agent_id,
            DomainAgentSkill.skill_id == skill_id,
        )
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise NotFoundError(f"Skill '{skill_id}' not found for agent '{agent_id}'")
    await db.delete(skill)
    await db.commit()
    await _log("agent_skill_deleted", {"domain_id": str(domain_id), "agent_id": agent_id, "skill_id": skill_id})
    return Response(status_code=204)


# ── Tool grant routes ─────────────────────────────────────────────────────────

@router.get("/{domain_id}/agents/{agent_id}/tool-grants", response_model=list[AgentToolGrantOut])
async def list_tool_grants(
    domain_id: UUID,
    agent_id: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[AgentToolGrantOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentToolGrant).where(
            DomainAgentToolGrant.domain_id == domain_id,
            DomainAgentToolGrant.agent_id == agent_id,
        ).order_by(DomainAgentToolGrant.connector_id, DomainAgentToolGrant.tool_name)
    )
    return [
        AgentToolGrantOut(
            id=str(g.id), domain_id=str(g.domain_id),
            agent_id=g.agent_id, connector_id=g.connector_id, tool_name=g.tool_name,
        )
        for g in result.scalars().all()
    ]


@router.post("/{domain_id}/agents/{agent_id}/tool-grants", response_model=AgentToolGrantOut, status_code=201)
async def add_tool_grant(
    domain_id: UUID,
    agent_id: str,
    body: AgentToolGrantCreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> AgentToolGrantOut:
    await _get_domain_or_404(domain_id, db)
    existing = await db.execute(
        select(DomainAgentToolGrant).where(
            DomainAgentToolGrant.domain_id == domain_id,
            DomainAgentToolGrant.agent_id == agent_id,
            DomainAgentToolGrant.connector_id == body.connector_id,
            DomainAgentToolGrant.tool_name == body.tool_name,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Tool grant {body.connector_id}/{body.tool_name} already exists")

    grant = DomainAgentToolGrant(
        domain_id=domain_id,
        agent_id=agent_id,
        connector_id=body.connector_id,
        tool_name=body.tool_name,
    )
    db.add(grant)
    await db.flush()
    await db.refresh(grant)
    out = AgentToolGrantOut(
        id=str(grant.id), domain_id=str(grant.domain_id),
        agent_id=grant.agent_id, connector_id=grant.connector_id, tool_name=grant.tool_name,
    )
    await db.commit()
    await _log(
        "tool_grant_added",
        {"domain_id": str(domain_id), "agent_id": agent_id, "connector_id": body.connector_id, "tool_name": body.tool_name},
    )
    return out


@router.delete("/{domain_id}/agents/{agent_id}/tool-grants/{grant_id}", status_code=204)
async def remove_tool_grant(
    domain_id: UUID,
    agent_id: str,
    grant_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainAgentToolGrant).where(
            DomainAgentToolGrant.id == grant_id,
            DomainAgentToolGrant.domain_id == domain_id,
            DomainAgentToolGrant.agent_id == agent_id,
        )
    )
    grant = result.scalar_one_or_none()
    if not grant:
        raise NotFoundError(f"Tool grant {grant_id} not found")
    await db.delete(grant)
    await db.commit()
    await _log("tool_grant_removed", {"domain_id": str(domain_id), "agent_id": agent_id, "grant_id": str(grant_id)})
    return Response(status_code=204)
