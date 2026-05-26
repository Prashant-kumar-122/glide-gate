from __future__ import annotations

import asyncio
import base64
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.documents import Document
from app.models.questionnaire import OnboardingQuestion, OnboardingQuestionnaire, OnboardingQuestionSession
from app.services.document.document_storage_adapter import storage_adapter


class AIExtractionService:
    """Synchronous on-demand document field extraction using a local vision LLM."""

    async def extract(self, case_id: UUID, db: AsyncSession) -> list[dict[str, Any]]:
        """
        Extract questionnaire field values from all uploaded documents for the case.
        Returns a list of {"key": str, "value": str, "confidence": float} dicts.
        Falls back to mock data on model failure, or [] on unexpected errors.
        """
        try:
            logger.info(f"ai_extraction: starting extraction for case {case_id}")

            schema_fields = await self._fetch_schema(case_id, db)
            if not schema_fields:
                logger.warning(f"ai_extraction: no schema fields found for case {case_id}")
                return []
            logger.info(f"ai_extraction: schema has {len(schema_fields)} fields")

            docs = await self._fetch_documents(case_id, db)
            if not docs:
                logger.warning(f"ai_extraction: no documents found for case {case_id}")
                return []
            logger.info(f"ai_extraction: found {len(docs)} document(s)")

            images_b64, pdf_texts = await self._load_document_content(docs)
            logger.info(f"ai_extraction: loaded {len(images_b64)} image(s), {len(pdf_texts)} PDF text(s)")

            if not images_b64 and not pdf_texts:
                logger.warning("ai_extraction: no readable content in documents (unsupported formats?)")
                return self._mock_extraction(schema_fields)

            try:
                response_text = await self._call_vision_model(schema_fields, images_b64, pdf_texts)
                logger.debug(f"ai_extraction: raw model response: {response_text[:500]}")
                return self._parse_response(response_text, schema_fields)
            except Exception:
                logger.exception(
                    f"ai_extraction: vision model failed for case {case_id}, falling back to mock data"
                )
                return self._mock_extraction(schema_fields)

        except Exception:
            logger.exception(f"ai_extraction: extraction failed for case {case_id}")
            return []

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _fetch_schema(self, case_id: UUID, db: AsyncSession) -> list[dict[str, str]]:
        questionnaire_id: UUID | None = None
        session_row = await db.execute(
            select(OnboardingQuestionSession.questionnaire_id)
            .where(OnboardingQuestionSession.case_id == case_id)
            .limit(1)
        )
        questionnaire_id = session_row.scalar_one_or_none()

        if questionnaire_id is None:
            q_row = await db.execute(
                select(OnboardingQuestionnaire.id)
                .where(OnboardingQuestionnaire.is_active.is_(True))
                .limit(1)
            )
            questionnaire_id = q_row.scalar_one_or_none()

        if questionnaire_id is None:
            return []

        result = await db.execute(
            select(OnboardingQuestion)
            .where(OnboardingQuestion.questionnaire_id == questionnaire_id)
            .order_by(OnboardingQuestion.order_index)
        )
        questions = result.scalars().all()
        return [
            {
                "key": q.question_key,
                "label": q.question_text or q.question_key.replace("_", " ").title(),
                "description": q.question_text or "",
            }
            for q in questions
        ]

    async def _fetch_documents(self, case_id: UUID, db: AsyncSession) -> list[Document]:
        result = await db.execute(
            select(Document)
            .where(Document.case_id == case_id)
            .where(Document.storage_path.isnot(None))
            .order_by(Document.created_at)
        )
        return list(result.scalars().all())

    async def _load_document_content(
        self, docs: list[Document]
    ) -> tuple[list[str], list[str]]:
        images_b64: list[str] = []
        pdf_texts: list[str] = []

        for doc in docs:
            if not doc.storage_path:
                continue
            try:
                file_bytes = await storage_adapter.retrieve(doc.storage_path)
            except Exception as exc:
                logger.warning(f"ai_extraction: could not read {doc.storage_path}: {exc}")
                continue

            mime = (doc.mime_type or "").lower()
            if mime in ("image/jpeg", "image/png", "image/tiff", "image/jpg"):
                resized = self._resize_image(file_bytes)
                images_b64.append(base64.b64encode(resized).decode())
            elif mime == "application/pdf":
                text = self._extract_pdf_text(file_bytes)
                if text.strip():
                    pdf_texts.append(f"[{doc.original_filename or 'document'}]\n{text}")

        return images_b64, pdf_texts

    def _resize_image(self, image_bytes: bytes, max_size: int = 1024) -> bytes:
        """Downscale to max_size on the longest side and re-encode as JPEG."""
        from PIL import Image
        try:
            img = Image.open(BytesIO(image_bytes))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            w, h = img.size
            if max(w, h) > max_size:
                scale = max_size / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            out = BytesIO()
            img.save(out, format="JPEG", quality=85)
            return out.getvalue()
        except Exception as exc:
            logger.warning(f"ai_extraction: image resize failed, using original: {exc}")
            return image_bytes

    def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(pdf_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except Exception as exc:
            logger.warning(f"ai_extraction: PDF text extraction failed: {exc}")
            return ""

    async def _call_vision_model(
        self,
        schema_fields: list[dict[str, str]],
        images_b64: list[str],
        pdf_texts: list[str],
    ) -> str:
        fields_json = json.dumps(schema_fields, indent=2)

        keys_only = json.dumps([f["key"] for f in schema_fields])
        labels = "\n".join(f'  "{f["key"]}": "{f["label"]}"' for f in schema_fields)

        prompt_parts = [
            "Extract information from the provided KYC documents.",
            "Return a single flat JSON object where each key is a field name and the value is the extracted text string.",
            "Leave a field as an empty string \"\" if it cannot be found.",
            "Use EXACTLY these field keys — do not add, rename, or omit any:",
            keys_only,
            "",
            "Field descriptions:",
            labels,
        ]

        if pdf_texts:
            prompt_parts.append("\nText extracted from PDF documents:")
            for text in pdf_texts:
                prompt_parts.append(text)

        prompt_parts.append("\nReturn ONLY the flat JSON object. No markdown, no explanation.")
        user_content = "\n".join(prompt_parts)

        message: dict[str, Any] = {"role": "user", "content": user_content}
        if images_b64:
            message["images"] = images_b64

        ollama_base = settings.LOCAL_MODEL_ENDPOINT.replace("/v1", "").rstrip("/")
        payload = {
            "model": settings.VISION_MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a KYC document data extraction assistant. "
                        "Extract client information from the provided documents. "
                        "Return ONLY a valid JSON object — no markdown, no explanation."
                    ),
                },
                message,
            ],
            "stream": True,
        }

        logger.info(
            f"ai_extraction: calling {settings.VISION_MODEL_NAME} at {ollama_base} "
            f"with {len(images_b64)} image(s) and {len(pdf_texts)} PDF text(s)"
        )

        # stream=true keeps the HTTP connection alive while the model generates tokens.
        # read=None disables per-chunk read timeout — the first token from a vision model
        # on CPU can take several minutes; any finite read timeout fires before it arrives.
        # asyncio.wait_for provides the hard outer cap (10 min) to prevent infinite hangs.
        timeout = httpx.Timeout(connect=10.0, read=None, write=120.0, pool=5.0)
        url = f"{ollama_base}/api/chat"

        async def _stream() -> str:
            content = ""
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        logger.error(
                            f"ai_extraction: Ollama HTTP {resp.status_code}: {body[:500]}"
                        )
                        resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            content += chunk.get("message", {}).get("content", "")
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            return content

        full_content = await asyncio.wait_for(_stream(), timeout=600.0)

        if not full_content:
            raise ValueError("Ollama returned an empty response")
        return full_content

    def _parse_response(
        self,
        response_text: str,
        schema_fields: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        valid_keys = {f["key"] for f in schema_fields}

        # Strip markdown code fences if present
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", response_text).strip()

        try:
            parsed: dict[str, Any] = json.loads(clean)
        except json.JSONDecodeError:
            # Try to extract just the JSON object from the response
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if not match:
                logger.warning("ai_extraction: could not find JSON in model response")
                return []
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("ai_extraction: JSON parse failed after extraction attempt")
                return []

        _EMPTY = {"", "null", "none", "n/a", "unknown", "not found", "not available"}

        results: list[dict[str, Any]] = []
        for key, val in parsed.items():
            if key not in valid_keys:
                continue
            # Accept both flat strings ("MOHAMED") and nested {"value": "MOHAMED", "confidence": 0.9}
            if isinstance(val, dict):
                value = str(val.get("value", "")).strip()
                confidence = float(val.get("confidence", 0.85))
            else:
                value = str(val).strip()
                confidence = 0.85  # fixed confidence for flat-format responses
            if value.lower() not in _EMPTY:
                results.append({"key": key, "value": value, "confidence": confidence})

        logger.info(f"ai_extraction: parsed {len(results)} fields from model response")
        return results

    def _mock_extraction(self, schema_fields: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Return plausible mock values for all schema fields when the vision model is unavailable."""
        # Load mock values from external JSON file in the `mocks/` folder.
        mock_file = Path(__file__).resolve().parent / "mocks" / "document_field_extraction.json"
        try:
            if mock_file.exists():
                with mock_file.open("r", encoding="utf-8") as fh:
                    _MOCK_VALUES: dict[str, Any] = json.load(fh)
            else:
                _MOCK_VALUES = {}
        except Exception as exc:
            logger.warning(f"ai_extraction: failed to load mock values from {mock_file}: {exc}")
            _MOCK_VALUES = {}

        results: list[dict[str, Any]] = []
        for field in schema_fields:
            key = field["key"]
            key_lower = key.lower()
            mock_value: Any | None = None
            # Prefer exact key match
            if key_lower in _MOCK_VALUES:
                mock_value = _MOCK_VALUES[key_lower]
            else:
                # Fallback to substring matches
                for k, v in _MOCK_VALUES.items():
                    if k in key_lower or key_lower in k:
                        mock_value = v
                        break
            if mock_value is None:
                mock_value = f"Mock {field['label']}"

            # Ensure the returned value is a string (Pydantic expects string type).
            if isinstance(mock_value, list):
                mock_value = ", ".join(str(i) for i in mock_value)
            elif isinstance(mock_value, dict):
                # Prefer an inner `value` key when present, otherwise JSON-serialize.
                if "value" in mock_value:
                    mock_value = str(mock_value.get("value", ""))
                else:
                    try:
                        mock_value = json.dumps(mock_value)
                    except Exception:
                        mock_value = str(mock_value)
            else:
                mock_value = str(mock_value)

            results.append({"key": key, "value": mock_value, "confidence": 0.85})

        logger.warning(
            f"ai_extraction: returning mock data for {len(results)} field(s) — "
            "vision model unavailable"
        )
        return results


ai_extraction_service = AIExtractionService()
