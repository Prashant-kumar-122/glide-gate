from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from loguru import logger
from pydantic import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class QuestionnaireField(BaseModel):
    field_id: str
    label: str
    question: str
    field_type: str  # text | number | date | email | phone | choice | multi_choice
    section: str
    options: list[str] | None = None
    required: bool = True
    show_if: dict[str, Any] | None = None
    validation_rules: dict[str, Any] | None = None


class CollectionStatus(BaseModel):
    collected_fields: dict[str, Any]
    pending_fields: list[str]
    current_section: str
    is_complete: bool
    completion_pct: float


# ── Hardcoded fallback fields (used when DB load fails) ───────────────────────

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
    # Section 7 — Cash Account (show_if: product selected)
    QuestionnaireField(
        field_id="ca_initial_deposit", label="Initial Deposit Amount (USD)",
        question="What initial amount would you like to deposit into your Cash Account?",
        field_type="number", section="cash_account",
        show_if={"field": "selected_products", "operator": "contains", "value": "cash_account"},
    ),
    QuestionnaireField(
        field_id="ca_account_purpose", label="Account Purpose",
        question="What is the primary purpose of your Cash Account? (e.g., emergency fund, short-term savings, everyday spending)",
        field_type="text", section="cash_account",
        show_if={"field": "selected_products", "operator": "contains", "value": "cash_account"},
    ),
    QuestionnaireField(
        field_id="ca_expected_monthly_activity", label="Expected Monthly Activity (USD)",
        question="What is your approximate expected monthly transaction volume for this Cash Account?",
        field_type="number", section="cash_account", required=False,
        show_if={"field": "selected_products", "operator": "contains", "value": "cash_account"},
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
    "cash_account",
    "retirement_account",
]

# Maps DB question_type → internal field_type used by extract_value()
_DB_TYPE_MAP: dict[str, str] = {
    "text": "text",
    "number": "number",
    "date": "date",
    "select": "choice",
    "multi_select": "multi_choice",
    "boolean": "choice",
    "currency": "number",
}


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
_PHONE_RE = re.compile(r"[\+\d][\d\s\-\(\)]{6,20}")
_NUMBER_RE = re.compile(r"[\$,]?(\d[\d,]*\.?\d*)")
_DATE_RE = re.compile(r"\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})\b")
_ALNUM_RE = re.compile(r"^[a-zA-Z0-9]+$")


def extract_value(message: str, field: QuestionnaireField) -> Any | None:
    """Best-effort extraction of a typed field value from free-text."""
    msg = message.strip()
    ft = field.field_type
    rules = field.validation_rules or {}

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

    # text / default — min_length from DB rules, default 1
    min_len = rules.get("min_length", 1)
    return msg if len(msg) >= min_len else None


# ── Value validator ───────────────────────────────────────────────────────────

def _parse_dmy(value: str) -> date | None:
    """Parse DD/MM/YYYY produced by extract_value into a date object."""
    try:
        parts = value.split("/")
        if len(parts) == 3:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        pass
    return None


def validate_value(
    value: Any, field: QuestionnaireField, collected: dict[str, Any]
) -> str | None:
    """
    Returns a human-readable error string if the extracted value violates a
    validation_rules constraint, or None if the value is acceptable.
    """
    rules = field.validation_rules or {}
    v = str(value).strip()

    # min_length / max_length
    min_len = rules.get("min_length", 1)
    if len(v) < min_len:
        return f"Must be at least {min_len} character(s) long."
    if "max_length" in rules and len(v) > rules["max_length"]:
        return f"Must be {rules['max_length']} characters or fewer."

    # alphanumeric + max_alphanumeric (e.g. large trader ID)
    if rules.get("alphanumeric"):
        if not _ALNUM_RE.match(v):
            return "Must contain only letters and numbers — no spaces or special characters."
        limit = rules.get("max_alphanumeric")
        if limit and len(v) > limit:
            return f"Must be {limit} characters or fewer."

    # min_digits / max_digits (phone numbers)
    if "min_digits" in rules or "max_digits" in rules:
        digits = re.sub(r"\D", "", v)
        if "min_digits" in rules and len(digits) < rules["min_digits"]:
            return f"Must contain at least {rules['min_digits']} digits."
        if "max_digits" in rules and len(digits) > rules["max_digits"]:
            return f"Must contain no more than {rules['max_digits']} digits."

    # postal_code — permissive: 3–10 alphanumeric chars/spaces/hyphens
    if rules.get("postal_code"):
        if not re.match(r"^[a-zA-Z0-9][\sa\-zA-Z0-9]{2,9}$", v):
            return "Please enter a valid postal code (e.g. 10001 or SW1A 1AA)."

    # min_age (date of birth)
    if "min_age" in rules and field.field_type == "date":
        parsed = _parse_dmy(v)
        if parsed is None:
            return "Please enter a valid date in DD/MM/YYYY format."
        today = date.today()
        age = today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day))
        if age < rules["min_age"]:
            return f"You must be at least {rules['min_age']} years old to open an account."

    # future_date (ID expiration)
    if rules.get("future_date") and field.field_type == "date":
        parsed = _parse_dmy(v)
        if parsed is None:
            return "Please enter a valid date in DD/MM/YYYY format."
        if parsed <= date.today():
            return "The expiration date must be in the future."

    # match_fields (e.g. full_name_signature must contain first + last name)
    if "match_fields" in rules:
        parts = [str(collected.get(f, "")).strip().lower() for f in rules["match_fields"]]
        parts = [p for p in parts if p]
        name_lower = v.lower()
        missing = [p for p in parts if p not in name_lower]
        if missing:
            labels = " and ".join(r.replace("_", " ") for r in rules["match_fields"])
            return f"Must include your {labels} as entered during onboarding."

    return None


