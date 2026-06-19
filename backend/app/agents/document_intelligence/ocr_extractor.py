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

def _build_simulated_templates(client_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build per-category OCR templates from the case's shared_context.client_data."""
    first = client_data.get("first_name", "")
    last = client_data.get("last_name", "")
    full_name = f"{first} {last}".strip() or "Unknown Client"

    dob = client_data.get("date_of_birth", "")
    id_number = client_data.get("id_number", "")
    id_expiry = client_data.get("id_expiration_date", "")
    id_type = client_data.get("id_type", "Passport")
    nationality = client_data.get(
        "country_of_citizenship", client_data.get("tax_residency_country", "")
    )

    tin = (
        client_data.get("social_security_number")
        or client_data.get("large_trader_id_number")
        or ""
    )
    tax_residency = client_data.get("tax_residency_country", "")
    pep_raw = str(client_data.get("is_senior_political_figure", "No")).lower()
    pep = "No" if pep_raw in ("no", "false", "0", "") else "Yes"

    occupation = client_data.get("occupation", "")
    employer = client_data.get("employer_name", "")
    income = client_data.get("annual_income", "")
    source_of_funds = client_data.get("source_of_funds", "")
    country = client_data.get("country", "")

    address = ", ".join(
        p for p in [
            client_data.get("address_line_1", ""),
            client_data.get("city", ""),
            client_data.get("state", ""),
            client_data.get("postal_code", ""),
            country,
        ]
        if p
    )

    return {
        "identity": {
            "raw": (
                f"{id_type.upper()}\nSurname: {last.upper()}\nGiven Names: {first.upper()}\n"
                f"Nationality: {nationality}\nDate of Birth: {dob}\n"
                f"Date of Expiry: {id_expiry}\n{id_type} No: {id_number}\n"
                f"Address: {address}\nPhoto: Present\n"
            ),
            "fields": [
                ("full_name", full_name),
                ("nationality", nationality),
                ("date_of_birth", dob),
                ("document_number", id_number),
                ("id_number", id_number),
                ("expiry_date", id_expiry),
                ("photo", "Present"),
            ],
        },
        "financial": {
            "raw": (
                f"ACCOUNT STATEMENT\nAccount Holder: {full_name}\n"
                f"Statement Period: Recent 3 months\nClosing Balance: Present\n"
                f"Bank: Financial Institution\n"
                f"Annual Income: {income}\nSource of Funds: {source_of_funds}\n"
            ),
            "fields": [
                ("account_holder", full_name),
                ("statement_period", "Recent 3 months"),
                ("closing_balance", "Present"),
                ("bank_name", "Financial Institution"),
                ("annual_income", income),
                ("source_of_funds", source_of_funds),
            ],
        },
        "legal": {
            "raw": (
                f"LEGAL DOCUMENT\nGrantor / Donor: {full_name}\n"
                f"Attorney / Trustee: Present\nEstablishment Date: Present\n"
                f"Governing Jurisdiction: {country}\nAddress: {address}\n"
            ),
            "fields": [
                ("full_name", full_name),
                ("grantor", full_name),
                ("attorney", "Present"),
                ("establishment_date", "Present"),
                ("governing_jurisdiction", country),
            ],
        },
        "compliance": {
            "raw": (
                f"KYC / COMPLIANCE FORM\nClient Name: {full_name}\n"
                f"Date of Birth: {dob}\nTax Residency: {tax_residency}\nTIN: {tin}\n"
                f"Politically Exposed Person: {pep}\n"
                f"Occupation: {occupation}\nEmployer: {employer}\n"
                f"Source of Funds: {source_of_funds}\n"
                f"Date Completed: Present\nSignature: Present\n"
            ),
            "fields": [
                ("client_name", full_name),
                ("tax_residency", tax_residency),
                ("tin", tin),
                ("pep", pep),
                ("occupation", occupation),
                ("employer", employer),
                ("source_of_funds", source_of_funds),
                ("date_completed", "Present"),
                ("signature", "Present"),
            ],
        },
        "insurance": {
            "raw": (
                f"INSURANCE POLICY\nPolicyholder: {full_name}\n"
                f"Policy Number: Present\nSum Assured: Present\n"
                f"Insurer: Present\nPolicy Expiry: Present\n"
            ),
            "fields": [
                ("policyholder", full_name),
                ("policy_number", "Present"),
                ("sum_assured", "Present"),
                ("insurer", "Present"),
                ("expiry_date", "Present"),
            ],
        },
        "entity": {
            "raw": (
                f"COMPANY REGISTRATION\nCompany Name: Present\n"
                f"Registration Number: Present\nRegistration Date: Present\n"
                f"Status: Active\nDirectors: {full_name}\nBeneficial Owners: {full_name}\n"
            ),
            "fields": [
                ("company_name", "Present"),
                ("registration_number", "Present"),
                ("registration_date", "Present"),
                ("status", "Active"),
                ("directors", full_name),
                ("beneficial_owners", full_name),
            ],
        },
        "unknown": {
            "raw": "Document content could not be classified.",
            "fields": [],
        },
    }


# Fallback templates used when no client_data is available (e.g. unit tests,
# direct agent calls that don't carry a case context).
_FALLBACK_TEMPLATES: dict[str, dict[str, Any]] = {
    "identity": {
        "raw": "IDENTITY DOCUMENT\nFull Name: Present\nDate of Birth: Present\nDocument Number: Present\nExpiry Date: Present\nNationality: Present\nPhoto: Present\n",
        "fields": [
            ("full_name", "Present"),
            ("date_of_birth", "Present"),
            ("document_number", "Present"),
            ("expiry_date", "Present"),
            ("nationality", "Present"),
            ("photo", "Present"),
        ],
    },
    "financial": {
        "raw": "FINANCIAL DOCUMENT\nAccount Holder: Present\nStatement Period: Present\nClosing Balance: Present\nBank: Present\n",
        "fields": [
            ("account_holder", "Present"),
            ("statement_period", "Present"),
            ("closing_balance", "Present"),
            ("bank_name", "Present"),
        ],
    },
    "legal": {
        "raw": "LEGAL DOCUMENT\nGrantor: Present\nAttorney: Present\nEstablishment Date: Present\nGoverning Jurisdiction: Present\n",
        "fields": [
            ("grantor", "Present"),
            ("attorney", "Present"),
            ("establishment_date", "Present"),
            ("governing_jurisdiction", "Present"),
        ],
    },
    "compliance": {
        "raw": "COMPLIANCE FORM\nClient Name: Present\nTax Residency: Present\nTIN: Present\nPEP: No\nDate Completed: Present\nSignature: Present\n",
        "fields": [
            ("client_name", "Present"),
            ("tax_residency", "Present"),
            ("tin", "Present"),
            ("pep", "No"),
            ("date_completed", "Present"),
            ("signature", "Present"),
        ],
    },
    "insurance": {
        "raw": "INSURANCE POLICY\nPolicyholder: Present\nPolicy Number: Present\nSum Assured: Present\nInsurer: Present\nExpiry Date: Present\n",
        "fields": [
            ("policyholder", "Present"),
            ("policy_number", "Present"),
            ("sum_assured", "Present"),
            ("insurer", "Present"),
            ("expiry_date", "Present"),
        ],
    },
    "entity": {
        "raw": "ENTITY DOCUMENT\nCompany Name: Present\nRegistration Number: Present\nRegistration Date: Present\nStatus: Active\nDirectors: Present\n",
        "fields": [
            ("company_name", "Present"),
            ("registration_number", "Present"),
            ("registration_date", "Present"),
            ("status", "Active"),
            ("directors", "Present"),
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
        client_data: dict[str, Any] | None = None,
    ) -> OcrResult:
        if file_bytes:
            try:
                return await self._llm_extract(document_id, filename, category, file_bytes)
            except Exception as exc:
                logger.warning(
                    f"[OcrExtractor] LLM extraction failed for {filename}: {exc!r}; "
                    "falling back to simulated"
                )
        return await self._simulated_extract(document_id, filename, category, client_data)

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
        client_data: dict[str, Any] | None = None,
    ) -> OcrResult:
        latency = random.uniform(0.1, 0.6)
        await asyncio.sleep(latency)

        templates = (
            _build_simulated_templates(client_data)
            if client_data
            else _FALLBACK_TEMPLATES
        )
        template = templates.get(category, templates["unknown"])
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
