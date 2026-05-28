from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class KYCCheck(Base):
    __tablename__ = "kyc_checks"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','PASSED','FAILED','ESCALATED')", name="kyc_status_chk"),
        CheckConstraint("risk_band IN ('LOW','MEDIUM','HIGH','VERY_HIGH') OR risk_band IS NULL", name="kyc_risk_band_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False, index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    identity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    aml_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    profile_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    composite_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    risk_band: Mapped[str | None] = mapped_column(String(20))
    identity_verification_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    aml_check_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    sanctions_check_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    checkpoint_rules_applied: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    decision: Mapped[str | None] = mapped_column(String(30))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column()
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="kyc_checks")
    client: Mapped[Any] = relationship("Client")
    human_reviews: Mapped[list[HumanReview]] = relationship("HumanReview", back_populates="kyc_check")


class HumanReview(Base):
    __tablename__ = "human_reviews"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','MORE_INFO_REQUESTED')", name="hr_status_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False, index=True)
    kyc_check_id: Mapped[UUID] = mapped_column(ForeignKey("kyc_checks.id"), nullable=False, index=True)
    reviewer_id: Mapped[UUID | None] = mapped_column()
    reviewer_role: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    evidence_packet: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    decision: Mapped[str | None] = mapped_column(String(30))
    decision_notes: Mapped[str | None] = mapped_column(Text)
    escalation_reason: Mapped[str | None] = mapped_column(Text)
    assigned_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column()
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="human_reviews")
    kyc_check: Mapped[KYCCheck] = relationship("KYCCheck", back_populates="human_reviews")
