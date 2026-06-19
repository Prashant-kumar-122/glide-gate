from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.permission_guard import require_permission
from app.api.error_handlers import ConflictError, NotFoundError
from app.database import get_db
from app.models.domain import Domain, DomainPersona, DomainPermission
from app.services.audit.audit_event_types import AuditEventType
from app.services.audit.decision_log_service import DecisionLogEntry, decision_log_service

router = APIRouter(prefix="/admin/domains", tags=["admin"])

_KNOWN_SCOPES = {
    "case:read", "case:create", "case:approve",
    "review:read", "review:approve", "review:escalate",
    "sales:review", "sales:decide",
    "compliance:read", "compliance:decide",
    "audit:read", "audit:export",
    "document:upload", "document:validate",
    "admin:config",
}


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


# ── Persona models ────────────────────────────────────────────────────────────

class PersonaOut(BaseModel):
    id: str
    domain_id: str
    persona_code: str
    display_label: str
    color: str
    default_route: str
    nav_links: list[Any]


class PersonaCreate(BaseModel):
    persona_code: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9_]+$")
    display_label: str = Field(..., min_length=1, max_length=200)
    color: str = Field("#000000", max_length=50)
    default_route: str = Field("/", max_length=255)
    nav_links: list[Any] = []


class PersonaUpdate(BaseModel):
    display_label: str | None = Field(None, min_length=1, max_length=200)
    color: str | None = Field(None, max_length=50)
    default_route: str | None = Field(None, max_length=255)
    nav_links: list[Any] | None = None


# ── Permission models ─────────────────────────────────────────────────────────

class PermissionOut(BaseModel):
    id: str
    domain_id: str
    persona_code: str
    permission_scope: str


class PermissionCreate(BaseModel):
    permission_scope: str = Field(..., min_length=1, max_length=100)


class KnownScopesOut(BaseModel):
    scopes: list[str]


def _persona_to_out(p: DomainPersona) -> PersonaOut:
    return PersonaOut(
        id=str(p.id), domain_id=str(p.domain_id),
        persona_code=p.persona_code, display_label=p.display_label,
        color=p.color, default_route=p.default_route, nav_links=p.nav_links,
    )


# ── Persona routes ────────────────────────────────────────────────────────────

@router.get("/{domain_id}/personas", response_model=list[PersonaOut])
async def list_personas(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[PersonaOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainPersona)
        .where(DomainPersona.domain_id == domain_id)
        .order_by(DomainPersona.persona_code)
    )
    return [_persona_to_out(p) for p in result.scalars().all()]