# ── Orchestrator ──────────────────────────────────────────────────────────────

class DataCollectionOrchestrator:
    """
    Drives sequential questionnaire collection, respecting show_if visibility rules.

    Questions are loaded from the DB (onboarding_questions table) on session init
    via load_questions_from_db(). Falls back to the hardcoded _FIELDS list if the
    DB load fails or the questionnaire table is empty.
    """

    def __init__(self) -> None:
        self._collected: dict[UUID, dict[str, Any]] = {}
        # Per-case DB-loaded fields (key = case_id)
        self._fields_cache: dict[UUID, list[QuestionnaireField]] = {}
        # field_id → DB question UUID per case
        self._question_id_map: dict[UUID, dict[str, UUID]] = {}
        # case_id → DB questionnaire UUID
        self._questionnaire_id_map: dict[UUID, UUID] = {}

    # ── DB loading ────────────────────────────────────────────────────────────

    async def load_questions_from_db(self, case_id: UUID, db: AsyncSession) -> None:
        """
        Load questions from onboarding_questions into per-case memory cache.
        Gracefully falls back to hardcoded _FIELDS on any error.
        """
        try:
            from sqlalchemy import select
            from app.models.questionnaire import OnboardingQuestion, OnboardingQuestionnaire

            q_result = await db.execute(
                select(OnboardingQuestionnaire)
                .where(OnboardingQuestionnaire.is_active == True)  # noqa: E712
                .limit(1)
            )
            questionnaire = q_result.scalar_one_or_none()
            if questionnaire is None:
                logger.warning(f"DCO: no active questionnaire found, using fallback for case {case_id}")
                return

            self._questionnaire_id_map[case_id] = questionnaire.id

            oq_result = await db.execute(
                select(OnboardingQuestion)
                .where(OnboardingQuestion.questionnaire_id == questionnaire.id)
                .order_by(OnboardingQuestion.order_index)
            )
            questions = oq_result.scalars().all()

            if not questions:
                logger.warning(f"DCO: questionnaire has no questions, using fallback for case {case_id}")
                return

            fields: list[QuestionnaireField] = []
            question_id_map: dict[str, UUID] = {}

            for q in questions:
                options = list(q.options) if q.options else None
                # boolean questions get Yes/No options for the choice extractor
                if q.question_type == "boolean":
                    options = ["Yes", "No"]

                field = QuestionnaireField(
                    field_id=q.question_key,
                    label=q.question_text,
                    question=q.question_text,
                    field_type=_DB_TYPE_MAP.get(q.question_type, "text"),
                    section=q.section,
                    options=options,
                    required=q.is_required,
                    show_if=q.show_if,
                    validation_rules=dict(q.validation_rules) if q.validation_rules else None,
                )
                fields.append(field)
                question_id_map[q.question_key] = q.id

            self._fields_cache[case_id] = fields
            self._question_id_map[case_id] = question_id_map
            logger.info(f"DCO: loaded {len(fields)} questions from DB for case {case_id}")

        except Exception as exc:
            logger.warning(f"DCO: DB load failed for case {case_id}, using fallback: {exc}")

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get_question_id(self, case_id: UUID, field_id: str) -> UUID | None:
        """Return the DB UUID for a question_key, or None if not DB-loaded."""
        return self._question_id_map.get(case_id, {}).get(field_id)

    def get_questionnaire_id(self, case_id: UUID) -> UUID | None:
        """Return the DB UUID for the active questionnaire, or None if not DB-loaded."""
        return self._questionnaire_id_map.get(case_id)

    def is_db_loaded(self, case_id: UUID) -> bool:
        return case_id in self._fields_cache

    def _effective_fields(self, case_id: UUID) -> list[QuestionnaireField]:
        return self._fields_cache.get(case_id, _FIELDS)

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def init_session(self, case_id: UUID, selected_products: list[str]) -> None:
        self._collected[case_id] = {"selected_products": selected_products}

    def has_session(self, case_id: UUID) -> bool:
        return case_id in self._collected

    def update(self, case_id: UUID, field_id: str, value: Any) -> None:
        self._collected.setdefault(case_id, {})[field_id] = value

    def get_collected(self, case_id: UUID) -> dict[str, Any]:
        return dict(self._collected.get(case_id, {}))

    # ── Field navigation ──────────────────────────────────────────────────────

    def next_field(self, case_id: UUID) -> QuestionnaireField | None:
        collected = self._collected.get(case_id, {})
        fields = self._effective_fields(case_id)

        if self.is_db_loaded(case_id):
            # DB path: fields already in order_index order
            for field in fields:
                if not _visible(field, collected):
                    continue
                if field.required and field.field_id not in collected:
                    return field
            return None

        # Fallback: hardcoded fields iterated by section order
        for section in _SECTION_ORDER:
            for field in fields:
                if field.section != section:
                    continue
                if not _visible(field, collected):
                    continue
                if field.required and field.field_id not in collected:
                    return field
        return None

    def status(self, case_id: UUID) -> CollectionStatus:
        collected = self._collected.get(case_id, {})
        fields = self._effective_fields(case_id)
        visible_required = [f for f in fields if _visible(f, collected) and f.required]
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
    ) -> tuple[Any | None, str | None]:
        """
        Returns (value, error):
          (value, None)  — extracted and validated successfully
          (None, error)  — extracted but failed validation
          (None, None)   — could not extract (user didn't provide the info)
        """
        value = extract_value(message, field)
        if value is None:
            return None, None
        collected = self._collected.get(case_id, {})
        error = validate_value(value, field, collected)
        if error:
            return None, error
        self.update(case_id, field.field_id, value)
        return value, None
