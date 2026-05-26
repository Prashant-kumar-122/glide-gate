from __future__ import annotations

import asyncio
import base64
import io
import json
import mimetypes
import random
import re
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from loguru import logger
from pydantic import BaseModel

from app.agents.document_intelligence.document_classifier import DocumentCategory
from app.config import settings


class OcrField(BaseModel):
    key: str
    value: str
    confidence: float  # 0.0–1.0


class OcrResult(BaseModel):
    extraction_id: UUID
    document_id: UUID | None
    raw_text: str
    fields: list[OcrField]
    page_count: int
    language: str = "en"
    extraction_quality: float   # 0.0–1.0 (avg field confidence)
    latency_ms: int
    extracted_at: str
    is_simulated: bool = True


_OCR_SYSTEM_PROMPT = """\
You are a precise document OCR engine for GlideGate, a wealth management platform.
Extract all identifiable fields from the provided document.

Respond ONLY with a JSON object matching this schema:
{
  "raw_text": "<all visible text concatenated>",
  "fields": [
    {"key": "<snake_case_field_name>", "value": "<extracted value>", "confidence": <0.0-1.0>}
  ]
}

Rules:
- Extract every identifiable field (names, dates, numbers, addresses, IDs, amounts, etc.)
- Use descriptive snake_case keys (full_name, date_of_birth, document_number, expiry_date, etc.)
- confidence: 0.9+ if clearly legible, 0.6-0.9 if partially legible, below 0.6 if uncertain
- Do not add commentary outside the JSON object
"""

_CATEGORY_TEMPLATES: dict[str, dict[str, Any]] = {
    "identity": {
        "raw": (
            "PASSPORT\nSurname: MEHTA\nGiven Names: AARAV KUMAR\n"
            "Nationality: INDIAN\nDate of Birth: 15 JAN 1985\n"
            "Place of Birth: MUMBAI, INDIA\nDate of Issue: 10 MAR 2020\n"
            "Date of Expiry: 09 MAR 2030\nPassport No: J8342910\n"
            "Photo: Present\n"
        ),
        "fields": [
            ("full_name", "Aarav Kumar Mehta"),
            ("nationality", "Indian"),
            ("date_of_birth", "15 Jan 1985"),
            ("document_number", "J8342910"),
            ("issue_date", "10 Mar 2020"),
            ("expiry_date", "09 Mar 2030"),
            ("photo", "Present"),
        ],
    },
    "financial": {
        "raw": (
            "ACCOUNT STATEMENT\nAccount Holder: Aarav Kumar Mehta\n"
            "Account Number: ****-****-****-4821\nStatement Period: 01 Jan 2025 – 31 Mar 2025\n"
            "Opening Balance: SGD 125,430.00\nClosing Balance: SGD 148,960.50\n"
            "Total Credits: SGD 47,250.00\nTotal Debits: SGD 23,719.50\n"
            "Bank: DBS Bank Limited\n"
        ),
        "fields": [
            ("account_holder", "Aarav Kumar Mehta"),
            ("account_number", "****-****-****-4821"),
            ("period_from", "01 Jan 2025"),
            ("period_to", "31 Mar 2025"),
            ("closing_balance", "SGD 148,960.50"),
            ("bank_name", "DBS Bank Limited"),
        ],
    },
    "legal": {
        "raw": (
            "TRUST DEED\nTrust Name: Mehta Family Trust\nTrustee: Aarav Kumar Mehta\n"
            "Beneficiaries: Priya Mehta, Arjun Mehta\nEstablishment Date: 05 Feb 2018\n"
            "Governing Law: Singapore\nRegistration Number: T18TT12345A\n"
        ),
        "fields": [
            ("trust_name", "Mehta Family Trust"),
            ("trustee", "Aarav Kumar Mehta"),
            ("beneficiary", "Priya Mehta, Arjun Mehta"),
            ("establishment_date", "05 Feb 2018"),
            ("registration_number", "T18TT12345A"),
        ],
    },
    "compliance": {
        "raw": (
            "KYC FORM\nClient Name: Aarav Kumar Mehta\nDate of Birth: 15 Jan 1985\n"
            "Tax Residency: Singapore\nTIN: S1234567D\n"
            "Politically Exposed Person: No\nUSA Person: No\nDate Completed: 15 May 2025\n"
        ),
        "fields": [
            ("client_name", "Aarav Kumar Mehta"),
            ("tax_residency", "Singapore"),
            ("tin", "S1234567D"),
            ("pep", "No"),
            ("date_completed", "15 May 2025"),
        ],
    },
    "insurance": {
        "raw": (
            "LIFE INSURANCE POLICY\nPolicyholder: Aarav Kumar Mehta\nPolicy Number: LI-2022-884321\n"
            "Sum Assured: SGD 1,000,000\nAnnual Premium: SGD 8,400\n"
            "Commencement Date: 01 Jul 2022\nExpiry Date: 30 Jun 2042\nInsurer: Great Eastern Life\n"
        ),
        "fields": [
            ("policyholder", "Aarav Kumar Mehta"),
            ("policy_number", "LI-2022-884321"),
            ("sum_assured", "SGD 1,000,000"),
            ("expiry_date", "30 Jun 2042"),
            ("insurer", "Great Eastern Life"),
        ],
    },
    "entity": {
        "raw": (
            "COMPANY REGISTRATION\nCompany Name: Mehta Ventures Pte. Ltd.\n"
            "UEN: 202012345K\nRegistration Date: 12 Jun 2020\nStatus: Live\n"
            "Registered Address: 1 Raffles Place, #40-01, Singapore 048616\n"
            "Directors: Aarav Kumar Mehta\nShareholding: Aarav Kumar Mehta 100%\n"
        ),
        "fields": [
            ("company_name", "Mehta Ventures Pte. Ltd."),
            ("uen", "202012345K"),
            ("registration_date", "12 Jun 2020"),
            ("status", "Live"),
            ("directors", "Aarav Kumar Mehta"),
        ],
    },
    "unknown": {
        "raw": "Document content could not be classified.",
        "fields": [],
    },
}


