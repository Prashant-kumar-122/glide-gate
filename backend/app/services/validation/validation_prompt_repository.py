from __future__ import annotations

"""Loads the effective validation prompt for a given document category.

Resolution order:
1. In-memory admin override (set via PUT /admin/validation-prompts/{category})
2. File-based default from prompts/validation_defaults/{category}.json
3. Hardcoded fallback (mirrors the defaults bundled in configs/agents/document_intelligence.config.json)
"""

import json
from pathlib import Path
from typing import Any

from app.services.validation.prompt_override_store import get_prompt_override

_DEFAULTS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "prompts" / "validation_defaults"
)

_HARDCODED_DEFAULTS: dict[str, dict[str, Any]] = {
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
        "factors": [
            "Document contains readable text",
            "At least one identifying field extracted",
        ],
    },
}


def get_effective_prompt(category: str) -> dict[str, Any]:
    """Return the effective validation prompt for *category*."""
    # 1. Admin in-memory override
    override = get_prompt_override(category)
    if override:
        return override

    # 2. File-based default
    path = _DEFAULTS_DIR / f"{category}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 3. Hardcoded fallback
    return _HARDCODED_DEFAULTS.get(category, _HARDCODED_DEFAULTS["unknown"])
