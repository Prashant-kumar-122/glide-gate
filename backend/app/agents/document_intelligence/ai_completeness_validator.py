from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.agents.document_intelligence.document_classifier import DocumentCategory
from app.agents.document_intelligence.ocr_extractor import OcrResult


class FindingSeverity(str):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class FindingResult(BaseModel):
    field: str
    severity: Literal["pass", "warn", "fail"]
    message: str
    suggestion: str | None = None


class ValidationResult(BaseModel):
    validation_id: UUID
    document_id: UUID | None
    category: DocumentCategory
    overall_status: Literal["pass", "warn", "fail"]
    findings: list[FindingResult]
    completeness_pct: float     # 0.0–100.0
    validated_at: str
    prompt_used: str = ""       # editable prompt stored for audit
    llm_used: bool = False


# ── Default validation prompts per category ───────────────────────────────────
# These are returned from DB in STEP-28; here they are the hardcoded defaults.

_DEFAULT_PROMPTS: dict[str, dict[str, Any]] = {
    "identity": {
        "goal": "Verify the identity document is complete, valid, and not expired.",
        "factors": [
            "full_name is present and legible",
            "date_of_birth is present",
            "document_number / id_number is present",
            "expiry_date is present and the document is not expired",
            "nationality is present",
            "photo or biometric data noted",
        ],
    },
    "financial": {
        "goal": "Confirm the financial document covers a recent period and includes account/balance details.",
        "factors": [
            "account_holder name matches client",
            "statement period is within the last 3 months",
            "closing_balance is present",
            "bank or institution name is present",
            "no evidence of alteration",
        ],
    },
    "legal": {
        "goal": "Ensure the legal document is properly executed and relevant parties are identified.",
        "factors": [
            "document is signed/executed",
            "relevant parties (trustee/beneficiary or grantor/attorney) are named",
            "establishment or execution date is present",
            "governing jurisdiction is stated",
            "document is not expired (if applicable)",
        ],
    },
    "insurance": {
        "goal": "Confirm insurance policy details are complete and coverage is active.",
        "factors": [
            "policyholder name matches client",
            "policy_number is present",
            "sum_assured or coverage amount is stated",
            "policy is not expired",
            "insurer name is present",
        ],
    },
    "compliance": {
        "goal": "Verify the compliance form is fully completed and signed.",
        "factors": [
            "client_name is present",
            "tax_residency is declared",
            "TIN or NRIC is provided",
            "PEP declaration is answered",
            "date_completed is present",
            "signature or confirmation is noted",
        ],
    },
    "entity": {
        "goal": "Confirm corporate entity documents establish current legal standing.",
        "factors": [
            "company_name is present",
            "registration_number / UEN is present",
            "registration_date is present",
            "current status is Live or Active",
            "directors or beneficial owners are identified",
        ],
    },
    "unknown": {
        "goal": "Attempt basic completeness check on unclassified document.",
        "factors": ["Document contains readable text", "At least one identifying field extracted"],
    },
}

_SYSTEM_PROMPT = """\
You are a meticulous compliance document reviewer for GlideGate, a wealth management platform.
Your task is to evaluate whether a financial onboarding document is complete and valid.

Respond ONLY with a JSON array of finding objects matching this schema:
[
  {
    "field": "<field name or area assessed>",
    "severity": "pass" | "warn" | "fail",
    "message": "<concise observation>",
    "suggestion": "<optional remediation step>"
  }
]

Rules:
- "pass"  = requirement is clearly met
- "warn"  = requirement is partially met or unclear — document may still be usable
- "fail"  = requirement is missing or clearly not met — document should be rejected/revised
- Return one finding per factor in the prompt
- Do not add commentary outside the JSON array
"""


