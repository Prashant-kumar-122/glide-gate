from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SalesManagerReview(Base):
    """Human-in-the-loop review performed by the Sales Manager for institutional cases.

    Lifecycle:
      PENDING → APPROVED  → triggers KYC
      PENDING → REJECTED  → case moved back to REVIEW
      PENDING → MORE_INFO_REQUESTED → case moved back to REVIEW pending client action
    """

    __tablename__ = "sales_manager_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED','MORE_INFO_REQUESTED')",
            name="smr_status_chk",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("onboarding_cases.id"), nullable=False, index=True
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(index=True)
    reviewer_role: Mapped[str | None] = mapped_column(String(50))

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    decision: Mapped[str | None] = mapped_column(String(30))
    decision_notes: Mapped[str | None] = mapped_column(Text)

    # AI-generated risk summary presented to the SM on the review dashboard
    ai_risk_summary: Mapped[str | None] = mapped_column(Text)
    risk_score: Mapped[float | None] = mapped_column()

    # Structured data snapshot used to build the review dashboard
    case_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    assigned_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    decided_at: Mapped[datetime | None] = mapped_column()

    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="sales_manager_reviews")
