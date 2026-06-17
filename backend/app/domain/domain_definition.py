"""DomainDefinition — in-memory model of a fully-loaded domain (Phase 1).

DomainDefinitionLoader.load(domain_id, session) reads all domain_* tables for
a given domain and assembles a validated DomainDefinition.  The loader runs
these contract checks on every load and raises DomainValidationError on failure:

  1. No dangling transition targets (every referenced stage must exist)
  2. Every from_stage in transitions is a known stage
  3. At least one terminal stage is reachable from the initial stage (BFS)
  4. Every SLA row references a stage that exists in domain_stages
  5. warning_pct < escalation_pct for every SLA row (also enforced by DB CHECK)
"""
from __future__ import annotations

from collections import deque
from typing import Any

from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ── Error type ────────────────────────────────────────────────────────────────


class DomainValidationError(ValueError):
    """Raised by DomainDefinitionLoader.validate() on a malformed domain."""


# ── Per-table Pydantic value objects ──────────────────────────────────────────


class StageSpec(BaseModel):
    stage_code: str
    display_name: str
    is_terminal: bool = False
    is_human_pending: bool = False


class StageActionSpec(BaseModel):
    stage_code: str
    target_agent: str
    task_type: str
    priority: str = "NORMAL"
    payload_template: dict[str, Any] = {}
    notification_templates: dict[str, Any] = {}


class AgentRosterEntry(BaseModel):
    agent_id: str
    agent_class: str
    status: str = "APPROVED"  # APPROVED | DEPRECATED


class AgentCapabilitySpec(BaseModel):
    agent_id: str
    subscribed_task_types: list[str] = []
    emitted_task_types: list[str] = []
    allowed_handoff_targets: list[str] = []


class ProductPipelineStep(BaseModel):
    product_code: str
    step_id: str
    step_label: str
    step_order: int
    is_parallel: bool = False
    step_config: dict[str, Any] = {}


class AgentPrompt(BaseModel):
    agent_id: str
    prompt_role: str
    prompt_text: str


class AgentSkillBinding(BaseModel):
    agent_id: str
    skill_id: str
    bound_parameters: dict[str, Any] = {}


class AgentToolGrant(BaseModel):
    agent_id: str
    connector_id: str
    tool_name: str


class SLASpec(BaseModel):
    stage_code: str
    priority_tier: str | None = None
    product_code: str | None = None
    is_enabled: bool = True
    window_hours: float
    warning_pct: int = 80
    escalation_pct: int = 100
    warning_task_type: str
    escalation_task_type: str
    escalation_target_agent: str
    pause_on_human_review: bool = False

    @model_validator(mode="after")
    def _check_pct_order(self) -> "SLASpec":
        if self.warning_pct >= self.escalation_pct:
            raise ValueError(
                f"warning_pct ({self.warning_pct}) must be < escalation_pct ({self.escalation_pct})"
            )
        return self


class PersonaSpec(BaseModel):
    persona_code: str
    display_label: str
    color: str = "#000000"
    default_route: str = "/"
    nav_links: list[Any] = []


class DomainProductSpec(BaseModel):
    product_code: str
    display_name: str
    product_type: str = "retail"
    is_active: bool = True
    suitability_criteria: dict[str, Any] = {}
    required_documents: list[str] = []
    activation_criteria: dict[str, Any] = {}


class DisplayConfigEntry(BaseModel):
    entity_type: str
    entity_code: str
    label: str
    color: str = "#000000"
    style: dict[str, Any] = {}


# ── Assembled domain model ────────────────────────────────────────────────────


class DomainDefinition(BaseModel):
    """Fully loaded, validated in-memory representation of one configured domain."""

    domain_id: str
    domain_code: str
    display_name: str
    is_active: bool
    initial_stage: str = "INTAKE"

    # FSM
    stages: dict[str, StageSpec]           # stage_code → spec
    transitions: dict[str, list[str]]      # from_stage → [to_stage, ...]

    # Stage-level orchestration
    task_routing: dict[str, StageActionSpec]   # stage_code → action spec

    # Agent configuration
    agent_roster: dict[str, AgentRosterEntry]              # agent_id → entry
    agent_capabilities: dict[str, AgentCapabilitySpec]     # agent_id → caps
    agent_prompts: dict[str, list[AgentPrompt]]            # agent_id → [prompts]
    agent_skills: dict[str, list[AgentSkillBinding]]       # agent_id → [bindings]
    agent_tool_grants: dict[str, list[AgentToolGrant]]     # agent_id → [grants]

    # Product pipelines
    product_pipelines: dict[str, list[ProductPipelineStep]]  # product_code → [steps ordered by step_order]

    # SLA configuration
    slas: list[SLASpec]

    # Personas + permission model
    personas: dict[str, PersonaSpec]          # persona_code → spec
    permissions: dict[str, list[str]]         # persona_code → [permission_scopes]

    # Product catalog
    products: dict[str, DomainProductSpec]    # product_code → spec

    # Frontend display vocabulary
    display_config: dict[str, DisplayConfigEntry]  # "{entity_type}:{entity_code}" → entry


