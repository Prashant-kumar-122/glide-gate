from __future__ import annotations

import asyncio
import io
from datetime import datetime
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType
from app.database import AsyncSessionLocal
from app.models.documents import Document
from app.services.document.document_status_service import document_status_service
from app.services.document.document_storage_adapter import storage_adapter
from app.services.document.document_version_manager import document_version_manager
from app.websocket.socket_emitter import socket_emitter

_IMAGE_MIMES = {"image/jpeg", "image/png", "image/tiff", "image/webp"}
_PDF_MIMES = {"application/pdf"}
_WORD_MIMES = {
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _preprocess_file(data: bytes, mime_type: str) -> bytes:
    """Pre-process uploaded file bytes before storage.

    Images  — strip EXIF metadata and normalise orientation via Pillow.
    PDFs    — passed through unchanged; text extraction is handled downstream
              by the Document Intelligence Agent OCR pipeline.
    Word    — passed through unchanged; same rationale as PDFs.

    Raises ValueError for any MIME type not in the three known groups (the
    router validates ALLOWED_MIME_TYPES before calling this, so this path
    should never be reached in normal operation).
    """
    if mime_type in _IMAGE_MIMES:
        return _preprocess_image(data, mime_type)

    if mime_type in _PDF_MIMES:
        logger.debug(f"[UploadService] PDF ({mime_type!r}) stored without pre-processing")
        return data

    if mime_type in _WORD_MIMES:
        logger.debug(f"[UploadService] Word document ({mime_type!r}) stored without pre-processing")
        return data

    raise ValueError(
        f"Unhandled MIME type {mime_type!r}. "
        "This should have been rejected by the router's ALLOWED_MIME_TYPES check."
    )


def _preprocess_image(data: bytes, mime_type: str) -> bytes:
    """Strip EXIF and fix orientation using Pillow.  Returns original bytes on failure."""
    try:
        from PIL import Image, ImageOps  # type: ignore[import]

        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)

        buf = io.BytesIO()
        fmt = "JPEG" if mime_type == "image/jpeg" else (img.format or "PNG")
        img.save(buf, format=fmt)
        processed = buf.getvalue()
        logger.debug(
            f"[UploadService] Image pre-processed: "
            f"{len(data)} → {len(processed)} bytes (mime={mime_type})"
        )
        return processed
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[UploadService] Image pre-processing skipped: {exc}")
        return data


