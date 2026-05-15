from __future__ import annotations

from typing import Literal
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documents import Document
from app.services.audit.audit_log_service import audit_log_service
from app.websocket.socket_emitter import socket_emitter

DocumentStatus = Literal[
    "NOT_REQUESTED",
    "REQUESTED",
    "RECEIVED",
    "UNDER_REVIEW",
    "NEEDS_REVISION",
    "APPROVED",
]

# Valid one-way status transitions
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "NOT_REQUESTED": {"REQUESTED"},
    "REQUESTED": {"RECEIVED"},
    "RECEIVED": {"UNDER_REVIEW", "NEEDS_REVISION"},
    "UNDER_REVIEW": {"NEEDS_REVISION", "APPROVED"},
    "NEEDS_REVISION": {"RECEIVED"},
    "APPROVED": set(),
}


class DocumentStatusService:
    """Manages document status transitions and emits socket events on change."""

    async def update_status(
        self,
        document_id: UUID,
        new_status: str,
        db: AsyncSession,
        *,
        reason: str | None = None,
        emit_event: bool = True,
    ) -> Document:
        """Transition a document to *new_status*.

        Validates the transition is allowed, persists to DB, and emits a
        DOCUMENT_STATUS_CHANGED socket event to the case room.
        """
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise ValueError(f"Document {document_id} not found")

        current = doc.status
        allowed = _ALLOWED_TRANSITIONS.get(current, set())
        if new_status not in allowed and new_status != current:
            raise ValueError(
                f"Invalid status transition {current!r} → {new_status!r}. "
                f"Allowed from {current!r}: {allowed or {'(terminal state)'}}"
            )

        if new_status == current:
            return doc

        doc.status = new_status
        await db.flush()

        logger.info(
            f"[DocStatus] document={document_id} {current} → {new_status}"
            + (f" reason={reason}" if reason else "")
        )

        await audit_log_service.log_document_status_changed(
            document_id=document_id,
            case_id=doc.case_id,
            old_status=current,
            new_status=new_status,
            category=doc.category,
            db=db,
        )

        if emit_event:
            badge_count = await self.get_upload_badge_count(doc.case_id, db)
            await socket_emitter.document_status_changed(
                doc.case_id,
                {
                    "document_id": str(document_id),
                    "case_id": str(doc.case_id),
                    "old_status": current,
                    "new_status": new_status,
                    "document_type": doc.document_type,
                    "category": doc.category,
                    "badge_count": badge_count,
                    "reason": reason,
                },
            )

        return doc

    async def get_upload_badge_count(self, case_id: UUID, db: AsyncSession) -> int:
        """Count documents in RECEIVED or UNDER_REVIEW state for badge display."""
        result = await db.execute(
            select(func.count()).where(
                Document.case_id == case_id,
                Document.status.in_(["RECEIVED", "UNDER_REVIEW"]),
            )
        )
        return result.scalar_one() or 0


document_status_service = DocumentStatusService()
