from __future__ import annotations

import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class QuestionnaireField(BaseModel):
    field_id: str
    label: str
    question: str
    field_type: Literal["text", "number", "date", "email", "phone", "choice", "multi_choice"]
    section: str
    options: list[str] | None = None
    required: bool = True
    show_if: dict[str, Any] | None = None


class CollectionStatus(BaseModel):
    collected_fields: dict[str, Any]
    pending_fields: list[str]
    current_section: str
    is_complete: bool
    completion_pct: float


# ── Full questionnaire definition ─────────────────────────────────────────────
# Mirrors the 12-section questionnaire seeded in STEP-12 with the same
# show_if rule shapes used by the CheckpointRuleEngine.

_FIELDS: list[QuestionnaireField] = [
    # Section 1 — Personal Details
    QuestionnaireField(
        field_id="full_name", label="Full Legal Name",
        question="Let's start with your full legal name as it appears on your ID document.",
        field_type="text", section="personal_details",
    ),
    QuestionnaireField(
        field_id="date_of_birth", label="Date of Birth",
        question="What is your date of birth? (DD/MM/YYYY)",
        field_type="date", section="personal_details",
    ),
    QuestionnaireField(
        field_id="nationality", label="Nationality",
        question="What is your nationality?",
        field_type="text", section="personal_details",
    ),
    QuestionnaireField(
        field_id="email", label="Email Address",
        question="What is your primary email address?",
        field_type="email", section="personal_details",
    ),
    QuestionnaireField(
        field_id="phone", label="Phone Number",
        question="What is your phone number, including country code?",
        field_type="phone", section="personal_details",
    ),
    # Section 2 — Address
    QuestionnaireField(
        field_id="residential_address", label="Residential Address",
        question="What is your current residential address?",
        field_type="text", section="address",
    ),
    QuestionnaireField(
        field_id="years_at_address", label="Years at Address",
        question="How many years have you lived at this address?",
        field_type="number", section="address",
    ),
    # Section 3 — Employment
    QuestionnaireField(
        field_id="employment_status", label="Employment Status",
        question="What is your current employment status?",
        field_type="choice",
        options=["Employed", "Self-Employed", "Retired", "Student", "Unemployed"],
        section="employment",
    ),
    QuestionnaireField(
        field_id="employer_name", label="Employer Name",
        question="Who is your current employer?",
        field_type="text", section="employment",
        show_if={"field": "employment_status", "operator": "in", "value": ["Employed", "Self-Employed"]},
    ),
    QuestionnaireField(
        field_id="occupation", label="Occupation / Job Title",
        question="What is your occupation or job title?",
        field_type="text", section="employment",
        show_if={"field": "employment_status", "operator": "in", "value": ["Employed", "Self-Employed"]},
    ),
    QuestionnaireField(
        field_id="annual_income", label="Annual Income (USD)",
        question="What is your approximate annual income in USD?",
        field_type="number", section="employment",
    ),
    # Section 4 — Financial Profile
    QuestionnaireField(
        field_id="investable_assets", label="Investable Assets (USD)",
        question="How much do you have in investable assets, excluding your primary residence?",
        field_type="number", section="financial_profile",
    ),
    QuestionnaireField(
        field_id="net_worth", label="Net Worth (USD)",
        question="What is your approximate total net worth?",
        field_type="number", section="financial_profile",
    ),
    QuestionnaireField(
        field_id="source_of_funds", label="Source of Funds",
        question="What is the primary source of funds for this investment?",
        field_type="choice",
        options=["Employment Income", "Business Income", "Inheritance", "Investment Returns", "Property Sale", "Other"],
        section="financial_profile",
    ),
    QuestionnaireField(
        field_id="source_of_wealth_detail", label="Source of Wealth Detail",
        question="Given your income level, please provide additional details about your primary source of wealth.",
        field_type="text", section="financial_profile",
        show_if={"field": "annual_income", "operator": "gt", "value": 250000},
    ),
    # Section 5 — Investment Experience
    QuestionnaireField(
        field_id="investment_experience", label="Investment Experience",
        question="How would you describe your investment experience?",
        field_type="choice",
        options=["None", "Limited (1–3 years)", "Moderate (3–10 years)", "Extensive (10+ years)"],
        section="investment_experience",
    ),
    QuestionnaireField(
        field_id="risk_tolerance", label="Risk Tolerance",
        question="What is your risk tolerance for investments?",
        field_type="choice",
        options=["Conservative", "Moderate", "Aggressive"],
        section="investment_experience",
    ),
    QuestionnaireField(
        field_id="investment_objectives", label="Investment Objectives",
        question="What are your primary investment objectives? (select all that apply)",
        field_type="multi_choice",
        options=["Capital Preservation", "Income Generation", "Capital Growth", "Speculation"],
        section="investment_experience",
    ),
    # Section 6 — KYC Identity
    QuestionnaireField(
        field_id="id_type", label="Identity Document Type",
        question="What type of identity document will you be providing?",
        field_type="choice",
        options=["Passport", "National ID", "Driver's License"],
        section="kyc_identity",
    ),
    QuestionnaireField(
        field_id="id_number", label="ID Document Number",
        question="Please provide your document number.",
        field_type="text", section="kyc_identity",
    ),
    QuestionnaireField(
        field_id="tax_residency", label="Tax Residency Country",
        question="In which country are you a tax resident?",
        field_type="text", section="kyc_identity",
    ),
    QuestionnaireField(
        field_id="tax_identification_number", label="Tax Identification Number",
        question="What is your Tax Identification Number (TIN)?",
        field_type="text", section="kyc_identity",
    ),
    # Section 7 — Managed Portfolio suitability (show_if: product selected)
    QuestionnaireField(
        field_id="mp_investment_horizon", label="Investment Horizon",
        question="For your Managed Portfolio, what is your investment time horizon?",
        field_type="choice",
        options=["Short-term (< 3 years)", "Medium-term (3–7 years)", "Long-term (7+ years)"],
        section="managed_portfolio",
        show_if={"field": "selected_products", "operator": "contains", "value": "managed_portfolio"},
    ),
    QuestionnaireField(
        field_id="mp_initial_investment", label="Initial Investment Amount (USD)",
        question="What initial amount would you like to invest in the Managed Portfolio?",
        field_type="number", section="managed_portfolio",
        show_if={"field": "selected_products", "operator": "contains", "value": "managed_portfolio"},
    ),
    QuestionnaireField(
        field_id="mp_benchmark_preference", label="Benchmark Preference",
        question="Do you have a preferred benchmark or investment strategy for the Managed Portfolio?",
        field_type="text", section="managed_portfolio", required=False,
        show_if={"field": "selected_products", "operator": "contains", "value": "managed_portfolio"},
    ),
    # Section 8 — Retirement Account (show_if: product selected)
    QuestionnaireField(
        field_id="ra_retirement_age", label="Target Retirement Age",
        question="At what age are you planning to retire?",
        field_type="number", section="retirement_account",
        show_if={"field": "selected_products", "operator": "contains", "value": "retirement_account"},
    ),
    QuestionnaireField(
        field_id="ra_monthly_contribution", label="Monthly Contribution (USD)",
        question="How much would you like to contribute monthly to your Retirement Account?",
        field_type="number", section="retirement_account",
        show_if={"field": "selected_products", "operator": "contains", "value": "retirement_account"},
    ),
    QuestionnaireField(
        field_id="ra_existing_plans", label="Existing Retirement Plans",
        question="Do you have any existing retirement plans or pension arrangements?",
        field_type="choice",
        options=["Yes", "No"],
        section="retirement_account",
        show_if={"field": "selected_products", "operator": "contains", "value": "retirement_account"},
    ),
]