async def _trigger_document_intelligence(
    document_id: UUID,
    case_id: UUID,
    client_id: UUID,
    filename: str,
    category: str,
) -> None:
    """Fire-and-forget: publish CLASSIFY_DOCUMENT + EXTRACT_OCR tasks via Temporal."""
    try:
        from app.services.orchestration.agent_orchestration_service import orchestration_service

        if not orchestration_service.is_started:
            logger.debug("[UploadService] Orchestration service not started; skipping DIA trigger")
            return

        classify_packet = TaskPacket(
            from_agent=AgentID.ORCHESTRATOR,
            to_agent=AgentID.DOCUMENT_INTELLIGENCE,
            task_type=TaskType.CLASSIFY_DOCUMENT,
            case_id=case_id,
            client_id=client_id,
            priority="NORMAL",
            payload={
                "document_id": str(document_id),
                "filename": filename,
                "raw_text": "",
            },
        )
        await orchestration_service.publish_task(classify_packet)

        ocr_packet = TaskPacket(
            from_agent=AgentID.ORCHESTRATOR,
            to_agent=AgentID.DOCUMENT_INTELLIGENCE,
            task_type=TaskType.EXTRACT_OCR,
            case_id=case_id,
            client_id=client_id,
            priority="NORMAL",
            payload={
                "document_id": str(document_id),
                "filename": filename,
                "category": category,
            },
        )
        await orchestration_service.publish_task(ocr_packet)

        logger.info(
            f"[UploadService] DIA tasks queued for document={document_id} "
            f"(classify + extract_ocr)"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[UploadService] DIA trigger failed (non-fatal): {exc}")


class DocumentUploadService:
    """Orchestrates the full document upload pipeline.

    Steps on every upload:
    1. File pre-processing: EXIF strip + orientation fix for images;
       PDFs and Word documents pass through unchanged.
    2. Persist bytes to storage backend (local disk or S3 stub).
    3. Determine version number via DocumentVersionManager.
    4. Create/persist the Document ORM record with storage_path.
    5. Fire-and-forget Document Intelligence Agent tasks via asyncio.create_task.
    6. Emit DOCUMENT_UPLOADED socket event with current badge count.
    """

    async def upload(
        self,
        *,
        case_id: UUID,
        client_id: UUID,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        document_type: str = "unknown",
        category: str = "identity",
        tags: list[str] | None = None,
        parent_doc_id: UUID | None = None,
        uploaded_by: str = "unknown",
        db: AsyncSession,
    ) -> Document:
        # Step 1 — pre-process file bytes (images: EXIF strip; PDFs/docs: pass-through)
        processed_bytes = _preprocess_file(file_bytes, mime_type)

        # Step 2 — persist to storage backend
        import uuid as _uuid
        temp_id = _uuid.uuid4()  # generate before DB insert so storage path is deterministic
        storage_result = await storage_adapter.store(
            case_id=case_id,
            document_id=temp_id,
            filename=filename,
            data=processed_bytes,
        )

        # Step 3 — version number (1 for new uploads, parent+1 for resubmissions)
        version = await document_version_manager.next_version(parent_doc_id, db)

        # Step 4 — persist Document record
        doc = Document(
            id=temp_id,
            case_id=case_id,
            client_id=client_id,
            document_type=document_type,
            category=category,
            status="RECEIVED",
            original_filename=filename,
            storage_path=storage_result.storage_path,
            file_size_bytes=storage_result.stored_bytes,
            mime_type=mime_type,
            version=version,
            parent_doc_id=parent_doc_id,
            uploaded_by=uploaded_by,
            tags=tags or [],
            uploaded_at=datetime.utcnow(),
            extra_metadata={"checksum_sha256": storage_result.checksum_sha256},
        )
        db.add(doc)
        await db.flush()  # populate DB-generated fields without closing session

        logger.info(
            f"[UploadService] Document persisted: id={doc.id} "
            f"case={case_id} version={version} "
            f"mime={mime_type} size={storage_result.stored_bytes}B"
        )

        # Step 5 — fire-and-forget DIA pipeline (classify + OCR via agent bus)
        asyncio.create_task(
            _trigger_document_intelligence(
                document_id=doc.id,
                case_id=case_id,
                client_id=client_id,
                filename=filename,
                category=category,
            ),
            name=f"dia-{doc.id}",
        )

        # Step 5a — auto-trigger AI completeness validation so results appear
        # in the UI without requiring a manual "Run AI Check".
        # The explicit POST /documents/{id}/validate endpoint remains available
        # for advisors to re-run validation on demand.
        from app.services.validation.validation_orchestrator import run_validate_in_background
        asyncio.create_task(
            run_validate_in_background(doc.id),
            name=f"validate-auto-{doc.id}",
        )

        # Step 5b — if this is a resubmission, compute version diff asynchronously
        if parent_doc_id is not None:
            from app.services.validation.validation_orchestrator import run_diff_in_background
            asyncio.create_task(
                run_diff_in_background(doc.id),
                name=f"diff-{doc.id}",
            )

        # Step 5c — create advisor task for document review
        asyncio.create_task(
            _create_document_task(
                case_id=case_id,
                document_id=doc.id,
                filename=filename,
            ),
            name=f"task-doc-{doc.id}",
        )

        # Step 6 — emit DOCUMENT_UPLOADED with badge count for UI badge update
        badge_count = await document_status_service.get_upload_badge_count(case_id, db)
        await socket_emitter.document_uploaded(
            case_id,
            {
                "document_id": str(doc.id),
                "case_id": str(case_id),
                "filename": filename,
                "document_type": document_type,
                "category": category,
                "mime_type": mime_type,
                "version": version,
                "parent_doc_id": str(parent_doc_id) if parent_doc_id else None,
                "status": "RECEIVED",
                "badge_count": badge_count,
                "uploaded_by": uploaded_by,
            },
        )

        return doc


async def _create_document_task(
    case_id: UUID, document_id: UUID, filename: str
) -> None:
    try:
        from app.services.task.task_service import task_service
        async with AsyncSessionLocal() as db:
            await task_service.create_task(
                case_id=case_id,
                assignee_id=None,
                assignee_role="advisor",
                task_type="DOCUMENT_REVIEW",
                title=f"Review uploaded document: {filename}",
                document_id=document_id,
                db=db,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[UploadService] create_document_task failed (non-fatal): {exc}")


document_upload_service = DocumentUploadService()
