from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.role_guard import require_role
from app.api.error_handlers import ConflictError, NotFoundError
from app.database import get_db
from app.models.cases import CaseProduct, OnboardingCase, Product
from app.models.documents import Document
from app.services.orchestration.agent_orchestration_service import orchestration_service

router = APIRouter(prefix="/cases", tags=["cases"])


# ── Request / Response models ─────────────────────────────────────────────────

class InitiateCaseRequest(BaseModel):
    client_id: UUID
    selected_products: list[str]
    assigned_advisor_id: UUID | None = None
    metadata: dict[str, Any] = {}


class ProductTrackOut(BaseModel):
    id: UUID
    product_code: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class CaseSummaryOut(BaseModel):
    id: UUID
    client_id: UUID
    status: str
    current_stage: str
    selected_products: list[str]
    assigned_advisor_id: UUID | None
    created_at: datetime
    updated_at: datetime
    product_tracks: list[ProductTrackOut]

    model_config = {"from_attributes": True}


class CaseDetailOut(BaseModel):
    id: UUID
    client_id: UUID
    status: str
    current_stage: str
    selected_products: list[str]
    shared_context: dict[str, Any]
    assigned_advisor_id: UUID | None
    sla_deadline: datetime | None
    completed_at: datetime | None
    extra_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    product_tracks: list[ProductTrackOut]

    model_config = {"from_attributes": True}


class CaseProgressOut(BaseModel):
    case_id: UUID
    current_stage: str
    status: str
    documents_required: int
    documents_received: int
    documents_approved: int
    product_tracks: list[ProductTrackOut]
    kyc_status: str | None


class ResumeResponse(BaseModel):
    case_id: UUID
    message: str
    stage: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_case_or_404(case_id: UUID, db: AsyncSession) -> OnboardingCase:
    result = await db.execute(
        select(OnboardingCase)
        .options(selectinload(OnboardingCase.case_products))
        .where(OnboardingCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise NotFoundError("OnboardingCase", str(case_id))
    return case


def _case_products_to_tracks(case: OnboardingCase) -> list[ProductTrackOut]:
    return [ProductTrackOut.model_validate(cp) for cp in case.case_products]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=CaseSummaryOut)
async def initiate_case(
    body: InitiateCaseRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("Advisor", "Admin")),
) -> CaseSummaryOut:
    if not body.selected_products:
        raise ConflictError("At least one product must be selected")

    # Validate products exist
    product_rows = await db.execute(
        select(Product).where(Product.product_code.in_(body.selected_products))
    )
    products = product_rows.scalars().all()
    found_codes = {p.product_code for p in products}
    unknown = set(body.selected_products) - found_codes
    if unknown:
        raise ConflictError(f"Unknown product codes: {sorted(unknown)}")

    case = OnboardingCase(
        client_id=body.client_id,
        selected_products=body.selected_products,
        assigned_advisor_id=body.assigned_advisor_id,
        metadata=body.metadata,
    )
    db.add(case)
    await db.flush()

    for product in products:
        cp = CaseProduct(
            case_id=case.id,
            product_id=product.id,
            product_code=product.product_code,
        )
        db.add(cp)

    await db.commit()

    refreshed = await _get_case_or_404(case.id, db)

    # Kick off agent workflow asynchronously — the HTTP response is returned
    # immediately; the orchestrator runs in the background via asyncio.Task.
    asyncio.create_task(
        orchestration_service.start_onboarding(
            case_id=refreshed.id,
            client_id=refreshed.client_id,
            selected_products=refreshed.selected_products,
        )
    )

    return CaseSummaryOut(
        id=refreshed.id,
        client_id=refreshed.client_id,
        status=refreshed.status,
        current_stage=refreshed.current_stage,
        selected_products=refreshed.selected_products,
        assigned_advisor_id=refreshed.assigned_advisor_id,
        created_at=refreshed.created_at,
        updated_at=refreshed.updated_at,
        product_tracks=_case_products_to_tracks(refreshed),
    )


@router.get("/{case_id}", response_model=CaseDetailOut)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> CaseDetailOut:
    case = await _get_case_or_404(case_id, db)
    return CaseDetailOut(
        id=case.id,
        client_id=case.client_id,
        status=case.status,
        current_stage=case.current_stage,
        selected_products=case.selected_products,
        shared_context=case.shared_context,
        assigned_advisor_id=case.assigned_advisor_id,
        sla_deadline=case.sla_deadline,
        completed_at=case.completed_at,
        extra_metadata=case.extra_metadata,
        created_at=case.created_at,
        updated_at=case.updated_at,
        product_tracks=_case_products_to_tracks(case),
    )


@router.get("/{case_id}/summary", response_model=CaseProgressOut)
async def get_case_summary(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> CaseProgressOut:
    case = await _get_case_or_404(case_id, db)

    doc_result = await db.execute(
        select(Document.status).where(Document.case_id == case_id)
    )
    doc_statuses = doc_result.scalars().all()
    required = len(doc_statuses)
    received = sum(1 for s in doc_statuses if s not in ("NOT_REQUESTED", "REQUESTED"))
    approved = sum(1 for s in doc_statuses if s == "APPROVED")

    ctx = case.shared_context or {}
    return CaseProgressOut(
        case_id=case.id,
        current_stage=case.current_stage,
        status=case.status,
        documents_required=required,
        documents_received=received,
        documents_approved=approved,
        product_tracks=_case_products_to_tracks(case),
        kyc_status=ctx.get("kyc_status"),
    )


@router.post("/{case_id}/resume", status_code=status.HTTP_202_ACCEPTED, response_model=ResumeResponse)
async def resume_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("Advisor", "Admin")),
) -> ResumeResponse:
    case = await _get_case_or_404(case_id, db)
    asyncio.create_task(orchestration_service.resume_onboarding(case_id=case.id))
    return ResumeResponse(
        case_id=case.id,
        message="Resume request accepted — AgentOrchestrationService is re-routing the workflow",
        stage=case.current_stage,
    )
