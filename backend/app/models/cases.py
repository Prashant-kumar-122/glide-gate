from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OnboardingCase(Base):
    __tablename__ = "onboarding_cases"
    __table_args__ = (
        CheckConstraint("status IN ('INTAKE','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED')", name="oc_status_chk"),
        CheckConstraint("current_stage IN ('INTAKE','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED')", name="oc_stage_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="INTAKE", index=True)
    current_stage: Mapped[str] = mapped_column(String(30), nullable=False, default="INTAKE", index=True)
    selected_products: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    shared_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    assigned_advisor_id: Mapped[UUID | None] = mapped_column(index=True)
    sla_deadline: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    client: Mapped[Any] = relationship("Client", back_populates="onboarding_cases")
    case_products: Mapped[list[CaseProduct]] = relationship("CaseProduct", back_populates="case", cascade="all, delete-orphan")
    documents: Mapped[list[Any]] = relationship("Document", back_populates="case")
    kyc_checks: Mapped[list[Any]] = relationship("KYCCheck", back_populates="case")
    human_reviews: Mapped[list[Any]] = relationship("HumanReview", back_populates="case")
    agent_tasks: Mapped[list[Any]] = relationship("AgentTask", back_populates="case")
    notifications: Mapped[list[Any]] = relationship("Notification", back_populates="case")
    case_summaries: Mapped[list[Any]] = relationship("CaseSummary", back_populates="case")
    collaboration_rooms: Mapped[list[Any]] = relationship("CollaborationRoom", back_populates="case")
    conversation_messages: Mapped[list[Any]] = relationship("ConversationMessage", back_populates="case")
    question_sessions: Mapped[list[Any]] = relationship("OnboardingQuestionSession", back_populates="case")
    answers: Mapped[list[Any]] = relationship("OnboardingAnswer", back_populates="case")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("product_code", name="products_code_uq"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    required_documents: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    suitability_criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    step_sequence: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    case_products: Mapped[list[CaseProduct]] = relationship("CaseProduct", back_populates="product")


class CaseProduct(Base):
    __tablename__ = "case_products"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','IN_PROGRESS','COMPLETE','FAILED','SKIPPED')", name="cp_status_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    suitability_outcome: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    account_number: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    case: Mapped[OnboardingCase] = relationship("OnboardingCase", back_populates="case_products")
    product: Mapped[Product] = relationship("Product", back_populates="case_products")
    steps: Mapped[list[CaseProductStep]] = relationship("CaseProductStep", back_populates="case_product", cascade="all, delete-orphan")


class CaseProductStep(Base):
    __tablename__ = "case_product_steps"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','IN_PROGRESS','COMPLETE','FAILED','SKIPPED')", name="cps_status_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_product_id: Mapped[UUID] = mapped_column(ForeignKey("case_products.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    case_product: Mapped[CaseProduct] = relationship("CaseProduct", back_populates="steps")
