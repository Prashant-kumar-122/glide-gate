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
from app.models.cases import CaseProduct, CaseProductStep, OnboardingCase, Product
from app.models.clients import Client
from app.models.documents import Document
from app.services.orchestration.agent_orchestration_service import orchestration_service
from app.services.orchestration.journey_resumption_service import journey_resumption_service

router = APIRouter(prefix="/cases", tags=["cases"])


# ── Request / Response models ─────────────────────────────────────────────────

class InitiateCaseRequest(BaseModel):
    client_id: UUID | None = None       # omitted by clients (auto-filled from JWT sub)
    selected_products: list[str]
    assigned_advisor_id: UUID | None = None
    case_name: str | None = None        # stored in metadata
    metadata: dict[str, Any] = {}


_STAGE_PROGRESS: dict[str, int] = {
    "INTAKE": 15,
    "KYC": 35,
    "PARALLEL_PRODUCTS": 60,
    "REVIEW": 80,
    "COMPLETE": 100,
    "ESCALATED": 75,
}

_PRODUCT_STATUS_PROGRESS: dict[str, int] = {
    "PENDING": 0,
    "IN_PROGRESS": 50,
    "COMPLETE": 100,
    "FAILED": 0,
    "SKIPPED": 100,
}


class ProductTrackOut(BaseModel):
    id: UUID
    product_code: str
    product_name: str = ""
    status: str
    progress: int = 0
    steps_total: int = 0
    steps_completed: int = 0
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
    client_id: UUID
    client_name: str
    current_stage: str
    status: str
    overall_progress: int
    documents_total: int
    documents_received: int
    documents_approved: int
    products: list[ProductTrackOut]
    kyc_status: str | None
    escalated: bool


class CaseListOut(BaseModel):
    id: UUID
    client_id: UUID
    client_name: str
    case_name: str | None
    status: str
    current_stage: str
    selected_products: list[str]
    created_at: datetime
    updated_at: datetime


class ResumeResponse(BaseModel):
    case_id: UUID
    message: str
    stage: str


class ProductOut(BaseModel):
    id: UUID
    product_code: str
    name: str
    description: str | None

    model_config = {"from_attributes": True}


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


def _build_product_track(cp: CaseProduct) -> ProductTrackOut:
    steps = cp.steps or []
    completed = sum(1 for s in steps if s.status in ("COMPLETE", "SKIPPED"))
    product_name = cp.product.name if cp.product else cp.product_code
    return ProductTrackOut(
        id=cp.id,
        product_code=cp.product_code,
        product_name=product_name,
        status=cp.status,
        progress=_PRODUCT_STATUS_PROGRESS.get(cp.status, 0),
        steps_total=len(steps),
        steps_completed=completed,
        started_at=cp.started_at,
        completed_at=cp.completed_at,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/products", response_model=list[ProductOut])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> list[ProductOut]:
    result = await db.execute(select(Product).where(Product.is_active.is_(True)).order_by(Product.name))
    return [ProductOut.model_validate(p) for p in result.scalars().all()]


@router.get("", response_model=list[CaseListOut])
async def list_cases(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[CaseListOut]:
    query = (
        select(OnboardingCase, Client)
        .join(Client, OnboardingCase.client_id == Client.id)
        .order_by(OnboardingCase.updated_at.desc())
    )

    # Clients may only see their own cases
    if current_user.get("role") == "client":
        query = query.where(OnboardingCase.client_id == UUID(current_user["sub"]))

    result = await db.execute(query)
    rows = result.all()
    return [
        CaseListOut(
            id=case.id,
            client_id=case.client_id,
            client_name=f"{client.first_name} {client.last_name}",
            case_name=(case.extra_metadata or {}).get("case_name"),
            status=case.status,
            current_stage=case.current_stage,
            selected_products=case.selected_products,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
        for case, client in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CaseSummaryOut)
async def initiate_case(
    body: InitiateCaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CaseSummaryOut:
    role = current_user.get("role", "")

    # Clients always create cases for themselves; advisors/admins must supply client_id
    if role == "client":
        client_id = UUID(current_user["sub"])
    elif body.client_id is not None:
        client_id = body.client_id
    else:
        raise ConflictError("client_id is required for advisor/admin case creation")

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

    metadata = dict(body.metadata)
    if body.case_name:
        metadata["case_name"] = body.case_name

    case = OnboardingCase(
        client_id=client_id,
        selected_products=body.selected_products,
        assigned_advisor_id=body.assigned_advisor_id,
        extra_metadata=metadata,
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


def _assert_case_access(case: OnboardingCase, current_user: dict) -> None:
    if current_user.get("role") == "client" and str(case.client_id) != current_user["sub"]:
        from app.api.error_handlers import NotFoundError
        raise NotFoundError("OnboardingCase", str(case.id))


@router.get("/{case_id}", response_model=CaseDetailOut)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CaseDetailOut:
    case = await _get_case_or_404(case_id, db)
    _assert_case_access(case, current_user)
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
    current_user: dict = Depends(get_current_user),
) -> CaseProgressOut:
    result = await db.execute(
        select(OnboardingCase)
        .options(
            selectinload(OnboardingCase.client),
            selectinload(OnboardingCase.case_products).selectinload(CaseProduct.product),
            selectinload(OnboardingCase.case_products).selectinload(CaseProduct.steps),
        )
        .where(OnboardingCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise NotFoundError("OnboardingCase", str(case_id))
    _assert_case_access(case, current_user)

    doc_result = await db.execute(
        select(Document.status).where(Document.case_id == case_id)
    )
    doc_statuses = doc_result.scalars().all()
    total_docs = len(doc_statuses)
    received = sum(1 for s in doc_statuses if s not in ("NOT_REQUESTED", "REQUESTED"))
    approved = sum(1 for s in doc_statuses if s == "APPROVED")

    ctx = case.shared_context or {}
    stage = case.current_stage
    client = case.client
    client_name = f"{client.first_name} {client.last_name}" if client else "Unknown"
    escalated = stage == "ESCALATED" or bool(ctx.get("escalated", False))

    return CaseProgressOut(
        case_id=case.id,
        client_id=case.client_id,
        client_name=client_name,
        current_stage=stage,
        status=case.status,
        overall_progress=_STAGE_PROGRESS.get(stage, 0),
        documents_total=total_docs,
        documents_received=received,
        documents_approved=approved,
        products=[_build_product_track(cp) for cp in case.case_products],
        kyc_status=ctx.get("kyc_status"),
        escalated=escalated,
    )


@router.post("/{case_id}/resume", status_code=status.HTTP_202_ACCEPTED, response_model=ResumeResponse)
async def resume_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("advisor", "admin")),
) -> ResumeResponse:
    case = await _get_case_or_404(case_id, db)
    asyncio.create_task(journey_resumption_service.resume_case(case_id=case.id))
    return ResumeResponse(
        case_id=case.id,
        message="Resume request accepted — JourneyResumptionService will restore state and re-spawn agents",
        stage=case.current_stage,
    )