# ── Loader ────────────────────────────────────────────────────────────────────


class DomainDefinitionLoader:
    """Reads all domain_* tables for a given domain and returns a DomainDefinition.

    Usage::

        async with AsyncSessionLocal() as session:
            loader = DomainDefinitionLoader(session)
            domain = await loader.load("wealth_management")
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, domain_code_or_id: str) -> DomainDefinition:
        """Load a domain by domain_code (preferred) or domain_id (UUID string).

        Raises:
            ValueError: if the domain is not found.
            DomainValidationError: if the loaded domain fails contract checks.
        """
        from app.models.domain import (
            Domain,
            DomainAgentCapabilities,
            DomainAgentPrompt,
            DomainAgentRoster,
            DomainAgentSkill,
            DomainAgentToolGrant,
            DomainDisplayConfig,
            DomainPermission,
            DomainPersona,
            DomainProduct,
            DomainProductPipeline,
            DomainStageSLA,
            DomainStage,
            DomainTaskRouting,
            DomainTransition,
        )

        # Resolve domain row
        domain_row = await self._session.scalar(
            select(Domain).where(Domain.domain_code == domain_code_or_id)
        )
        if domain_row is None:
            # Try by UUID
            try:
                from uuid import UUID
                uid = UUID(domain_code_or_id)
                domain_row = await self._session.get(Domain, uid)
            except ValueError:
                pass
        if domain_row is None:
            raise ValueError(f"Domain {domain_code_or_id!r} not found")

        domain_id = domain_row.id

        # ── stages ────────────────────────────────────────────────────────────
        stage_rows = (await self._session.scalars(
            select(DomainStage).where(DomainStage.domain_id == domain_id)
        )).all()
        stages: dict[str, StageSpec] = {
            r.stage_code: StageSpec(
                stage_code=r.stage_code,
                display_name=r.display_name,
                is_terminal=r.is_terminal,
                is_human_pending=r.is_human_pending,
            )
            for r in stage_rows
        }

        # ── transitions ───────────────────────────────────────────────────────
        trans_rows = (await self._session.scalars(
            select(DomainTransition).where(DomainTransition.domain_id == domain_id)
        )).all()
        transitions: dict[str, list[str]] = {}
        for r in trans_rows:
            transitions.setdefault(r.from_stage, []).append(r.to_stage)
        # Ensure every stage has an entry (even if no outgoing transitions)
        for stage_code in stages:
            transitions.setdefault(stage_code, [])

        # ── task routing ──────────────────────────────────────────────────────
        routing_rows = (await self._session.scalars(
            select(DomainTaskRouting).where(DomainTaskRouting.domain_id == domain_id)
        )).all()
        task_routing: dict[str, StageActionSpec] = {
            r.stage_code: StageActionSpec(
                stage_code=r.stage_code,
                target_agent=r.target_agent,
                task_type=r.task_type,
                priority=r.priority,
                payload_template=r.payload_template or {},
                notification_templates=r.notification_templates or {},
            )
            for r in routing_rows
        }

        # ── agent roster ──────────────────────────────────────────────────────
        roster_rows = (await self._session.scalars(
            select(DomainAgentRoster).where(DomainAgentRoster.domain_id == domain_id)
        )).all()
        agent_roster: dict[str, AgentRosterEntry] = {
            r.agent_id: AgentRosterEntry(agent_id=r.agent_id, agent_class=r.agent_class, status=r.status)
            for r in roster_rows
        }

        # ── agent capabilities ────────────────────────────────────────────────
        caps_rows = (await self._session.scalars(
            select(DomainAgentCapabilities).where(DomainAgentCapabilities.domain_id == domain_id)
        )).all()
        agent_capabilities: dict[str, AgentCapabilitySpec] = {
            r.agent_id: AgentCapabilitySpec(
                agent_id=r.agent_id,
                subscribed_task_types=list(r.subscribed_task_types or []),
                emitted_task_types=list(r.emitted_task_types or []),
                allowed_handoff_targets=list(r.allowed_handoff_targets or []),
            )
            for r in caps_rows
        }

        # ── product pipelines ─────────────────────────────────────────────────
        pipeline_rows = (await self._session.scalars(
            select(DomainProductPipeline)
            .where(DomainProductPipeline.domain_id == domain_id)
            .order_by(DomainProductPipeline.product_code, DomainProductPipeline.step_order)
        )).all()
        product_pipelines: dict[str, list[ProductPipelineStep]] = {}
        for r in pipeline_rows:
            product_pipelines.setdefault(r.product_code, []).append(
                ProductPipelineStep(
                    product_code=r.product_code,
                    step_id=r.step_id,
                    step_label=r.step_label,
                    step_order=r.step_order,
                    is_parallel=r.is_parallel,
                    step_config=r.step_config or {},
                )
            )

        # ── agent prompts ─────────────────────────────────────────────────────
        prompt_rows = (await self._session.scalars(
            select(DomainAgentPrompt).where(DomainAgentPrompt.domain_id == domain_id)
        )).all()
        agent_prompts: dict[str, list[AgentPrompt]] = {}
        for r in prompt_rows:
            agent_prompts.setdefault(r.agent_id, []).append(
                AgentPrompt(agent_id=r.agent_id, prompt_role=r.prompt_role, prompt_text=r.prompt_text)
            )

        # ── agent skills ──────────────────────────────────────────────────────
        skill_rows = (await self._session.scalars(
            select(DomainAgentSkill).where(DomainAgentSkill.domain_id == domain_id)
        )).all()
        agent_skills: dict[str, list[AgentSkillBinding]] = {}
        for r in skill_rows:
            agent_skills.setdefault(r.agent_id, []).append(
                AgentSkillBinding(agent_id=r.agent_id, skill_id=r.skill_id, bound_parameters=r.bound_parameters or {})
            )

        # ── agent tool grants ─────────────────────────────────────────────────
        grant_rows = (await self._session.scalars(
            select(DomainAgentToolGrant).where(DomainAgentToolGrant.domain_id == domain_id)
        )).all()
        agent_tool_grants: dict[str, list[AgentToolGrant]] = {}
        for r in grant_rows:
            agent_tool_grants.setdefault(r.agent_id, []).append(
                AgentToolGrant(agent_id=r.agent_id, connector_id=r.connector_id, tool_name=r.tool_name)
            )

        # ── SLAs ──────────────────────────────────────────────────────────────
        sla_rows = (await self._session.scalars(
            select(DomainStageSLA).where(DomainStageSLA.domain_id == domain_id)
        )).all()
        slas: list[SLASpec] = [
            SLASpec(
                stage_code=r.stage_code,
                priority_tier=r.priority_tier,
                product_code=r.product_code,
                is_enabled=r.is_enabled,
                window_hours=float(r.window_hours),
                warning_pct=r.warning_pct,
                escalation_pct=r.escalation_pct,
                warning_task_type=r.warning_task_type,
                escalation_task_type=r.escalation_task_type,
                escalation_target_agent=r.escalation_target_agent,
                pause_on_human_review=r.pause_on_human_review,
            )
            for r in sla_rows
        ]

        # ── personas ──────────────────────────────────────────────────────────
        persona_rows = (await self._session.scalars(
            select(DomainPersona).where(DomainPersona.domain_id == domain_id)
        )).all()
        personas: dict[str, PersonaSpec] = {
            r.persona_code: PersonaSpec(
                persona_code=r.persona_code,
                display_label=r.display_label,
                color=r.color,
                default_route=r.default_route,
                nav_links=list(r.nav_links or []),
            )
            for r in persona_rows
        }

        # ── permissions ───────────────────────────────────────────────────────
        perm_rows = (await self._session.scalars(
            select(DomainPermission).where(DomainPermission.domain_id == domain_id)
        )).all()
        permissions: dict[str, list[str]] = {}
        for r in perm_rows:
            permissions.setdefault(r.persona_code, []).append(r.permission_scope)

        # ── products ──────────────────────────────────────────────────────────
        product_rows = (await self._session.scalars(
            select(DomainProduct).where(DomainProduct.domain_id == domain_id)
        )).all()
        products: dict[str, DomainProductSpec] = {
            r.product_code: DomainProductSpec(
                product_code=r.product_code,
                display_name=r.display_name,
                product_type=r.product_type,
                is_active=r.is_active,
                suitability_criteria=r.suitability_criteria or {},
                required_documents=list(r.required_documents or []),
                activation_criteria=r.activation_criteria or {},
            )
            for r in product_rows
        }

        # ── display config ────────────────────────────────────────────────────
        display_rows = (await self._session.scalars(
            select(DomainDisplayConfig).where(DomainDisplayConfig.domain_id == domain_id)
        )).all()
        display_config: dict[str, DisplayConfigEntry] = {
            f"{r.entity_type}:{r.entity_code}": DisplayConfigEntry(
                entity_type=r.entity_type,
                entity_code=r.entity_code,
                label=r.label,
                color=r.color,
                style=r.style or {},
            )
            for r in display_rows
        }

        domain_def = DomainDefinition(
            domain_id=str(domain_id),
            domain_code=domain_row.domain_code,
            display_name=domain_row.display_name,
            is_active=domain_row.is_active,
            stages=stages,
            transitions=transitions,
            task_routing=task_routing,
            agent_roster=agent_roster,
            agent_capabilities=agent_capabilities,
            agent_prompts=agent_prompts,
            agent_skills=agent_skills,
            agent_tool_grants=agent_tool_grants,
            product_pipelines=product_pipelines,
            slas=slas,
            personas=personas,
            permissions=permissions,
            products=products,
            display_config=display_config,
        )

        self.validate(domain_def)
        return domain_def

    # ── Contract validation ────────────────────────────────────────────────────

    @staticmethod
    def validate(domain_def: DomainDefinition) -> None:
        """Validate internal consistency of a DomainDefinition.

        Raises DomainValidationError on first failure (fail-fast).
        """
        stage_codes = set(domain_def.stages.keys())
        initial = domain_def.initial_stage

        # 1. initial_stage must be a known stage
        if initial not in stage_codes:
            raise DomainValidationError(
                f"initial_stage {initial!r} is not in domain_stages"
            )

        # 2. No dangling transition endpoints
        for from_stage, to_stages in domain_def.transitions.items():
            if from_stage not in stage_codes:
                raise DomainValidationError(
                    f"Transition from unknown stage {from_stage!r}"
                )
            for to_stage in to_stages:
                if to_stage not in stage_codes:
                    raise DomainValidationError(
                        f"Transition {from_stage!r} → {to_stage!r} references unknown stage"
                    )

        # 3. At least one terminal stage must exist and be reachable from initial_stage
        terminal_stages = {code for code, spec in domain_def.stages.items() if spec.is_terminal}
        if not terminal_stages:
            raise DomainValidationError("Domain has no terminal stages defined")

        reachable = _bfs_reachable(initial, domain_def.transitions)
        unreachable_terminals = terminal_stages - reachable
        if unreachable_terminals:
            raise DomainValidationError(
                f"Terminal stage(s) not reachable from initial stage {initial!r}: "
                f"{sorted(unreachable_terminals)}"
            )

        # 4. SLA rows reference defined stages
        for sla in domain_def.slas:
            if sla.stage_code not in stage_codes:
                raise DomainValidationError(
                    f"SLA row references undefined stage {sla.stage_code!r}"
                )
            # warning_pct < escalation_pct is enforced by SLASpec's model_validator,
            # but re-check here so validate() catches both DB-loaded and in-memory objects
            if sla.warning_pct >= sla.escalation_pct:
                raise DomainValidationError(
                    f"SLA for stage {sla.stage_code!r}: "
                    f"warning_pct ({sla.warning_pct}) must be < escalation_pct ({sla.escalation_pct})"
                )


def _bfs_reachable(start: str, transitions: dict[str, list[str]]) -> set[str]:
    """Return the set of all stage codes reachable from `start` (inclusive)."""
    visited: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in transitions.get(node, []):
            if neighbor not in visited:
                queue.append(neighbor)
    return visited
