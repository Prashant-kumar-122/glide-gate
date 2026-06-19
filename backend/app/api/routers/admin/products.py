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
from app.models.domain import Domain, DomainProduct, DomainProductPipeline
from app.services.audit.audit_event_types import AuditEventType
from app.services.audit.decision_log_service import DecisionLogEntry, decision_log_service

router = APIRouter(prefix="/admin/domains", tags=["admin"])


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


# ── Product models ────────────────────────────────────────────────────────────

class ProductOut(BaseModel):
    id: str
    domain_id: str
    product_code: str
    display_name: str
    description: str | None
    product_type: str
    is_active: bool
    suitability_criteria: dict[str, Any]
    required_documents: list[str]
    activation_criteria: dict[str, Any]
    extra_metadata: dict[str, Any]


class ProductCreate(BaseModel):
    product_code: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9_]+$")
    display_name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    product_type: str = Field("retail", max_length=50)
    is_active: bool = True
    suitability_criteria: dict[str, Any] = {}
    required_documents: list[str] = []
    activation_criteria: dict[str, Any] = {}
    extra_metadata: dict[str, Any] = {}


class ProductUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    product_type: str | None = Field(None, max_length=50)
    is_active: bool | None = None
    suitability_criteria: dict[str, Any] | None = None
    required_documents: list[str] | None = None
    activation_criteria: dict[str, Any] | None = None
    extra_metadata: dict[str, Any] | None = None


def _product_to_out(p: DomainProduct) -> ProductOut:
    return ProductOut(
        id=str(p.id), domain_id=str(p.domain_id),
        product_code=p.product_code, display_name=p.display_name,
        description=p.description,
        product_type=p.product_type, is_active=p.is_active,
        suitability_criteria=p.suitability_criteria,
        required_documents=p.required_documents,
        activation_criteria=p.activation_criteria,
        extra_metadata=p.extra_metadata,
    )


# ── Pipeline models ───────────────────────────────────────────────────────────

class PipelineStepOut(BaseModel):
    id: str
    domain_id: str
    product_code: str
    step_id: str
    step_label: str
    step_order: int
    is_parallel: bool
    step_config: dict[str, Any]


class PipelineStepCreate(BaseModel):
    step_id: str = Field(..., min_length=1, max_length=100)
    step_label: str = Field(..., min_length=1, max_length=200)
    step_order: int = Field(..., ge=0)
    is_parallel: bool = False
    step_config: dict[str, Any] = {}


class PipelineStepUpdate(BaseModel):
    step_label: str | None = Field(None, min_length=1, max_length=200)
    step_order: int | None = Field(None, ge=0)
    is_parallel: bool | None = None
    step_config: dict[str, Any] | None = None


class PipelineReorder(BaseModel):
    step_orders: dict[str, int] = Field(..., description="Map of step_id → new step_order")


def _step_to_out(s: DomainProductPipeline) -> PipelineStepOut:
    return PipelineStepOut(
        id=str(s.id), domain_id=str(s.domain_id),
        product_code=s.product_code, step_id=s.step_id,
        step_label=s.step_label, step_order=s.step_order,
        is_parallel=s.is_parallel, step_config=s.step_config,
    )


# ── Product routes ────────────────────────────────────────────────────────────

@router.get("/{domain_id}/products", response_model=list[ProductOut])
async def list_products(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[ProductOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainProduct)
        .where(DomainProduct.domain_id == domain_id)
        .order_by(DomainProduct.product_code)
    )
    return [_product_to_out(p) for p in result.scalars().all()]


