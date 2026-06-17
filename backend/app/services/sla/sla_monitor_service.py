"""SLAMonitorService — DB operations for case SLA tracking (Phase 5).

Responsibilities:
  - Resolve the best-matching domain_stage_slas row for a given
    (domain_code, stage_code, priority_tier, product_code) using the
    priority chain: most-specific → least-specific.
  - Write and update case_sla_tracking rows as stages are entered,
    paused, resumed, and breached.
  - All methods use the provided AsyncSession; callers must commit.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.domain_definition import SLASpec
from app.models.sla import CaseSlaTracking


class SLAMonitorService:
    """Thin DB-access layer for SLA tracking; no I/O beyond SQLAlchemy."""

    # ── SLA resolution ────────────────────────────────────────────────────────

    async def resolve_sla(
        self,
        db: AsyncSession,
        domain_code: str,
        stage_code: str,
        priority_tier: str | None = None,
        product_code: str | None = None,
    ) -> SLASpec | None:
        """Return the best-matching SLASpec for the given axes, or None.

        Priority chain (most specific wins):
          1. stage + priority_tier + product_code
          2. stage + priority_tier + NULL product_code
          3. stage + NULL priority_tier + product_code
          4. stage + NULL priority_tier + NULL product_code
        Returns None if no row is found or the matching row has is_enabled=False.
        """
        from app.models.domain import DomainStageSLA, Domain

        domain_row = await db.scalar(
            select(Domain).where(Domain.domain_code == domain_code)
        )
        if domain_row is None:
            return None

        domain_id = domain_row.id

        # Build candidate filters in priority order
        candidates: list[tuple[Any, Any]] = [
            (priority_tier, product_code),
            (priority_tier, None),
            (None, product_code),
            (None, None),
        ]
        # Deduplicate while preserving order
        seen: set[tuple] = set()
        unique_candidates: list[tuple[Any, Any]] = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        for pt, pc in unique_candidates:
            stmt = select(DomainStageSLA).where(
                DomainStageSLA.domain_id == domain_id,
                DomainStageSLA.stage_code == stage_code,
                DomainStageSLA.priority_tier == pt,
                DomainStageSLA.product_code == pc,
            )
            row = await db.scalar(stmt)
            if row is not None:
                if not row.is_enabled:
                    return None  # explicitly disabled
                return SLASpec(
                    stage_code=row.stage_code,
                    priority_tier=row.priority_tier,
                    product_code=row.product_code,
                    is_enabled=row.is_enabled,
                    window_hours=float(row.window_hours),
                    warning_pct=row.warning_pct,
                    escalation_pct=row.escalation_pct,
                    warning_task_type=row.warning_task_type,
                    escalation_task_type=row.escalation_task_type,
                    escalation_target_agent=row.escalation_target_agent,
                    pause_on_human_review=row.pause_on_human_review,
                )
        return None

    # ── Tracking lifecycle ────────────────────────────────────────────────────

    async def start_tracking(
        self,
        db: AsyncSession,
        case_id: UUID,
        stage_code: str,
        sla_spec: SLASpec,
        priority_tier: str | None = None,
        product_code: str | None = None,
    ) -> CaseSlaTracking:
        """Write a new case_sla_tracking row.  Caller must commit."""
        now = datetime.now(timezone.utc)
        row = CaseSlaTracking(
            case_id=case_id,
            stage_code=stage_code,
            window_hours=sla_spec.window_hours,
            warning_pct=sla_spec.warning_pct,
            escalation_pct=sla_spec.escalation_pct,
            warning_task_type=sla_spec.warning_task_type,
            escalation_task_type=sla_spec.escalation_task_type,
            escalation_target_agent=sla_spec.escalation_target_agent,
            pause_on_human_review=sla_spec.pause_on_human_review,
            priority_tier=priority_tier,
            product_code=product_code,
            is_enabled=sla_spec.is_enabled,
            started_at=now,
            paused_duration_seconds=0.0,
        )
        db.add(row)
        return row

    async def pause_tracking(
        self,
        db: AsyncSession,
        case_id: UUID,
        stage_code: str,
    ) -> None:
        """Set paused_at to now.  Caller must commit."""
        now = datetime.now(timezone.utc)
        await db.execute(
            sa_update(CaseSlaTracking)
            .where(
                CaseSlaTracking.case_id == case_id,
                CaseSlaTracking.stage_code == stage_code,
                CaseSlaTracking.paused_at.is_(None),
            )
            .values(paused_at=now)
        )

    async def resume_tracking(
        self,
        db: AsyncSession,
        case_id: UUID,
        stage_code: str,
    ) -> float:
        """Accumulate paused_duration_seconds; clear paused_at.
        Returns elapsed_active_seconds at the time of resumption."""
        now = datetime.now(timezone.utc)
        row = await db.scalar(
            select(CaseSlaTracking).where(
                CaseSlaTracking.case_id == case_id,
                CaseSlaTracking.stage_code == stage_code,
            )
        )
        if row is None:
            return 0.0

        added_pause: float = 0.0
        if row.paused_at is not None:
            added_pause = (now - row.paused_at).total_seconds()

        new_paused = row.paused_duration_seconds + added_pause
        total_elapsed = (now - row.started_at).total_seconds()
        active_elapsed = total_elapsed - new_paused

        await db.execute(
            sa_update(CaseSlaTracking)
            .where(
                CaseSlaTracking.case_id == case_id,
                CaseSlaTracking.stage_code == stage_code,
            )
            .values(paused_at=None, paused_duration_seconds=new_paused)
        )
        return max(0.0, active_elapsed)

    async def record_warning_sent(
        self,
        db: AsyncSession,
        case_id: UUID,
        stage_code: str,
    ) -> bool:
        """Set warning_sent_at.  Returns False if already set (idempotent)."""
        row = await db.scalar(
            select(CaseSlaTracking).where(
                CaseSlaTracking.case_id == case_id,
                CaseSlaTracking.stage_code == stage_code,
            )
        )
        if row is None or row.warning_sent_at is not None:
            return False
        await db.execute(
            sa_update(CaseSlaTracking)
            .where(
                CaseSlaTracking.case_id == case_id,
                CaseSlaTracking.stage_code == stage_code,
            )
            .values(warning_sent_at=datetime.now(timezone.utc))
        )
        return True

    async def record_breach_triggered(
        self,
        db: AsyncSession,
        case_id: UUID,
        stage_code: str,
    ) -> bool:
        """Set breach_triggered_at.  Returns False if already set (idempotent)."""
        row = await db.scalar(
            select(CaseSlaTracking).where(
                CaseSlaTracking.case_id == case_id,
                CaseSlaTracking.stage_code == stage_code,
            )
        )
        if row is None or row.breach_triggered_at is not None:
            return False
        await db.execute(
            sa_update(CaseSlaTracking)
            .where(
                CaseSlaTracking.case_id == case_id,
                CaseSlaTracking.stage_code == stage_code,
            )
            .values(breach_triggered_at=datetime.now(timezone.utc))
        )
        return True

    async def get_net_elapsed_seconds(
        self,
        db: AsyncSession,
        case_id: UUID,
        stage_code: str,
    ) -> float:
        """Return net active seconds (total elapsed − accumulated pause duration)."""
        row = await db.scalar(
            select(CaseSlaTracking).where(
                CaseSlaTracking.case_id == case_id,
                CaseSlaTracking.stage_code == stage_code,
            )
        )
        if row is None:
            return 0.0
        now = datetime.now(timezone.utc)
        total = (now - row.started_at).total_seconds()
        paused = row.paused_duration_seconds
        if row.paused_at is not None:
            paused += (now - row.paused_at).total_seconds()
        return max(0.0, total - paused)


sla_monitor_service = SLAMonitorService()
