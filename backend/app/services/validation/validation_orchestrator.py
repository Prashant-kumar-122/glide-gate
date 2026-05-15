from __future__ import annotations

"""End-to-end validation and version-diff pipeline (BRD FR-08, FR-09).

validate_document:
  API trigger → load effective prompt from repository → apply deterministic
  controls → Anthropic LLM call (with heuristic fallback) → parse FindingResult[]
  → persist to documents.validation_result → emit DOCUMENT_STATUS_CHANGED socket
  event → return ValidationResult.

compute_diff:
  Document resubmission → load parent document OCR text → VersionDiffDetector
  (Python difflib) → persist to documents.diff_result → return DiffResult.
"""

from datetime import datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.document_intelligence.ai_completeness_validator import (
    AICompletenessValidator,
    ValidationResult,
)
from app.agents.document_intelligence.ocr_extractor import OcrExtractor, OcrField, OcrResult
from app.agents.document_intelligence.version_diff_detector import (
    DiffResult,
    VersionDiffDetector,
)
from app.models.documents import Document
from app.services.validation.validation_prompt_repository import get_effective_prompt
from app.websocket.socket_emitter import socket_emitter

_validator = AICompletenessValidator()
_differ = VersionDiffDetector()
_ocr = OcrExtractor()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ocr_result_from_doc(doc: Document) -> OcrResult | None:
    """Reconstruct an OcrResult from the document's stored ocr_result JSONB.
    Returns None if the JSONB is empty or malformed.
    """
    data = doc.ocr_result
    if not data or "extraction_id" not in data:
        return None
    try:
        fields = [OcrField(**f) for f in data.get("fields", [])]
        return OcrResult(
            extraction_id=data["extraction_id"],
            document_id=doc.id,
            raw_text=data.get("raw_text", ""),
            fields=fields,
            page_count=data.get("page_count", 1),
            language=data.get("language", "en"),
            extraction_quality=data.get("extraction_quality", 0.8),
            latency_ms=data.get("latency_ms", 0),
            extracted_at=data.get("extracted_at", ""),
            is_simulated=data.get("is_simulated", True),
        )
    except Exception:
        return None


def _raw_text_from_doc(doc: Document) -> str:
    """Extract raw OCR text from a document's ocr_result JSONB."""
    if not doc.ocr_result:
        return ""
    raw = doc.ocr_result.get("raw_text", "")
    if raw:
        return raw
    # Reconstruct from fields if raw_text is absent
    fields = doc.ocr_result.get("fields", [])
    if fields:
        return "\n".join(f"{f['key']}: {f['value']}" for f in fields)
    return ""


# ── Orchestrator ──────────────────────────────────────────────────────────────

