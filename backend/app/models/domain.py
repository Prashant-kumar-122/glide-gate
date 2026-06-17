"""SQLAlchemy ORM models for all domain_* tables (Phase 1).

These models back the DomainDefinitionLoader (Phase 1) and the admin portal
API (Phase 9).  All domain tables cascade-delete from the parent `domains` row
so that dropping a domain removes all its configuration atomically.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=_now, onupdate=_now)

    stages: Mapped[list[DomainStage]] = relationship("DomainStage", back_populates="domain", cascade="all, delete-orphan")
    transitions: Mapped[list[DomainTransition]] = relationship("DomainTransition", back_populates="domain", cascade="all, delete-orphan")
    task_routing: Mapped[list[DomainTaskRouting]] = relationship("DomainTaskRouting", back_populates="domain", cascade="all, delete-orphan")
    agent_roster: Mapped[list[DomainAgentRoster]] = relationship("DomainAgentRoster", back_populates="domain", cascade="all, delete-orphan")
    agent_capabilities: Mapped[list[DomainAgentCapabilities]] = relationship("DomainAgentCapabilities", back_populates="domain", cascade="all, delete-orphan")
    product_pipelines: Mapped[list[DomainProductPipeline]] = relationship("DomainProductPipeline", back_populates="domain", cascade="all, delete-orphan")
    agent_prompts: Mapped[list[DomainAgentPrompt]] = relationship("DomainAgentPrompt", back_populates="domain", cascade="all, delete-orphan")
    agent_skills: Mapped[list[DomainAgentSkill]] = relationship("DomainAgentSkill", back_populates="domain", cascade="all, delete-orphan")
    agent_tool_grants: Mapped[list[DomainAgentToolGrant]] = relationship("DomainAgentToolGrant", back_populates="domain", cascade="all, delete-orphan")
    slas: Mapped[list[DomainStageSLA]] = relationship("DomainStageSLA", back_populates="domain", cascade="all, delete-orphan")
    personas: Mapped[list[DomainPersona]] = relationship("DomainPersona", back_populates="domain", cascade="all, delete-orphan")
    permissions: Mapped[list[DomainPermission]] = relationship("DomainPermission", back_populates="domain", cascade="all, delete-orphan")
    products: Mapped[list[DomainProduct]] = relationship("DomainProduct", back_populates="domain", cascade="all, delete-orphan")
    display_config: Mapped[list[DomainDisplayConfig]] = relationship("DomainDisplayConfig", back_populates="domain", cascade="all, delete-orphan")


class DomainStage(Base):
    __tablename__ = "domain_stages"
    __table_args__ = (UniqueConstraint("domain_id", "stage_code", name="domain_stages_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    stage_code: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_human_pending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    domain: Mapped[Domain] = relationship("Domain", back_populates="stages")


class DomainTransition(Base):
    __tablename__ = "domain_transitions"
    __table_args__ = (UniqueConstraint("domain_id", "from_stage", "to_stage", name="domain_transitions_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    from_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)

    domain: Mapped[Domain] = relationship("Domain", back_populates="transitions")


class DomainTaskRouting(Base):
    __tablename__ = "domain_task_routing"
    __table_args__ = (UniqueConstraint("domain_id", "stage_code", name="domain_task_routing_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    stage_code: Mapped[str] = mapped_column(String(50), nullable=False)
    target_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")
    payload_template: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notification_templates: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    domain: Mapped[Domain] = relationship("Domain", back_populates="task_routing")


class DomainAgentRoster(Base):
    __tablename__ = "domain_agent_roster"
    __table_args__ = (UniqueConstraint("domain_id", "agent_id", name="domain_agent_roster_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_class: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="APPROVED")

    domain: Mapped[Domain] = relationship("Domain", back_populates="agent_roster")


class DomainAgentCapabilities(Base):
    __tablename__ = "domain_agent_capabilities"
    __table_args__ = (UniqueConstraint("domain_id", "agent_id", name="domain_agent_capabilities_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    subscribed_task_types: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    emitted_task_types: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    allowed_handoff_targets: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    domain: Mapped[Domain] = relationship("Domain", back_populates="agent_capabilities")


class DomainProductPipeline(Base):
    __tablename__ = "domain_product_pipelines"
    __table_args__ = (UniqueConstraint("domain_id", "product_code", "step_id", name="domain_product_pipelines_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    step_id: Mapped[str] = mapped_column(String(100), nullable=False)
    step_label: Mapped[str] = mapped_column(String(200), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_parallel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    step_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    domain: Mapped[Domain] = relationship("Domain", back_populates="product_pipelines")


class DomainAgentPrompt(Base):
    __tablename__ = "domain_agent_prompts"
    __table_args__ = (UniqueConstraint("domain_id", "agent_id", "prompt_role", name="domain_agent_prompts_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_role: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)

    domain: Mapped[Domain] = relationship("Domain", back_populates="agent_prompts")


class DomainAgentSkill(Base):
    __tablename__ = "domain_agent_skills"
    __table_args__ = (UniqueConstraint("domain_id", "agent_id", "skill_id", name="domain_agent_skills_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(100), nullable=False)
    bound_parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    domain: Mapped[Domain] = relationship("Domain", back_populates="agent_skills")


class DomainAgentToolGrant(Base):
    __tablename__ = "domain_agent_tool_grants"
    __table_args__ = (UniqueConstraint("domain_id", "agent_id", "connector_id", "tool_name", name="domain_agent_tool_grants_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    connector_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)

    domain: Mapped[Domain] = relationship("Domain", back_populates="agent_tool_grants")


class DomainStageSLA(Base):
    __tablename__ = "domain_stage_slas"
    __table_args__ = (
        CheckConstraint("warning_pct < escalation_pct", name="domain_stage_slas_pct_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    stage_code: Mapped[str] = mapped_column(String(50), nullable=False)
    priority_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    product_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    window_hours: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    warning_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    escalation_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    warning_task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    escalation_task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    escalation_target_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    pause_on_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    domain: Mapped[Domain] = relationship("Domain", back_populates="slas")


class DomainPersona(Base):
    __tablename__ = "domain_personas"
    __table_args__ = (UniqueConstraint("domain_id", "persona_code", name="domain_personas_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    persona_code: Mapped[str] = mapped_column(String(50), nullable=False)
    display_label: Mapped[str] = mapped_column(String(200), nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False, default="#000000")
    default_route: Mapped[str] = mapped_column(String(255), nullable=False, default="/")
    nav_links: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    domain: Mapped[Domain] = relationship("Domain", back_populates="personas")


class DomainPermission(Base):
    __tablename__ = "domain_permissions"
    __table_args__ = (UniqueConstraint("domain_id", "persona_code", "permission_scope", name="domain_permissions_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    persona_code: Mapped[str] = mapped_column(String(50), nullable=False)
    permission_scope: Mapped[str] = mapped_column(String(100), nullable=False)

    domain: Mapped[Domain] = relationship("Domain", back_populates="permissions")


class DomainProduct(Base):
    __tablename__ = "domain_products"
    __table_args__ = (UniqueConstraint("domain_id", "product_code", name="domain_products_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False, default="retail")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    suitability_criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    required_documents: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    activation_criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    domain: Mapped[Domain] = relationship("Domain", back_populates="products")


class DomainDisplayConfig(Base):
    __tablename__ = "domain_display_config"
    __table_args__ = (UniqueConstraint("domain_id", "entity_type", "entity_code", name="domain_display_config_uq"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_code: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False, default="#000000")
    style: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    domain: Mapped[Domain] = relationship("Domain", back_populates="display_config")