def _detect_mime(file_bytes: bytes, filename: str) -> str:
    if file_bytes[:4] == b"%PDF":
        return "application/pdf"
    if file_bytes[:2] == b"\xff\xd8":
        return "image/jpeg"
    if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if file_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(file_bytes) > 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "image/webp"
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _resize_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """Downscale to max_size on the longest side and re-encode as JPEG."""
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue()
    except Exception as exc:
        logger.warning(f"[OcrExtractor] Image resize failed, using original: {exc}")
        return image_bytes


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        logger.warning(f"[OcrExtractor] PDF text extraction failed: {exc}")
        return ""


def _parse_llm_response(raw: str) -> dict[str, Any]:
    clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


class OcrExtractor:
    """
    Extracts document fields using the configured vision model (VISION_MODEL_NAME).

    When file_bytes are provided the real LLM path runs:
    - Images (JPEG, PNG, GIF, WEBP) → resized and sent to the vision model.
    - PDFs → text extracted via pypdf first; if the PDF is a scanned image the
      first embedded image page is sent to the vision model instead.

    Falls back to deterministic simulated data when file_bytes are absent or
    when the LLM call fails, so the rest of the pipeline is never blocked.
    """

    async def extract(
        self,
        document_id: UUID | None,
        filename: str,
        category: DocumentCategory,
        file_bytes: bytes | None = None,
    ) -> OcrResult:
        if file_bytes:
            try:
                return await self._llm_extract(document_id, filename, category, file_bytes)
            except Exception as exc:
                logger.warning(
                    f"[OcrExtractor] LLM extraction failed for {filename}: {exc!r}; "
                    "falling back to simulated"
                )
        return await self._simulated_extract(document_id, filename, category)

    # ── Real LLM extraction ───────────────────────────────────────────────────

    async def _llm_extract(
        self,
        document_id: UUID | None,
        filename: str,
        category: DocumentCategory,
        file_bytes: bytes,
    ) -> OcrResult:
        import time
        t0 = time.monotonic()

        mime = _detect_mime(file_bytes, filename)
        logger.info(f"[OcrExtractor] LLM extraction: file={filename} mime={mime}")

        image_b64: str | None = None
        text_content: str | None = None

        if mime.startswith("image/"):
            resized = _resize_image(file_bytes)
            image_b64 = base64.b64encode(resized).decode()
        elif mime == "application/pdf":
            pdf_text = _extract_pdf_text(file_bytes).strip()
            if len(pdf_text) > 50:
                text_content = pdf_text
            else:
                # Scanned PDF: extract the first embedded image
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                for page in reader.pages:
                    for img in page.images:
                        resized = _resize_image(img.data)
                        image_b64 = base64.b64encode(resized).decode()
                        break
                    if image_b64:
                        break
                if not image_b64:
                    raise ValueError("Scanned PDF has no extractable images")
        else:
            raise ValueError(f"Unsupported file type: {mime}")

        data = await self._call_model(image_b64=image_b64, text_content=text_content)
        latency_ms = round((time.monotonic() - t0) * 1000)

        raw_text: str = data.get("raw_text", "")
        fields = [
            OcrField(
                key=str(f["key"]),
                value=str(f["value"]),
                confidence=float(f.get("confidence", 0.85)),
            )
            for f in data.get("fields", [])
            if isinstance(f, dict) and "key" in f and "value" in f
        ]
        quality = (
            round(sum(f.confidence for f in fields) / len(fields), 4) if fields else 0.5
        )

        logger.info(
            f"[OcrExtractor] Extracted {len(fields)} fields in {latency_ms}ms "
            f"(quality={quality})"
        )
        return OcrResult(
            extraction_id=uuid4(),
            document_id=document_id,
            raw_text=raw_text,
            fields=fields,
            page_count=1,
            extraction_quality=quality,
            latency_ms=latency_ms,
            extracted_at=datetime.utcnow().isoformat(),
            is_simulated=False,
        )

    async def _call_model(
        self,
        image_b64: str | None,
        text_content: str | None,
    ) -> dict[str, Any]:
        """Call Ollama's native /api/chat — same pattern as AIExtractionService."""
        user_text = (
            _OCR_SYSTEM_PROMPT + "\n\nExtract all fields from this document."
            if image_b64
            else _OCR_SYSTEM_PROMPT + f"\n\nExtract all fields from this document text:\n\n{text_content}"
        )
        message: dict[str, Any] = {"role": "user", "content": user_text}
        if image_b64:
            message["images"] = [image_b64]

        ollama_base = settings.LOCAL_MODEL_ENDPOINT.replace("/v1", "").rstrip("/")
        payload = {
            "model": settings.VISION_MODEL_NAME,
            "messages": [message],
            "stream": True,
        }

        logger.info(
            f"[OcrExtractor] Calling {settings.VISION_MODEL_NAME} at {ollama_base} "
            f"({'image' if image_b64 else 'text'} mode)"
        )

        timeout = httpx.Timeout(connect=10.0, read=None, write=120.0, pool=5.0)

        async def _stream() -> str:
            content = ""
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST", f"{ollama_base}/api/chat", json=payload
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        logger.error(
                            f"[OcrExtractor] Ollama HTTP {resp.status_code}: {body[:500]}"
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

        return _parse_llm_response(full_content)

    # ── Simulated fallback ────────────────────────────────────────────────────

    async def _simulated_extract(
        self,
        document_id: UUID | None,
        filename: str,
        category: DocumentCategory,
    ) -> OcrResult:
        latency = random.uniform(0.1, 0.6)
        await asyncio.sleep(latency)

        template = _CATEGORY_TEMPLATES.get(category, _CATEGORY_TEMPLATES["unknown"])
        raw_text: str = template["raw"]

        rng = random.Random(str(document_id) + filename)
        fields = [
            OcrField(
                key=k,
                value=v,
                confidence=round(rng.uniform(0.88, 0.99), 4),
            )
            for k, v in template["fields"]
        ]
        quality = round(
            sum(f.confidence for f in fields) / len(fields) if fields else 0.0,
            4,
        )

        return OcrResult(
            extraction_id=uuid4(),
            document_id=document_id,
            raw_text=raw_text,
            fields=fields,
            page_count=rng.randint(1, 3),
            extraction_quality=quality,
            latency_ms=round(latency * 1000),
            extracted_at=datetime.utcnow().isoformat(),
        )
