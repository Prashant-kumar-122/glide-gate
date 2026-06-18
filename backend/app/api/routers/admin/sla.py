from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.permission_guard import require_permission
from app.api.error_handlers import ConflictError, NotFoundError, UnprocessableError
from app.database import get_db
from app.models.domain import Domain, DomainStageSLA
from app.models.cases import OnboardingCase
from app.models.sla import CaseSlaTracking
from app.services.audit.audit_event_types import AuditEventType
from app.services.audit.decision_log_service import DecisionLogEntry, decision_log_service

router = APIRouter(prefix="/admin", tags=["admin"])

_REGULATED_STAGES = {"KYC", "REVIEW", "SALES_REVIEW", "ESCALATED"}


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


# ── SLA models ────────────────────────────────────────────────────────────────

class SLAOut(BaseModel):
    id: str
    domain_id: str
    stage_code: str
    priority_tier: str | None
    product_code: str | None
    is_enabled: bool
    window_hours: float
    warning_pct: int
    escalation_pct: int
    warning_task_type: str
    escalation_task_type: str
    escalation_target_agent: str
    pause_on_human_review: bool


class SLACreate(BaseModel):
    stage_code: str = Field(..., min_length=1, max_length=50)
    priority_tier: str | None = Field(None, max_length=50)
    product_code: str | None = Field(None, max_length=50)
    is_enabled: bool = True
    window_hours: float = Field(..., gt=0)
    warning_pct: int = Field(80, ge=1, le=99)
    escalation_pct: int = Field(100, ge=2, le=200)
    warning_task_type: str = Field("SEND_SLA_WARNING", max_length=100)
    escalation_task_type: str = Field("SEND_ESCALATION_ALERT", max_length=100)
    escalation_target_agent: str = Field("orchestrator", max_length=100)
    pause_on_human_review: bool = False

    @model_validator(mode="after")
    def pct_order(self) -> "SLACreate":
        if self.warning_pct >= self.escalation_pct:
            raise ValueError("warning_pct must be less than escalation_pct")
        return self


class SLAUpdate(BaseModel):
    is_enabled: bool | None = None
    window_hours: float | None = Field(None, gt=0)
    warning_pct: int | None = Field(None, ge=1, le=99)
    escalation_pct: int | None = Field(None, ge=2, le=200)
    warning_task_type: str | None = Field(None, max_length=100)
    escalation_task_type: str | None = Field(None, max_length=100)
    escalation_target_agent: str | None = Field(None, max_length=100)
    pause_on_human_review: bool | None = None

    @model_validator(mode="after")
    def pct_order(self) -> "SLAUpdate":
        if self.warning_pct is not None and self.escalation_pct is not None:
            if self.warning_pct >= self.escalation_pct:
                raise ValueError("warning_pct must be less than escalation_pct")
        return self


class SLAHealthEntry(BaseModel):
    case_id: str
    stage_code: str
    started_at: str
    net_elapsed_seconds: float
    window_hours: float | None
    warning_pct: int | None
    escalation_pct: int | None
    warning_sent: bool
    breach_triggered: bool
    pct_elapsed: float | None


def _sla_to_out(s: DomainStageSLA) -> SLAOut:
    return SLAOut(
        id=str(s.id), domain_id=str(s.domain_id),
        stage_code=s.stage_code, priority_tier=s.priority_tier,
        product_code=s.product_code, is_enabled=s.is_enabled,
        window_hours=float(s.window_hours), warning_pct=s.warning_pct,
        escalation_pct=s.escalation_pct, warning_task_type=s.warning_task_type,
        escalation_task_type=s.escalation_task_type,
        escalation_target_agent=s.escalation_target_agent,
        pause_on_human_review=s.pause_on_human_review,
    )


# ── SLA domain routes ─────────────────────────────────────────────────────────

@router.get("/domains/{domain_id}/slas", response_model=list[SLAOut])
async def list_slas(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[SLAOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainStageSLA)
        .where(DomainStageSLA.domain_id == domain_id)
        .order_by(DomainStageSLA.stage_code, DomainStageSLA.priority_tier, DomainStageSLA.product_code)
    )
    return [_sla_to_out(s) for s in result.scalars().all()]


