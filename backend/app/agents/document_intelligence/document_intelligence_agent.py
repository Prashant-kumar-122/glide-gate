from __future__ import annotations

from typing import Any
from uuid import UUID

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskResponse, TaskType
from app.agents.base.base_agent import BaseAgent
from app.agents.document_intelligence.ai_completeness_validator import (
    AICompletenessValidator,
)
from app.agents.document_intelligence.document_classifier import DocumentClassifier
from app.agents.document_intelligence.ocr_extractor import OcrExtractor
from app.agents.document_intelligence.version_diff_detector import VersionDiffDetector


class DocumentIntelligenceAgent(BaseAgent):
    """
    Document Intelligence Agent (BRD Section 6.1, FR-06, FR-08, FR-09).

    Handles:
    - CLASSIFY_DOCUMENT  — classify document type and category from filename/text
    - EXTRACT_OCR        — simulate OCR extraction, return structured fields
    - VALIDATE_DOCUMENT  — AI completeness validation (pass/warn/fail findings)
    - COMPUTE_DIFF       — difflib-based version diff between two document texts

    MCP Document Management connector wired in STEP-16 replaces simulated OCR.
    """

    agent_id = AgentID.DOCUMENT_INTELLIGENCE

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._classifier = DocumentClassifier()
        self._ocr = OcrExtractor()
        self._validator = AICompletenessValidator()
        self._differ = VersionDiffDetector()

    # ── BaseAgent.process ─────────────────────────────────────────────────────

    async def process(self, task: TaskPacket) -> TaskResponse:
        handlers = {
            TaskType.CLASSIFY_DOCUMENT: self._handle_classify,
            TaskType.EXTRACT_OCR: self._handle_ocr,
            TaskType.VALIDATE_DOCUMENT: self._handle_validate,
            TaskType.COMPUTE_DIFF: self._handle_diff,
        }
        handler = handlers.get(task.task_type)
        if handler is None:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=[f"Unsupported task_type: {task.task_type}"],
            )
        return await handler(task)

    # ── Task handlers ─────────────────────────────────────────────────────────

    async def _handle_classify(self, task: TaskPacket) -> TaskResponse:
        filename: str = task.payload.get("filename", "")
        raw_text: str = task.payload.get("raw_text", "")

        self.logger.info(
            f"Classifying document for case={task.case_id} filename='{filename}'"
        )

        result = self._classifier.classify(filename=filename, raw_text=raw_text)
        self.logger.info(
            f"Classification result: category={result.category} "
            f"doc_type={result.doc_type} confidence={result.confidence}"
        )

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={
                "category": result.category,
                "doc_type": result.doc_type,
                "confidence": result.confidence,
                "display_name": result.display_name,
                "requires_expiry_check": result.requires_expiry_check,
                "typical_fields": result.typical_fields,
            },
        )

    async def _handle_ocr(self, task: TaskPacket) -> TaskResponse:
        document_id_str: str | None = task.payload.get("document_id")
        document_id: UUID | None = UUID(document_id_str) if document_id_str else None
        filename: str = task.payload.get("filename", "")
        category: str = task.payload.get("category", "unknown")

        self.logger.info(
            f"OCR extraction for case={task.case_id} "
            f"document_id={document_id} category={category}"
        )

        result = await self._ocr.extract(
            document_id=document_id,
            filename=filename,
            category=category,  # type: ignore[arg-type]
        )

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={
                "extraction_id": str(result.extraction_id),
                "document_id": str(result.document_id) if result.document_id else None,
                "raw_text": result.raw_text,
                "fields": [f.model_dump() for f in result.fields],
                "page_count": result.page_count,
                "language": result.language,
                "extraction_quality": result.extraction_quality,
                "latency_ms": result.latency_ms,
                "extracted_at": result.extracted_at,
                "is_simulated": result.is_simulated,
            },
        )

    async def _handle_validate(self, task: TaskPacket) -> TaskResponse:
        document_id_str: str | None = task.payload.get("document_id")
        category: str = task.payload.get("category", "unknown")
        custom_prompt: dict[str, Any] | None = task.payload.get("custom_prompt")

        # Accept either an OcrResult dict payload or a plain fields dict
        ocr_payload: dict[str, Any] = task.payload.get("ocr_result", {})
        if not ocr_payload:
            # Build a minimal OcrResult from flat fields list
            fields_raw: list[dict[str, Any]] = task.payload.get("fields", [])
            raw_text: str = task.payload.get("raw_text", "")
            ocr_payload = {
                "extraction_id": str(task.id),
                "document_id": document_id_str,
                "raw_text": raw_text,
                "fields": fields_raw,
                "page_count": 1,
                "extraction_quality": 0.9,
                "latency_ms": 0,
                "extracted_at": "",
            }

        from app.agents.document_intelligence.ocr_extractor import OcrResult

        ocr_result = OcrResult(**ocr_payload)

        self.logger.info(
            f"Validating document for case={task.case_id} "
            f"document_id={document_id_str} category={category}"
        )

        validation = await self._validator.validate(
            ocr_result=ocr_result,
            category=category,  # type: ignore[arg-type]
            custom_prompt=custom_prompt,
        )

        self.logger.info(
            f"Validation complete: overall={validation.overall_status} "
            f"completeness={validation.completeness_pct}% "
            f"findings={len(validation.findings)}"
        )

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={
                "validation_id": str(validation.validation_id),
                "document_id": str(validation.document_id) if validation.document_id else None,
                "category": validation.category,
                "overall_status": validation.overall_status,
                "findings": [f.model_dump() for f in validation.findings],
                "completeness_pct": validation.completeness_pct,
                "validated_at": validation.validated_at,
                "llm_used": validation.llm_used,
            },
        )

    async def _handle_diff(self, task: TaskPacket) -> TaskResponse:
        document_id_str: str | None = task.payload.get("document_id")
        document_id: UUID | None = UUID(document_id_str) if document_id_str else None
        old_version: int = task.payload.get("old_version", 1)
        new_version: int = task.payload.get("new_version", 2)

        # Accept text or field dicts
        old_text: str = task.payload.get("old_text", "")
        new_text: str = task.payload.get("new_text", "")
        old_fields: dict[str, str] = task.payload.get("old_fields", {})
        new_fields: dict[str, str] = task.payload.get("new_fields", {})

        self.logger.info(
            f"Computing diff for case={task.case_id} "
            f"document_id={document_id} v{old_version}→v{new_version}"
        )

        if old_fields and new_fields:
            diff = self._differ.compute_from_fields(
                document_id=document_id,
                old_version=old_version,
                new_version=new_version,
                old_fields=old_fields,
                new_fields=new_fields,
            )
        else:
            diff = self._differ.compute(
                document_id=document_id,
                old_version=old_version,
                new_version=new_version,
                old_text=old_text,
                new_text=new_text,
            )

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={
                "diff_id": str(diff.diff_id),
                "document_id": str(diff.document_id) if diff.document_id else None,
                "old_version": diff.old_version,
                "new_version": diff.new_version,
                "sections": [s.model_dump() for s in diff.sections],
                "added_count": diff.added_count,
                "modified_count": diff.modified_count,
                "removed_count": diff.removed_count,
                "unchanged_count": diff.unchanged_count,
                "similarity_ratio": diff.similarity_ratio,
                "summary": diff.summary,
                "computed_at": diff.computed_at,
            },
        )
