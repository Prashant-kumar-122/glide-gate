from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel, computed_field
from sqlalchemy import select, update as sa_update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.role_guard import require_role
from app.api.error_handlers import NotFoundError, UnprocessableError
from app.database import get_db
from app.database import AsyncSessionLocal
from app.models.cases import OnboardingCase
from app.models.documents import Document
from app.services.document.document_upload_service import document_upload_service
from app.services.validation.validation_orchestrator import run_validate_in_background

router = APIRouter(tags=["documents"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

DOCUMENT_STATUSES = (
    "NOT_REQUESTED",
    "REQUESTED",
    "RECEIVED",
    "UNDER_REVIEW",
    "NEEDS_REVISION",
    "APPROVED",
)


# ── Response models ───────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: UUID
    case_id: UUID
    client_id: UUID
    document_type: str
    category: str
    status: str
    original_filename: str | None
    file_size_bytes: int | None
    mime_type: str | None
    version: int
    parent_doc_id: UUID | None
    uploaded_by: str | None
    tags: list[str]
    ocr_result: dict[str, Any]
    classification_result: dict[str, Any]
    validation_result: dict[str, Any]
    diff_result: dict[str, Any]
    uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def name(self) -> str | None:
        return self.original_filename

    @computed_field
    @property
    def has_validation_result(self) -> bool:
        return bool(self.validation_result)

    @computed_field
    @property
    def has_diff(self) -> bool:
        return bool(self.diff_result)


class DocumentStatusOut(BaseModel):
    id: UUID
    status: str
    version: int
    validation_result: dict[str, Any]
    updated_at: datetime

    model_config = {"from_attributes": True}


class ValidateAcceptedOut(BaseModel):
    document_id: UUID
    message: str


class UpdateDocumentStatusRequest(BaseModel):
    status: str


class DiffOut(BaseModel):
    document_id: UUID
    version: int
    parent_doc_id: UUID | None
    diff_result: dict[str, Any]

    @computed_field
    @property
    def parent_id(self) -> UUID | None:
        return self.parent_doc_id

    @computed_field
    @property
    def similarity_ratio(self) -> float:
        return float(self.diff_result.get("similarity_ratio", 0.0))

    @computed_field
    @property
    def sections(self) -> list:
        return self.diff_result.get("sections", [])

    @computed_field
    @property
    def summary(self) -> str:
        return self.diff_result.get("summary", "")

    @computed_field
    @property
    def computed_at(self) -> str | None:
        return self.diff_result.get("computed_at")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_doc_or_404(doc_id: UUID, db: AsyncSession) -> Document:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError("Document", str(doc_id))
    return doc


async def _update_case_percentage_for_docs(case_id: UUID) -> None:
    """Recompute the document portion (70-100%) of the case percentage column."""
    try:
        async with AsyncSessionLocal() as db:
            total_result = await db.execute(
                select(func.count()).select_from(Document).where(Document.case_id == case_id)
            )
            total = total_result.scalar() or 0

            approved_result = await db.execute(
                select(func.count()).select_from(Document)
                .where(Document.case_id == case_id)
                .where(Document.status == "APPROVED")
            )
            approved = approved_result.scalar() or 0

            doc_ratio = (approved / total) if total > 0 else 0.0
            # Documents contribute the 70-100% band of the overall progress bar
            new_pct = round(70.0 + doc_ratio * 30.0, 1)

            await db.execute(
                sa_update(OnboardingCase)
                .where(OnboardingCase.id == case_id)
                .values(percentage=new_pct)
            )
            await db.commit()
    except Exception as exc:
        from loguru import logger
        logger.warning(f"documents: percentage update failed for case {case_id}: {exc}")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/cases/{case_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentOut,
    tags=["documents"],
)
async def upload_document(
    case_id: UUID,
    file: UploadFile = File(...),
    document_type: str = Form("unknown"),
    category: str = Form("identity"),
    tags: str = Form(""),
    parent_doc_id: UUID | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> DocumentOut:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise UnprocessableError(
            f"Unsupported file type '{file.content_type}'. Allowed: {sorted(ALLOWED_MIME_TYPES)}"
        )

    raw = await file.read()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    from app.models.cases import OnboardingCase
    case_result = await db.execute(
        select(OnboardingCase.client_id).where(OnboardingCase.id == case_id)
    )
    client_id_row = case_result.scalar_one_or_none()
    if client_id_row is None:
        raise NotFoundError("OnboardingCase", str(case_id))

    doc = await document_upload_service.upload(
        case_id=case_id,
        client_id=client_id_row,
        file_bytes=raw,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        document_type=document_type,
        category=category,
        tags=tag_list,
        parent_doc_id=parent_doc_id,
        uploaded_by=user.get("role", "unknown"),
        db=db,
    )
    await db.commit()
    await db.refresh(doc)
    return DocumentOut.model_validate(doc)


@router.get(
    "/cases/{case_id}/documents",
    response_model=list[DocumentOut],
    tags=["documents"],
)
async def list_documents(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> list[DocumentOut]:
    result = await db.execute(
        select(Document)
        .where(Document.case_id == case_id)
        .order_by(Document.created_at)
    )
    docs = result.scalars().all()
    return [DocumentOut.model_validate(d) for d in docs]


@router.get(
    "/documents/{document_id}",
    response_model=DocumentOut,
    tags=["documents"],
)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> DocumentOut:
    doc = await _get_doc_or_404(document_id, db)
    return DocumentOut.model_validate(doc)


@router.post(
    "/documents/{document_id}/validate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ValidateAcceptedOut,
    tags=["documents"],
)
async def trigger_validation(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("Advisor", "Admin")),
) -> ValidateAcceptedOut:
    doc = await _get_doc_or_404(document_id, db)
    if doc.status == "RECEIVED":
        doc.status = "UNDER_REVIEW"
        await db.commit()
    asyncio.create_task(
        run_validate_in_background(document_id),
        name=f"validate-{document_id}",
    )
    return ValidateAcceptedOut(
        document_id=document_id,
        message="Validation accepted — AI completeness check running asynchronously",
    )


@router.patch(
    "/documents/{document_id}",
    response_model=DocumentOut,
    tags=["documents"],
)
async def update_document_status(
    document_id: UUID,
    body: UpdateDocumentStatusRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("Advisor", "Admin")),
) -> DocumentOut:
    if body.status not in DOCUMENT_STATUSES:
        raise UnprocessableError(
            f"Invalid status '{body.status}'. Allowed: {list(DOCUMENT_STATUSES)}"
        )
    doc = await _get_doc_or_404(document_id, db)
    doc.status = body.status
    await db.commit()
    await db.refresh(doc)

    # Recalculate the document portion (70-100%) of the overall percentage column
    if body.status in ("APPROVED", "REJECTED", "RECEIVED", "UNDER_REVIEW"):
        asyncio.create_task(_update_case_percentage_for_docs(doc.case_id))

    return DocumentOut.model_validate(doc)


@router.get(
    "/documents/{document_id}/diff",
    response_model=DiffOut,
    tags=["documents"],
)
async def get_document_diff(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> DiffOut:
    doc = await _get_doc_or_404(document_id, db)
    return DiffOut(
        document_id=doc.id,
        version=doc.version,
        parent_doc_id=doc.parent_doc_id,
        diff_result=doc.diff_result,
    )