@router.post("/{domain_id}/products", response_model=ProductOut, status_code=201)
async def create_product(
    domain_id: UUID,
    body: ProductCreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> ProductOut:
    await _get_domain_or_404(domain_id, db)
    existing = await db.execute(
        select(DomainProduct).where(
            DomainProduct.domain_id == domain_id,
            DomainProduct.product_code == body.product_code,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Product '{body.product_code}' already exists in domain")

    product = DomainProduct(
        domain_id=domain_id,
        product_code=body.product_code,
        display_name=body.display_name,
        description=body.description,
        product_type=body.product_type,
        is_active=body.is_active,
        suitability_criteria=body.suitability_criteria,
        required_documents=body.required_documents,
        activation_criteria=body.activation_criteria,
        extra_metadata=body.extra_metadata,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    out = _product_to_out(product)
    await db.commit()
    await _log("product_created", {"domain_id": str(domain_id), "product_code": body.product_code})
    return out


@router.put("/{domain_id}/products/{product_id}", response_model=ProductOut)
async def update_product(
    domain_id: UUID,
    product_id: UUID,
    body: ProductUpdate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> ProductOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainProduct).where(
            DomainProduct.id == product_id,
            DomainProduct.domain_id == domain_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError(f"Product {product_id} not found in domain {domain_id}")

    if body.display_name is not None:
        product.display_name = body.display_name
    if "description" in body.model_fields_set:
        product.description = body.description
    if body.product_type is not None:
        product.product_type = body.product_type
    if body.is_active is not None:
        product.is_active = body.is_active
    if body.suitability_criteria is not None:
        product.suitability_criteria = body.suitability_criteria
    if body.required_documents is not None:
        product.required_documents = body.required_documents
    if body.activation_criteria is not None:
        product.activation_criteria = body.activation_criteria
    if body.extra_metadata is not None:
        product.extra_metadata = body.extra_metadata

    await db.flush()
    await db.refresh(product)
    out = _product_to_out(product)
    await db.commit()
    await _log("product_updated", {"domain_id": str(domain_id), "product_id": str(product_id)})
    return out


@router.delete("/{domain_id}/products/{product_id}", status_code=204)
async def delete_product(
    domain_id: UUID,
    product_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainProduct).where(
            DomainProduct.id == product_id,
            DomainProduct.domain_id == domain_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError(f"Product {product_id} not found in domain {domain_id}")
    product_code = product.product_code
    await db.delete(product)
    await db.commit()
    await _log("product_deleted", {"domain_id": str(domain_id), "product_code": product_code})
    return Response(status_code=204)


# ── Pipeline routes ───────────────────────────────────────────────────────────

@router.get("/{domain_id}/products/{product_code}/pipeline", response_model=list[PipelineStepOut])
async def list_pipeline(
    domain_id: UUID,
    product_code: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[PipelineStepOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainProductPipeline)
        .where(
            DomainProductPipeline.domain_id == domain_id,
            DomainProductPipeline.product_code == product_code,
        )
        .order_by(DomainProductPipeline.step_order)
    )
    return [_step_to_out(s) for s in result.scalars().all()]


@router.post("/{domain_id}/products/{product_code}/pipeline", response_model=PipelineStepOut, status_code=201)
async def add_pipeline_step(
    domain_id: UUID,
    product_code: str,
    body: PipelineStepCreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> PipelineStepOut:
    await _get_domain_or_404(domain_id, db)
    existing = await db.execute(
        select(DomainProductPipeline).where(
            DomainProductPipeline.domain_id == domain_id,
            DomainProductPipeline.product_code == product_code,
            DomainProductPipeline.step_id == body.step_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Pipeline step '{body.step_id}' already exists for product '{product_code}'")

    step = DomainProductPipeline(
        domain_id=domain_id,
        product_code=product_code,
        step_id=body.step_id,
        step_label=body.step_label,
        step_order=body.step_order,
        is_parallel=body.is_parallel,
        step_config=body.step_config,
    )
    db.add(step)
    await db.flush()
    await db.refresh(step)
    out = _step_to_out(step)
    await db.commit()
    await _log("pipeline_step_added", {"domain_id": str(domain_id), "product_code": product_code, "step_id": body.step_id})
    return out


@router.put("/{domain_id}/products/{product_code}/pipeline/{step_id}", response_model=PipelineStepOut)
async def update_pipeline_step(
    domain_id: UUID,
    product_code: str,
    step_id: str,
    body: PipelineStepUpdate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> PipelineStepOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainProductPipeline).where(
            DomainProductPipeline.domain_id == domain_id,
            DomainProductPipeline.product_code == product_code,
            DomainProductPipeline.step_id == step_id,
        )
    )
    step = result.scalar_one_or_none()
    if not step:
        raise NotFoundError(f"Pipeline step '{step_id}' not found for product '{product_code}'")

    if body.step_label is not None:
        step.step_label = body.step_label
    if body.step_order is not None:
        step.step_order = body.step_order
    if body.is_parallel is not None:
        step.is_parallel = body.is_parallel
    if body.step_config is not None:
        step.step_config = body.step_config

    await db.flush()
    await db.refresh(step)
    out = _step_to_out(step)
    await db.commit()
    await _log("pipeline_step_updated", {"domain_id": str(domain_id), "product_code": product_code, "step_id": step_id})
    return out


@router.put("/{domain_id}/products/{product_code}/pipeline-reorder", response_model=list[PipelineStepOut])
async def reorder_pipeline(
    domain_id: UUID,
    product_code: str,
    body: PipelineReorder,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[PipelineStepOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainProductPipeline).where(
            DomainProductPipeline.domain_id == domain_id,
            DomainProductPipeline.product_code == product_code,
        )
    )
    steps = result.scalars().all()

    for step in steps:
        if step.step_id in body.step_orders:
            step.step_order = body.step_orders[step.step_id]

    await db.flush()
    result2 = await db.execute(
        select(DomainProductPipeline)
        .where(
            DomainProductPipeline.domain_id == domain_id,
            DomainProductPipeline.product_code == product_code,
        )
        .order_by(DomainProductPipeline.step_order)
    )
    out = [_step_to_out(s) for s in result2.scalars().all()]
    await db.commit()
    await _log("pipeline_reordered", {"domain_id": str(domain_id), "product_code": product_code})
    return out


@router.delete("/{domain_id}/products/{product_code}/pipeline/{step_id}", status_code=204)
async def delete_pipeline_step(
    domain_id: UUID,
    product_code: str,
    step_id: str,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainProductPipeline).where(
            DomainProductPipeline.domain_id == domain_id,
            DomainProductPipeline.product_code == product_code,
            DomainProductPipeline.step_id == step_id,
        )
    )
    step = result.scalar_one_or_none()
    if not step:
        raise NotFoundError(f"Pipeline step '{step_id}' not found for product '{product_code}'")
    await db.delete(step)
    await db.commit()
    await _log("pipeline_step_deleted", {"domain_id": str(domain_id), "product_code": product_code, "step_id": step_id})
    return Response(status_code=204)