class ValidationOrchestrator:
    """Wires the full AI validation and version-diff flows."""

    async def validate_document(
        self, document_id: UUID, db: AsyncSession
    ) -> ValidationResult:
        # 1. Load document
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise ValueError(f"Document {document_id} not found")

        logger.info(
            f"[ValidationOrchestrator] Starting validation: "
            f"document={document_id} category={doc.category}"
        )

        # 2. Get OcrResult — use stored result or run simulated extraction
        ocr_result = _ocr_result_from_doc(doc)
        if ocr_result is None or (not ocr_result.fields and not ocr_result.raw_text):
            logger.debug(
                f"[ValidationOrchestrator] No OCR data for doc={document_id}; "
                "running simulated extraction"
            )
            try:
                ocr_result = await _ocr.extract(
                    document_id=doc.id,
                    filename=doc.original_filename or "document",
                    category=doc.category,  # type: ignore[arg-type]
                )
                # Persist the fresh OCR result so future validation calls skip re-extraction
                doc.ocr_result = ocr_result.model_dump(mode="json")
            except Exception as exc:
                logger.warning(f"[ValidationOrchestrator] Simulated OCR failed: {exc}")
                # Continue with an empty OcrResult — heuristic fallback handles it
                from uuid import uuid4
                ocr_result = OcrResult(
                    extraction_id=uuid4(),
                    document_id=doc.id,
                    raw_text="",
                    fields=[],
                    page_count=1,
                    language="en",
                    extraction_quality=0.5,
                    latency_ms=0,
                    extracted_at=datetime.utcnow().isoformat(),
                    is_simulated=True,
                )

        # 3. Load effective prompt (admin override → file default → hardcoded)
        prompt = get_effective_prompt(doc.category)

        # 4. Run AI completeness validation (LLM + heuristic fallback)
        validation = await _validator.validate(
            ocr_result=ocr_result,
            category=doc.category,  # type: ignore[arg-type]
            custom_prompt=prompt,
        )

        # 5. Persist validation result and advance status
        doc.validation_result = validation.model_dump(mode="json")
        if doc.status == "RECEIVED":
            doc.status = "UNDER_REVIEW"
        await db.commit()

        # 6. Emit real-time socket event so the advisor workspace updates instantly
        await socket_emitter.document_status_changed(
            doc.case_id,
            {
                "document_id": str(doc.id),
                "case_id": str(doc.case_id),
                "status": doc.status,
                "validation_result": {
                    "overall_status": validation.overall_status,
                    "completeness_pct": validation.completeness_pct,
                    "findings_count": len(validation.findings),
                    "validated_at": validation.validated_at,
                    "llm_used": validation.llm_used,
                },
                "badge_count": 0,
            },
        )

        logger.info(
            f"[ValidationOrchestrator] Validation complete: "
            f"document={document_id} overall={validation.overall_status} "
            f"completeness={validation.completeness_pct}% "
            f"llm_used={validation.llm_used}"
        )
        return validation

    async def compute_diff(
        self, document_id: UUID, db: AsyncSession
    ) -> DiffResult | None:
        # 1. Load document
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise ValueError(f"Document {document_id} not found")

        if doc.parent_doc_id is None:
            return None

        # 2. Load parent document
        parent_result = await db.execute(
            select(Document).where(Document.id == doc.parent_doc_id)
        )
        parent = parent_result.scalar_one_or_none()
        if parent is None:
            logger.warning(
                f"[ValidationOrchestrator] Parent {doc.parent_doc_id} not found; "
                "skipping diff"
            )
            return None

        logger.info(
            f"[ValidationOrchestrator] Computing diff: "
            f"document={document_id} v{parent.version}→v{doc.version}"
        )

        # 3. Extract text from both versions (OCR fields or raw text)
        old_text = _raw_text_from_doc(parent)
        new_text = _raw_text_from_doc(doc)

        # Synthetic fallback for demo when neither version has been OCR'd
        if not old_text:
            old_text = (
                f"Document version {parent.version}\n"
                f"Category: {parent.category}\n"
                f"Filename: {parent.original_filename or 'unknown'}\n"
                f"Uploaded: {parent.uploaded_at or parent.created_at}"
            )
        if not new_text:
            new_text = (
                f"Document version {doc.version}\n"
                f"Category: {doc.category}\n"
                f"Filename: {doc.original_filename or 'unknown'}\n"
                f"Uploaded: {doc.uploaded_at or doc.created_at}"
            )

        # 4. Compute diff using VersionDiffDetector (difflib)
        diff = _differ.compute(
            document_id=doc.id,
            old_version=parent.version,
            new_version=doc.version,
            old_text=old_text,
            new_text=new_text,
        )

        # 5. Persist diff result
        doc.diff_result = diff.model_dump(mode="json")
        await db.commit()

        logger.info(
            f"[ValidationOrchestrator] Diff complete: "
            f"similarity={diff.similarity_ratio} "
            f"added={diff.added_count} modified={diff.modified_count} "
            f"removed={diff.removed_count}"
        )
        return diff


# ── Singletons ────────────────────────────────────────────────────────────────

validation_orchestrator = ValidationOrchestrator()


# ── Background task wrappers ──────────────────────────────────────────────────
# Each acquires its own DB session so they can be safely fired with
# asyncio.create_task without holding the request's session open.

async def run_validate_in_background(document_id: UUID) -> None:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            await validation_orchestrator.validate_document(document_id, db)
        except Exception as exc:
            logger.error(
                f"[ValidationOrchestrator] Background validation failed "
                f"doc={document_id}: {exc}"
            )


async def run_diff_in_background(document_id: UUID) -> None:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            await validation_orchestrator.compute_diff(document_id, db)
        except Exception as exc:
            logger.error(
                f"[ValidationOrchestrator] Background diff failed "
                f"doc={document_id}: {exc}"
            )
