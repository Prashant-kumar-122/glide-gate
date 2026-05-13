from __future__ import annotations

import hashlib
import random
import uuid
from datetime import datetime
from typing import Any


# Simulated document storage — keyed by document_id
_DOCUMENT_STORE: dict[str, dict[str, Any]] = {}

# OCR field templates per document category (mirrors OcrExtractor from STEP-07)
_OCR_TEMPLATES: dict[str, list[str]] = {
    "identity": ["full_name", "date_of_birth", "nationality", "document_number", "issue_date", "expiry_date"],
    "financial": ["account_holder", "institution", "account_number", "statement_period", "opening_balance", "closing_balance", "total_credits", "total_debits"],
    "legal": ["document_title", "parties_involved", "effective_date", "jurisdiction", "governing_law"],
    "insurance": ["policy_number", "insured_name", "policy_type", "coverage_amount", "premium", "policy_start", "policy_end"],
    "compliance": ["client_name", "risk_rating", "compliance_officer", "review_date", "findings", "outcome"],
    "entity": ["entity_name", "registration_number", "jurisdiction", "registered_address", "directors", "shareholders"],
}

_QUALITY_LEVELS = ["HIGH", "HIGH", "HIGH", "MEDIUM", "MEDIUM", "LOW"]


def _seed_from(value: str) -> random.Random:
    digest = int(hashlib.md5(value.encode()).hexdigest(), 16)
    return random.Random(digest)


def simulate_upload_document(inputs: dict[str, Any]) -> dict[str, Any]:
    file_name: str = inputs.get("file_name", "document.pdf")
    file_size: int = int(inputs.get("file_size", 204800))
    content_type: str = inputs.get("content_type", "application/pdf")
    document_category: str = inputs.get("document_category", "identity")
    case_id: str = str(inputs.get("case_id", ""))

    doc_id = str(uuid.uuid4())
    checksum = hashlib.sha256(f"{file_name}:{file_size}:{case_id}".encode()).hexdigest()
    storage_url = f"s3://glide-gate-documents/{case_id}/{doc_id}/{file_name}"
    uploaded_at = datetime.utcnow().isoformat()

    record = {
        "document_id": doc_id,
        "file_name": file_name,
        "file_size": file_size,
        "content_type": content_type,
        "document_category": document_category,
        "case_id": case_id,
        "storage_url": storage_url,
        "checksum": checksum,
        "status": "RECEIVED",
        "uploaded_at": uploaded_at,
    }
    _DOCUMENT_STORE[doc_id] = record

    return {
        "document_id": doc_id,
        "storage_url": storage_url,
        "upload_status": "SUCCESS",
        "checksum": checksum,
        "uploaded_at": uploaded_at,
        "provider": "GlideDocs-SIM",
    }


def simulate_retrieve_document(inputs: dict[str, Any]) -> dict[str, Any]:
    doc_id: str = str(inputs.get("document_id", ""))

    if doc_id in _DOCUMENT_STORE:
        record = _DOCUMENT_STORE[doc_id]
        return {
            "document_id": doc_id,
            "file_name": record["file_name"],
            "content_type": record["content_type"],
            "storage_url": record["storage_url"],
            "file_size": record["file_size"],
            "checksum": record["checksum"],
            "document_category": record["document_category"],
            "status": record["status"],
            "download_url": f"{record['storage_url']}?token=sim-{doc_id[:8]}",
            "provider": "GlideDocs-SIM",
        }

    # Simulate a generic document for IDs not in the in-memory store
    rng = _seed_from(doc_id)
    return {
        "document_id": doc_id,
        "file_name": "document.pdf",
        "content_type": "application/pdf",
        "storage_url": f"s3://glide-gate-documents/unknown/{doc_id}/document.pdf",
        "file_size": rng.randint(50000, 2000000),
        "checksum": hashlib.sha256(doc_id.encode()).hexdigest(),
        "document_category": "identity",
        "status": "RECEIVED",
        "download_url": f"s3://glide-gate-documents/unknown/{doc_id}/document.pdf?token=sim-{doc_id[:8]}",
        "provider": "GlideDocs-SIM",
    }


def simulate_get_document_status(inputs: dict[str, Any]) -> dict[str, Any]:
    doc_id: str = str(inputs.get("document_id", ""))

    if doc_id in _DOCUMENT_STORE:
        record = _DOCUMENT_STORE[doc_id]
        return {
            "document_id": doc_id,
            "status": record["status"],
            "last_updated": datetime.utcnow().isoformat(),
            "reviewer_id": None,
            "provider": "GlideDocs-SIM",
        }

    rng = _seed_from(doc_id)
    statuses = ["RECEIVED", "UNDER_REVIEW", "APPROVED"]
    status = rng.choice(statuses)
    return {
        "document_id": doc_id,
        "status": status,
        "last_updated": datetime.utcnow().isoformat(),
        "reviewer_id": f"REV-{rng.randint(1000, 9999)}" if status != "RECEIVED" else None,
        "provider": "GlideDocs-SIM",
    }


def simulate_extract_ocr(inputs: dict[str, Any]) -> dict[str, Any]:
    doc_id: str = str(inputs.get("document_id", ""))
    document_category: str = inputs.get("document_category", "identity").lower()

    rng = _seed_from(f"ocr:{doc_id}")
    fields = _OCR_TEMPLATES.get(document_category, _OCR_TEMPLATES["identity"])
    confidence = round(rng.uniform(0.78, 0.99), 4)
    quality = _QUALITY_LEVELS[min(int((1 - confidence) * 10), len(_QUALITY_LEVELS) - 1)]

    extracted: dict[str, Any] = {}
    for field in fields:
        field_confidence = round(min(confidence + rng.uniform(-0.05, 0.05), 1.0), 4)
        extracted[field] = {
            "value": f"[SIM_{field.upper()}]",
            "confidence": field_confidence,
            "bounding_box": {
                "x": rng.randint(10, 400),
                "y": rng.randint(10, 600),
                "width": rng.randint(80, 300),
                "height": rng.randint(12, 30),
            },
        }

    return {
        "document_id": doc_id,
        "document_category": document_category,
        "extracted_fields": extracted,
        "confidence": confidence,
        "extraction_quality": quality,
        "pages_processed": rng.randint(1, 4),
        "extracted_at": datetime.utcnow().isoformat(),
        "provider": "GlideOCR-SIM",
    }
