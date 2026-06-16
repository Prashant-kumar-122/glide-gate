"""ORM model for case_sla_tracking (Phase 5)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CaseSlaTracking(Base):
    """Per-stage SLA clock for one onboarding case.

    One row per (case_id, stage_code).  Created when a stage is entered;
    paused/resumed around human-review waits; warning_sent_at / breach_triggered_at
    set by the corresponding Temporal activities.
    """

    __tablename__ = "case_sla_tracking"
    __table_args__ = (
        UniqueConstraint("case_id", "stage_code", name="case_sla_tracking_uq"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("onboarding_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Resolved SLA config (snapshot at stage entry)
    window_hours: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    warning_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    escalation_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    warning_task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    escalation_task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    escalation_target_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    pause_on_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Axis keys used for resolution (informational)
    priority_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    product_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Clock state
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Event timestamps
    warning_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    breach_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
