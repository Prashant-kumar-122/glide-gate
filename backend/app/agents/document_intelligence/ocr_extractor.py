from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.agents.document_intelligence.document_classifier import DocumentCategory


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


class OcrExtractor:
    """
    Simulated OCR extractor (BRD FR-06, STEP-07).

    Returns deterministic field extractions keyed by document category.
    Real implementation replaced by MCP Document Management connector in STEP-16.
    Adds 100–600 ms simulated latency.
    """

    async def extract(
        self,
        document_id: UUID | None,
        filename: str,
        category: DocumentCategory,
        file_bytes: bytes | None = None,
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
            sum(f.confidence for f in fields) / len(fields)
            if fields
            else 0.0,
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