@router.post("/domains/{domain_id}/slas", response_model=SLAOut, status_code=201)
async def create_sla(
    domain_id: UUID,
    body: SLACreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> SLAOut:
    await _get_domain_or_404(domain_id, db)

    existing = await db.execute(
        select(DomainStageSLA).where(
            DomainStageSLA.domain_id == domain_id,
            DomainStageSLA.stage_code == body.stage_code,
            DomainStageSLA.priority_tier == body.priority_tier,
            DomainStageSLA.product_code == body.product_code,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            f"SLA for stage '{body.stage_code}' "
            f"(tier={body.priority_tier!r}, product={body.product_code!r}) "
            "already exists in this domain"
        )

    row = DomainStageSLA(
        domain_id=domain_id,
        stage_code=body.stage_code,
        priority_tier=body.priority_tier,
        product_code=body.product_code,
        is_enabled=body.is_enabled,
        window_hours=body.window_hours,
        warning_pct=body.warning_pct,
        escalation_pct=body.escalation_pct,
        warning_task_type=body.warning_task_type,
        escalation_task_type=body.escalation_task_type,
        escalation_target_agent=body.escalation_target_agent,
        pause_on_human_review=body.pause_on_human_review,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    out = _sla_to_out(row)
    await db.commit()
    await _log("sla_created", {"domain_id": str(domain_id), "stage_code": body.stage_code})
    return out


@router.put("/domains/{domain_id}/slas/{sla_id}", response_model=SLAOut)
async def update_sla(
    domain_id: UUID,
    sla_id: UUID,
    body: SLAUpdate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> SLAOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainStageSLA).where(
            DomainStageSLA.id == sla_id,
            DomainStageSLA.domain_id == domain_id,
        )
    )
    sla = result.scalar_one_or_none()
    if not sla:
        raise NotFoundError(f"SLA {sla_id} not found in domain {domain_id}")

    if body.is_enabled is False and sla.stage_code in _REGULATED_STAGES:
        raise UnprocessableError(
            f"Disabling SLA on regulated stage '{sla.stage_code}' requires explicit confirmation. "
            "Use the force_disable=true query parameter to confirm."
        )

    # Validate pct ordering considering current values
    eff_warning = body.warning_pct if body.warning_pct is not None else sla.warning_pct
    eff_escalation = body.escalation_pct if body.escalation_pct is not None else sla.escalation_pct
    if eff_warning >= eff_escalation:
        raise UnprocessableError("warning_pct must be less than escalation_pct")

    if body.is_enabled is not None:
        sla.is_enabled = body.is_enabled
    if body.window_hours is not None:
        sla.window_hours = body.window_hours
    if body.warning_pct is not None:
        sla.warning_pct = body.warning_pct
    if body.escalation_pct is not None:
        sla.escalation_pct = body.escalation_pct
    if body.warning_task_type is not None:
        sla.warning_task_type = body.warning_task_type
    if body.escalation_task_type is not None:
        sla.escalation_task_type = body.escalation_task_type
    if body.escalation_target_agent is not None:
        sla.escalation_target_agent = body.escalation_target_agent
    if body.pause_on_human_review is not None:
        sla.pause_on_human_review = body.pause_on_human_review

    await db.flush()
    await db.refresh(sla)
    out = _sla_to_out(sla)
    await db.commit()
    await _log("sla_updated", {"domain_id": str(domain_id), "sla_id": str(sla_id)})
    return out


@router.delete("/domains/{domain_id}/slas/{sla_id}", status_code=204)
async def delete_sla(
    domain_id: UUID,
    sla_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainStageSLA).where(
            DomainStageSLA.id == sla_id,
            DomainStageSLA.domain_id == domain_id,
        )
    )
    sla = result.scalar_one_or_none()
    if not sla:
        raise NotFoundError(f"SLA {sla_id} not found in domain {domain_id}")
    await db.delete(sla)
    await db.commit()
    await _log("sla_deleted", {"domain_id": str(domain_id), "sla_id": str(sla_id)})
    return Response(status_code=204)


# ── SLA health dashboard ──────────────────────────────────────────────────────

@router.get("/sla-health", response_model=list[SLAHealthEntry])
async def sla_health(
    domain_code: str = "wealth_management",
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[SLAHealthEntry]:
    """Return active SLA tracking rows with elapsed percentage for the health dashboard."""
    from app.services.sla.sla_monitor_service import SLAMonitorService

    sla_monitor = SLAMonitorService()

    tracking_result = await db.execute(
        select(CaseSlaTracking)
        .where(CaseSlaTracking.breach_triggered_at.is_(None))
        .order_by(CaseSlaTracking.started_at.asc())
    )
    tracking_rows = tracking_result.scalars().all()

    entries: list[SLAHealthEntry] = []
    for row in tracking_rows:
        elapsed = await sla_monitor.get_net_elapsed_seconds(db, row.id)

        domain_result = await db.execute(select(Domain).where(Domain.domain_code == domain_code))
        domain = domain_result.scalar_one_or_none()

        sla_spec = None
        case_result = await db.execute(
            select(OnboardingCase).where(OnboardingCase.id == row.case_id)
        )
        case = case_result.scalar_one_or_none()
        if domain and case:
            priority_tier = case.priority_tier if hasattr(case, "priority_tier") else None
            sla_spec = await sla_monitor.resolve_sla(db, domain_code, row.stage_code, priority_tier, None)

        pct_elapsed: float | None = None
        if sla_spec and sla_spec.window_hours and elapsed is not None:
            window_secs = sla_spec.window_hours * 3600
            pct_elapsed = round((elapsed / window_secs) * 100, 1) if window_secs > 0 else None

        entries.append(SLAHealthEntry(
            case_id=str(row.case_id),
            stage_code=row.stage_code,
            started_at=row.started_at.isoformat(),
            net_elapsed_seconds=elapsed or 0.0,
            window_hours=float(sla_spec.window_hours) if sla_spec else None,
            warning_pct=sla_spec.warning_pct if sla_spec else None,
            escalation_pct=sla_spec.escalation_pct if sla_spec else None,
            warning_sent=row.warning_sent_at is not None,
            breach_triggered=row.breach_triggered_at is not None,
            pct_elapsed=pct_elapsed,
        ))

    return entries