class AICompletenessValidator:
    """
    Validates document completeness using the Anthropic LLM (BRD FR-08, FR-09).

    Falls back to a heuristic rule-based validation when the API is unavailable
    so demos function without a live Anthropic key.
    """

    def __init__(self) -> None:
        self._anthropic: Any = None

    def _get_client(self) -> Any:
        if self._anthropic is None:
            try:
                import anthropic  # type: ignore[import]
                from app.config import settings

                if settings.ANTHROPIC_API_KEY:
                    self._anthropic = anthropic.AsyncAnthropic(
                        api_key=settings.ANTHROPIC_API_KEY
                    )
            except Exception:
                pass
        return self._anthropic

    async def validate(
        self,
        ocr_result: OcrResult,
        category: DocumentCategory,
        custom_prompt: dict[str, Any] | None = None,
    ) -> ValidationResult:
        prompt_cfg = custom_prompt or _DEFAULT_PROMPTS.get(
            category, _DEFAULT_PROMPTS["unknown"]
        )

        findings = await self._llm_validate(ocr_result, prompt_cfg)
        if not findings:
            findings = self._heuristic_validate(ocr_result, prompt_cfg)

        pass_count = sum(1 for f in findings if f.severity == "pass")
        fail_count = sum(1 for f in findings if f.severity == "fail")
        warn_count = sum(1 for f in findings if f.severity == "warn")

        completeness_pct = (
            round(pass_count / len(findings) * 100, 1) if findings else 0.0
        )

        if fail_count > 0:
            overall = "fail"
        elif warn_count > 0:
            overall = "warn"
        else:
            overall = "pass"

        return ValidationResult(
            validation_id=uuid4(),
            document_id=ocr_result.document_id,
            category=category,
            overall_status=overall,
            findings=findings,
            completeness_pct=completeness_pct,
            validated_at=datetime.utcnow().isoformat(),
            prompt_used=json.dumps(prompt_cfg),
            llm_used=self._anthropic is not None,
        )

    async def _llm_validate(
        self, ocr_result: OcrResult, prompt_cfg: dict[str, Any]
    ) -> list[FindingResult]:
        client = self._get_client()
        if client is None:
            return []

        extracted_summary = "\n".join(
            f"  {f.key}: {f.value} (confidence {f.confidence:.2f})"
            for f in ocr_result.fields
        )
        if not extracted_summary:
            extracted_summary = ocr_result.raw_text[:800]

        factors_text = "\n".join(f"- {factor}" for factor in prompt_cfg.get("factors", []))
        user_message = (
            f"Goal: {prompt_cfg.get('goal', '')}\n\n"
            f"Factors to assess:\n{factors_text}\n\n"
            f"Extracted document fields:\n{extracted_summary}\n\n"
            "Return your assessment as a JSON array only."
        )

        try:
            from app.config import settings

            resp = await client.messages.create(
                model=settings.PRIMARY_LLM_MODEL,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
                temperature=0.2,
            )
            raw = resp.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return [FindingResult(**item) for item in data]
        except Exception:
            return []

    def _heuristic_validate(
        self, ocr_result: OcrResult, prompt_cfg: dict[str, Any]
    ) -> list[FindingResult]:
        extracted_keys = {f.key.lower() for f in ocr_result.fields}
        factors = prompt_cfg.get("factors", [])
        findings: list[FindingResult] = []

        for factor in factors:
            # Derive a key name from the factor text for a rough match
            factor_lower = factor.lower()
            matched = any(key in factor_lower or factor_lower in key for key in extracted_keys)

            if matched:
                findings.append(FindingResult(
                    field=factor,
                    severity="pass",
                    message="Field present in extracted document data.",
                ))
            elif "not expired" in factor_lower or "valid" in factor_lower:
                findings.append(FindingResult(
                    field=factor,
                    severity="warn",
                    message="Expiry/validity could not be automatically verified.",
                    suggestion="Please confirm expiry date is in the future.",
                ))
            elif ocr_result.extraction_quality < 0.7:
                findings.append(FindingResult(
                    field=factor,
                    severity="warn",
                    message="OCR quality is low; field may be present but unreadable.",
                    suggestion="Request a higher-quality scan.",
                ))
            else:
                findings.append(FindingResult(
                    field=factor,
                    severity="fail",
                    message="Required field not found in extracted document data.",
                    suggestion="Ensure the document contains this information and resubmit.",
                ))

        if not findings:
            findings.append(FindingResult(
                field="general",
                severity="warn",
                message="No validation factors defined for this document category.",
            ))

        return findings