_SECTION_ORDER = [
    "personal_details",
    "address",
    "employment",
    "financial_profile",
    "investment_experience",
    "kyc_identity",
    "managed_portfolio",
    "retirement_account",
]

# ── show_if evaluator ─────────────────────────────────────────────────────────

def _eval_show_if(rule: dict[str, Any], collected: dict[str, Any]) -> bool:
    val = collected.get(rule["field"])
    if val is None:
        return False
    op, target = rule["operator"], rule["value"]
    if op == "contains":
        return target in (val if isinstance(val, list) else str(val))
    if op == "gt":
        try:
            return float(val) > float(target)
        except (TypeError, ValueError):
            return False
    if op == "eq":
        return str(val) == str(target)
    if op == "in":
        return val in target
    return False


def _visible(field: QuestionnaireField, collected: dict[str, Any]) -> bool:
    return field.show_if is None or _eval_show_if(field.show_if, collected)


# ── Value extractor ───────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"[\+\d][\d\s\-\(\)]{7,15}")
_NUMBER_RE = re.compile(r"[\$,]?(\d[\d,]*\.?\d*)")
_DATE_RE = re.compile(r"\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})\b")


def extract_value(message: str, field: QuestionnaireField) -> Any | None:
    """Best-effort extraction of a typed field value from free-text."""
    msg = message.strip()
    ft = field.field_type

    if ft == "email":
        m = _EMAIL_RE.search(msg)
        return m.group(0) if m else None

    if ft == "phone":
        m = _PHONE_RE.search(msg)
        return m.group(0).strip() if m else None

    if ft == "date":
        m = _DATE_RE.search(msg)
        if m:
            d, mo, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
            y = f"20{y}" if len(y) == 2 else y
            return f"{d}/{mo}/{y}"
        return None

    if ft == "number":
        m = _NUMBER_RE.search(msg)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                return float(raw)
            except ValueError:
                return None
        return None

    if ft == "choice" and field.options:
        lower = msg.lower()
        for opt in field.options:
            if opt.lower() in lower:
                return opt
        m = re.match(r"^(\d+)$", msg.strip())
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(field.options):
                return field.options[idx]
        return None

    if ft == "multi_choice" and field.options:
        lower = msg.lower()
        found = [o for o in field.options if o.lower() in lower]
        return found if found else None

    # text / default
    return msg if len(msg) >= 2 else None