@router.post("/{domain_id}/personas", response_model=PersonaOut, status_code=201)
async def create_persona(
    domain_id: UUID,
    body: PersonaCreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> PersonaOut:
    await _get_domain_or_404(domain_id, db)
    existing = await db.execute(
        select(DomainPersona).where(
            DomainPersona.domain_id == domain_id,
            DomainPersona.persona_code == body.persona_code,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Persona '{body.persona_code}' already exists in domain")

    persona = DomainPersona(
        domain_id=domain_id,
        persona_code=body.persona_code,
        display_label=body.display_label,
        color=body.color,
        default_route=body.default_route,
        nav_links=body.nav_links,
    )
    db.add(persona)
    await db.flush()
    await db.refresh(persona)
    out = _persona_to_out(persona)
    await db.commit()
    await _log("persona_created", {"domain_id": str(domain_id), "persona_code": body.persona_code})
    return out


@router.put("/{domain_id}/personas/{persona_id}", response_model=PersonaOut)
async def update_persona(
    domain_id: UUID,
    persona_id: UUID,
    body: PersonaUpdate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> PersonaOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainPersona).where(
            DomainPersona.id == persona_id,
            DomainPersona.domain_id == domain_id,
        )
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise NotFoundError(f"Persona {persona_id} not found in domain {domain_id}")

    if body.display_label is not None:
        persona.display_label = body.display_label
    if body.color is not None:
        persona.color = body.color
    if body.default_route is not None:
        persona.default_route = body.default_route
    if body.nav_links is not None:
        persona.nav_links = body.nav_links

    await db.flush()
    await db.refresh(persona)
    out = _persona_to_out(persona)
    await db.commit()
    await _log("persona_updated", {"domain_id": str(domain_id), "persona_id": str(persona_id)})
    return out


@router.delete("/{domain_id}/personas/{persona_id}", status_code=204)
async def delete_persona(
    domain_id: UUID,
    persona_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainPersona).where(
            DomainPersona.id == persona_id,
            DomainPersona.domain_id == domain_id,
        )
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise NotFoundError(f"Persona {persona_id} not found in domain {domain_id}")
    persona_code = persona.persona_code
    await db.delete(persona)
    await db.commit()
    await _log("persona_deleted", {"domain_id": str(domain_id), "persona_code": persona_code})
    return Response(status_code=204)


# ── Permission routes ─────────────────────────────────────────────────────────

@router.get("/{domain_id}/personas/{persona_code}/permissions", response_model=list[PermissionOut])
async def list_permissions(
    domain_id: UUID,
    persona_code: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[PermissionOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainPermission).where(
            DomainPermission.domain_id == domain_id,
            DomainPermission.persona_code == persona_code,
        ).order_by(DomainPermission.permission_scope)
    )
    return [
        PermissionOut(
            id=str(p.id), domain_id=str(p.domain_id),
            persona_code=p.persona_code, permission_scope=p.permission_scope,
        )
        for p in result.scalars().all()
    ]


@router.post("/{domain_id}/personas/{persona_code}/permissions", response_model=PermissionOut, status_code=201)
async def add_permission(
    domain_id: UUID,
    persona_code: str,
    body: PermissionCreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> PermissionOut:
    await _get_domain_or_404(domain_id, db)
    existing = await db.execute(
        select(DomainPermission).where(
            DomainPermission.domain_id == domain_id,
            DomainPermission.persona_code == persona_code,
            DomainPermission.permission_scope == body.permission_scope,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Permission '{body.permission_scope}' already granted to '{persona_code}'")

    perm = DomainPermission(
        domain_id=domain_id,
        persona_code=persona_code,
        permission_scope=body.permission_scope,
    )
    db.add(perm)
    await db.flush()
    await db.refresh(perm)
    out = PermissionOut(
        id=str(perm.id), domain_id=str(perm.domain_id),
        persona_code=perm.persona_code, permission_scope=perm.permission_scope,
    )
    await db.commit()
    await _log("permission_added", {
        "domain_id": str(domain_id), "persona_code": persona_code, "scope": body.permission_scope,
    })

    from app.api.dependencies.permission_guard import clear_permission_cache
    clear_permission_cache()
    return out


@router.delete("/{domain_id}/personas/{persona_code}/permissions/{scope}", status_code=204)
async def remove_permission(
    domain_id: UUID,
    persona_code: str,
    scope: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainPermission).where(
            DomainPermission.domain_id == domain_id,
            DomainPermission.persona_code == persona_code,
            DomainPermission.permission_scope == scope,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise NotFoundError(f"Permission '{scope}' not found for persona '{persona_code}'")
    await db.delete(perm)
    await db.commit()
    await _log("permission_removed", {
        "domain_id": str(domain_id), "persona_code": persona_code, "scope": scope,
    })

    from app.api.dependencies.permission_guard import clear_permission_cache
    clear_permission_cache()
    return Response(status_code=204)


@router.get("/{domain_id}/personas/known-scopes", response_model=KnownScopesOut)
async def list_known_scopes(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> KnownScopesOut:
    await _get_domain_or_404(domain_id, db)
    return KnownScopesOut(scopes=sorted(_KNOWN_SCOPES))
