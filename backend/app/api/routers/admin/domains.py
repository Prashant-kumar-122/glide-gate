from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.permission_guard import require_permission
from app.api.error_handlers import ConflictError, NotFoundError, UnprocessableError
from app.database import get_db
from app.domain.domain_definition import DomainDefinitionLoader, DomainValidationError
from app.models.domain import Domain
from app.services.audit.audit_event_types import AuditEventType
from app.services.audit.decision_log_service import DecisionLogEntry, decision_log_service

router = APIRouter(prefix="/admin/domains", tags=["admin"])


# ── Request / Response models ─────────────────────────────────────────────────

class DomainOut(BaseModel):
    id: str
    domain_code: str
    display_name: str
    is_active: bool
    created_at: str
    updated_at: str


class DomainCreate(BaseModel):
    domain_code: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9_]+$")
    display_name: str = Field(..., min_length=1, max_length=200)
    is_active: bool = False


class DomainUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=200)
    is_active: bool | None = None


class DomainValidationResult(BaseModel):
    valid: bool
    errors: list[str]


def _to_out(d: Domain) -> DomainOut:
    return DomainOut(
        id=str(d.id),
        domain_code=d.domain_code,
        display_name=d.display_name,
        is_active=d.is_active,
        created_at=d.created_at.isoformat(),
        updated_at=d.updated_at.isoformat(),
    )


async def _log_config_change(
    action: str,
    payload: dict[str, Any],
    db: AsyncSession,
) -> None:
    entry = DecisionLogEntry(
        agent_id="admin_portal",
        event_type=AuditEventType.CONFIG_CHANGE,
        payload={"action": action, **payload},
    )
    await decision_log_service.append(entry)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[DomainOut])
async def list_domains(
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[DomainOut]:
    result = await db.execute(select(Domain).order_by(Domain.domain_code))
    return [_to_out(d) for d in result.scalars().all()]


@router.post("", response_model=DomainOut, status_code=201)
async def create_domain(
    body: DomainCreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> DomainOut:
    existing = await db.execute(
        select(Domain).where(Domain.domain_code == body.domain_code)
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Domain '{body.domain_code}' already exists")

    domain = Domain(
        domain_code=body.domain_code,
        display_name=body.display_name,
        is_active=body.is_active,
    )
    db.add(domain)
    await db.flush()
    await db.refresh(domain)
    out = _to_out(domain)
    await db.commit()

    await _log_config_change(
        "domain_created",
        {"domain_code": body.domain_code, "display_name": body.display_name},
        db,
    )
    return out


@router.get("/{domain_id}", response_model=DomainOut)
async def get_domain(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> DomainOut:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    if not domain:
        raise NotFoundError(f"Domain {domain_id} not found")
    return _to_out(domain)


@router.put("/{domain_id}", response_model=DomainOut)
async def update_domain(
    domain_id: UUID,
    body: DomainUpdate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> DomainOut:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    if not domain:
        raise NotFoundError(f"Domain {domain_id} not found")

    if body.display_name is not None:
        domain.display_name = body.display_name
    if body.is_active is not None:
        domain.is_active = body.is_active

    await db.flush()
    await db.refresh(domain)
    out = _to_out(domain)
    await db.commit()

    await _log_config_change(
        "domain_updated",
        {"domain_id": str(domain_id), **body.model_dump(exclude_none=True)},
        db,
    )
    return out


@router.delete("/{domain_id}", status_code=204)
async def delete_domain(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    if not domain:
        raise NotFoundError(f"Domain {domain_id} not found")

    domain_code = domain.domain_code
    await db.delete(domain)
    await db.commit()

    await _log_config_change("domain_deleted", {"domain_id": str(domain_id), "domain_code": domain_code}, db)
    return Response(status_code=204)


@router.post("/{domain_id}/validate", response_model=DomainValidationResult)
async def validate_domain(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> DomainValidationResult:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    if not result.scalar_one_or_none():
        raise NotFoundError(f"Domain {domain_id} not found")

    try:
        loader = DomainDefinitionLoader(db)
        await loader.load(str(domain_id))
        return DomainValidationResult(valid=True, errors=[])
    except DomainValidationError as exc:
        return DomainValidationResult(valid=False, errors=[str(exc)])
    except Exception as exc:  # noqa: BLE001
        return DomainValidationResult(valid=False, errors=[str(exc)])


@router.post("/{domain_id}/activate", response_model=DomainOut)
async def activate_domain(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> DomainOut:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    if not domain:
        raise NotFoundError(f"Domain {domain_id} not found")

    try:
        loader = DomainDefinitionLoader(db)
        await loader.load(str(domain_id))
    except DomainValidationError as exc:
        raise UnprocessableError(f"Domain validation failed: {exc}") from exc
    except Exception as exc:
        raise UnprocessableError(f"Domain cannot be activated: {exc}") from exc

    # Enforce single active domain — deactivate all others first
    await db.execute(
        update(Domain).where(Domain.id != domain_id).values(is_active=False)
    )
    domain.is_active = True
    await db.flush()
    await db.refresh(domain)
    out = _to_out(domain)
    await db.commit()

    await _log_config_change("domain_activated", {"domain_id": str(domain_id), "domain_code": domain.domain_code}, db)
    return out


@router.post("/{domain_id}/deactivate", response_model=DomainOut)
async def deactivate_domain(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> DomainOut:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    if not domain:
        raise NotFoundError(f"Domain {domain_id} not found")

    domain.is_active = False
    await db.flush()
    await db.refresh(domain)
    out = _to_out(domain)
    await db.commit()

    await _log_config_change("domain_deactivated", {"domain_id": str(domain_id), "domain_code": domain.domain_code}, db)
    return out