# ── Orchestrator ──────────────────────────────────────────────────────────────

class DataCollectionOrchestrator:
    """Drives sequential questionnaire collection, respecting show_if visibility rules."""

    def __init__(self) -> None:
        self._collected: dict[UUID, dict[str, Any]] = {}

    def init_session(self, case_id: UUID, selected_products: list[str]) -> None:
        self._collected[case_id] = {"selected_products": selected_products}

    def has_session(self, case_id: UUID) -> bool:
        return case_id in self._collected

    def update(self, case_id: UUID, field_id: str, value: Any) -> None:
        self._collected.setdefault(case_id, {})[field_id] = value

    def get_collected(self, case_id: UUID) -> dict[str, Any]:
        return dict(self._collected.get(case_id, {}))

    def next_field(self, case_id: UUID) -> QuestionnaireField | None:
        collected = self._collected.get(case_id, {})
        for section in _SECTION_ORDER:
            for field in _FIELDS:
                if field.section != section:
                    continue
                if not _visible(field, collected):
                    continue
                if field.required and field.field_id not in collected:
                    return field
        return None

    def status(self, case_id: UUID) -> CollectionStatus:
        collected = self._collected.get(case_id, {})
        visible_required = [f for f in _FIELDS if _visible(f, collected) and f.required]
        pending = [f.field_id for f in visible_required if f.field_id not in collected]
        total = len(visible_required)
        done = total - len(pending)
        nxt = self.next_field(case_id)
        return CollectionStatus(
            collected_fields=collected,
            pending_fields=pending,
            current_section=nxt.section if nxt else "complete",
            is_complete=len(pending) == 0,
            completion_pct=round(done / total * 100, 1) if total else 100.0,
        )

    def extract_and_update(
        self, case_id: UUID, message: str, field: QuestionnaireField
    ) -> Any | None:
        value = extract_value(message, field)
        if value is not None:
            self.update(case_id, field.field_id, value)
        return value
