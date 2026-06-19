"""GET /config/domain — serves domain display vocabulary to the frontend (Phase 10).

Returns stage labels/styles, persona colors/routes/nav-links, and the active
product catalog.  No auth required — display config contains no sensitive data
and must be available before login completes (the nav bar renders immediately).

Static wealth-domain fallback values are returned when:
  - No active domain exists (fresh deployment, migration not yet run)
  - A stage/persona has no corresponding domain_display_config row
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.domain import (
    Domain,
    DomainDisplayConfig,
    DomainPersona,
    DomainProduct,
    DomainStage,
)

router = APIRouter(prefix="/config", tags=["config"])

# ── Static fallback (wealth domain defaults, used when DB has no display rows) ──

_STAGE_FALLBACK: dict[str, dict[str, Any]] = {
    "INTAKE":            {"label": "Intake",         "color": "#9CA3AF", "style": {"badge": "text-gray-400",   "dot": "bg-gray-500",   "optionDot": "bg-gray-400"}},
    "KYC":               {"label": "KYC",            "color": "#3B82F6", "style": {"badge": "text-blue-400",   "dot": "bg-blue-500",   "optionDot": "bg-blue-400"}},
    "PARALLEL_PRODUCTS": {"label": "Products",       "color": "#8B5CF6", "style": {"badge": "text-violet-400", "dot": "bg-violet-500", "optionDot": "bg-violet-400"}},
    "REVIEW":            {"label": "Advisor Review", "color": "#F59E0B", "style": {"badge": "text-amber-400",  "dot": "bg-amber-500",  "optionDot": "bg-amber-400"}},
    "SALES_REVIEW":      {"label": "Sales Review",   "color": "#F59E0B", "style": {"badge": "text-amber-400",  "dot": "bg-amber-500",  "optionDot": "bg-amber-400"}},
    "COMPLETE":          {"label": "Live",           "color": "#10B981", "style": {"badge": "text-green-400",  "dot": "bg-green-500",  "optionDot": "bg-green-400"}},
    "ESCALATED":         {"label": "Escalated",      "color": "#EF4444", "style": {"badge": "text-red-400",    "dot": "bg-red-500",    "optionDot": "bg-red-400"}},
}

_PERSONA_FALLBACK: dict[str, dict[str, Any]] = {
    "advisor":            {"label": "Financial Advisor",  "color": "#3B82F6", "default_route": "/",       "nav_links": []},
    "sales_manager":      {"label": "Sales Manager",      "color": "#F59E0B", "default_route": "/",       "nav_links": []},
    "admin":              {"label": "Administrator",       "color": "#8B5CF6", "default_route": "/admin",  "nav_links": []},
    "client":             {"label": "Client",              "color": "#10B981", "default_route": "/client", "nav_links": []},
    "compliance_officer": {"label": "Compliance Officer",  "color": "#8B5CF6", "default_route": "/",       "nav_links": []},
}


# ── Response models ────────────────────────────────────────────────────────────


class StageConfigOut(BaseModel):
    code: str
    label: str
    color: str = "#000000"
    style: dict[str, Any] = {}
    is_terminal: bool = False
    is_human_pending: bool = False


class PersonaConfigOut(BaseModel):
    code: str
    label: str
    color: str = "#000000"
    default_route: str = "/"
    nav_links: list[Any] = []


class ProductConfigOut(BaseModel):
    code: str
    display_name: str
    product_type: str = "retail"
    is_active: bool = True


class DomainConfigOut(BaseModel):
    domain_code: str
    display_name: str
    stages: list[StageConfigOut]
    personas: list[PersonaConfigOut]
    products: list[ProductConfigOut]


# ── Static fallback response (no active domain in DB) ─────────────────────────

def _fallback_config() -> DomainConfigOut:
    return DomainConfigOut(
        domain_code="wealth_management",
        display_name="Wealth Management",
        stages=[
            StageConfigOut(code=code, **vals)
            for code, vals in _STAGE_FALLBACK.items()
        ],
        personas=[
            PersonaConfigOut(code=code, **vals)
            for code, vals in _PERSONA_FALLBACK.items()
        ],
        products=[],
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.get("/domain", response_model=DomainConfigOut)
async def get_domain_config(db: AsyncSession = Depends(get_db)) -> DomainConfigOut:
    """Return display vocabulary for the currently active domain.

    Stages are enriched with label/color/style from domain_display_config rows
    where entity_type='stage'.  Missing display rows fall back to the static
    wealth-domain defaults embedded above.
    """
    domain = await db.scalar(
        select(Domain).where(Domain.is_active.is_(True)).limit(1)
    )
    if domain is None:
        return _fallback_config()

    domain_id = domain.id

    # ── Stages ────────────────────────────────────────────────────────────────
    stage_rows = (await db.scalars(
        select(DomainStage).where(DomainStage.domain_id == domain_id)
    )).all()

    display_rows = (await db.scalars(
        select(DomainDisplayConfig)
        .where(DomainDisplayConfig.domain_id == domain_id)
        .where(DomainDisplayConfig.entity_type == "stage")
    )).all()
    display_by_code: dict[str, DomainDisplayConfig] = {r.entity_code: r for r in display_rows}

    stages: list[StageConfigOut] = []
    for s in stage_rows:
        dc = display_by_code.get(s.stage_code)
        fb = _STAGE_FALLBACK.get(s.stage_code, {})
        stages.append(StageConfigOut(
            code=s.stage_code,
            label=dc.label if dc else fb.get("label", s.display_name),
            color=dc.color if dc else fb.get("color", "#000000"),
            style=(dc.style or {}) if dc else fb.get("style", {}),
            is_terminal=s.is_terminal,
            is_human_pending=s.is_human_pending,
        ))

    # ── Personas ──────────────────────────────────────────────────────────────
    persona_rows = (await db.scalars(
        select(DomainPersona).where(DomainPersona.domain_id == domain_id)
    )).all()
    personas: list[PersonaConfigOut] = [
        PersonaConfigOut(
            code=p.persona_code,
            label=p.display_label,
            color=p.color,
            default_route=p.default_route,
            nav_links=list(p.nav_links or []),
        )
        for p in persona_rows
    ]
    if not personas:
        personas = [PersonaConfigOut(code=code, **vals) for code, vals in _PERSONA_FALLBACK.items()]

    # ── Products ──────────────────────────────────────────────────────────────
    product_rows = (await db.scalars(
        select(DomainProduct)
        .where(DomainProduct.domain_id == domain_id)
        .where(DomainProduct.is_active.is_(True))
        .order_by(DomainProduct.display_name)
    )).all()
    products: list[ProductConfigOut] = [
        ProductConfigOut(
            code=p.product_code,
            display_name=p.display_name,
            product_type=p.product_type,
            is_active=p.is_active,
        )
        for p in product_rows
    ]

    return DomainConfigOut(
        domain_code=domain.domain_code,
        display_name=domain.display_name,
        stages=stages,
        personas=personas,
        products=products,
    )
