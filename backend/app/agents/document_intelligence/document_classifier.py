from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

DocumentCategory = Literal[
    "identity", "financial", "legal", "insurance", "compliance", "entity", "unknown"
]

DocumentType = Literal[
    # identity
    "passport", "national_id", "drivers_license",
    # financial
    "bank_statement", "tax_return", "payslip", "investment_statement",
    # legal
    "trust_deed", "power_of_attorney", "incorporation_certificate", "partnership_agreement",
    # insurance
    "life_insurance_policy", "health_insurance_certificate",
    # compliance
    "kyc_form", "aml_declaration", "fatca_crs_form", "regulatory_questionnaire",
    # entity
    "company_registration", "ownership_structure", "shareholder_register",
    # fallback
    "unknown",
]


class ClassificationResult(BaseModel):
    category: DocumentCategory
    doc_type: DocumentType
    confidence: float          # 0.0–1.0
    display_name: str
    requires_expiry_check: bool = False
    typical_fields: list[str]


_RULES: list[tuple[list[str], DocumentCategory, DocumentType, str, bool, list[str]]] = [
    # keywords, category, doc_type, display_name, requires_expiry_check, typical_fields
    (
        ["passport"],
        "identity", "passport", "Passport", True,
        ["full_name", "date_of_birth", "nationality", "passport_number", "expiry_date"],
    ),
    (
        ["national id", "national_id", "nric", "national identification"],
        "identity", "national_id", "National ID", True,
        ["full_name", "date_of_birth", "id_number", "expiry_date"],
    ),
    (
        ["driver", "driving licence", "driving license"],
        "identity", "drivers_license", "Driver's License", True,
        ["full_name", "date_of_birth", "license_number", "expiry_date"],
    ),
    (
        ["bank statement", "bank_statement", "account statement"],
        "financial", "bank_statement", "Bank Statement", False,
        ["account_number", "account_holder", "period_from", "period_to", "closing_balance"],
    ),
    (
        ["tax return", "tax_return", "income tax"],
        "financial", "tax_return", "Tax Return", False,
        ["tax_year", "total_income", "tax_paid", "taxpayer_name"],
    ),
    (
        ["payslip", "pay slip", "salary slip", "pay stub"],
        "financial", "payslip", "Payslip", False,
        ["employee_name", "employer", "period", "gross_salary", "net_salary"],
    ),
    (
        ["investment statement", "portfolio statement", "brokerage statement"],
        "financial", "investment_statement", "Investment Statement", False,
        ["account_number", "account_holder", "portfolio_value", "period"],
    ),
    (
        ["trust deed", "trust_deed"],
        "legal", "trust_deed", "Trust Deed", False,
        ["trust_name", "trustee", "beneficiary", "establishment_date"],
    ),
    (
        ["power of attorney", "poa"],
        "legal", "power_of_attorney", "Power of Attorney", True,
        ["grantor", "attorney", "scope", "expiry_date"],
    ),
    (
        ["incorporation", "certificate of incorporation", "articles of incorporation"],
        "legal", "incorporation_certificate", "Certificate of Incorporation", False,
        ["company_name", "registration_number", "incorporation_date", "jurisdiction"],
    ),
    (
        ["partnership agreement"],
        "legal", "partnership_agreement", "Partnership Agreement", False,
        ["partnership_name", "partners", "commencement_date"],
    ),
    (
        ["life insurance", "life assurance"],
        "insurance", "life_insurance_policy", "Life Insurance Policy", True,
        ["policyholder", "policy_number", "sum_assured", "expiry_date"],
    ),
    (
        ["health insurance", "health certificate", "medical insurance"],
        "insurance", "health_insurance_certificate", "Health Insurance Certificate", True,
        ["policyholder", "policy_number", "coverage", "expiry_date"],
    ),
    (
        ["kyc form", "kyc_form", "know your customer"],
        "compliance", "kyc_form", "KYC Form", False,
        ["client_name", "date_completed", "reviewed_by"],
    ),
    (
        ["aml declaration", "aml_declaration", "anti-money laundering"],
        "compliance", "aml_declaration", "AML Declaration", False,
        ["declarant_name", "date_signed"],
    ),
    (
        ["fatca", "crs", "common reporting standard"],
        "compliance", "fatca_crs_form", "FATCA/CRS Form", False,
        ["account_holder", "tax_residency", "tin"],
    ),
    (
        ["regulatory questionnaire", "regulatory form", "suitability questionnaire"],
        "compliance", "regulatory_questionnaire", "Regulatory Questionnaire", False,
        ["client_name", "date_completed"],
    ),
    (
        ["company registration", "business registration", "acra"],
        "entity", "company_registration", "Company Registration", False,
        ["company_name", "uen", "registration_date", "status"],
    ),
    (
        ["ownership structure", "group structure"],
        "entity", "ownership_structure", "Ownership Structure", False,
        ["entity_name", "ultimate_beneficial_owner", "ownership_percentage"],
    ),
    (
        ["shareholder register", "shareholders"],
        "entity", "shareholder_register", "Shareholder Register", False,
        ["company_name", "shareholders", "shares_issued"],
    ),
]


class DocumentClassifier:
    """
    Rule-based document classifier (BRD Section 6.1, FR-06).

    Matches filename + extracted text keywords against a priority-ordered rule table.
    Returns category, doc_type, confidence, and expected fields for completeness validation.
    """

    def classify(
        self,
        filename: str = "",
        raw_text: str = "",
    ) -> ClassificationResult:
        combined = (filename + " " + raw_text).lower()
        combined = re.sub(r"[_\-/\\]", " ", combined)

        best_score = 0
        best_rule = None

        for keywords, category, doc_type, display_name, expiry, fields in _RULES:
            hits = sum(1 for kw in keywords if kw in combined)
            if hits > best_score:
                best_score = hits
                best_rule = (category, doc_type, display_name, expiry, fields, len(keywords))

        if best_rule is None or best_score == 0:
            return ClassificationResult(
                category="unknown",
                doc_type="unknown",
                confidence=0.0,
                display_name="Unknown Document",
                typical_fields=[],
            )

        category, doc_type, display_name, expiry, fields, total_kw = best_rule
        confidence = min(round(best_score / max(total_kw, 1), 2), 1.0)
        # Boost confidence when keyword found in filename
        filename_lower = filename.lower()
        if any(kw in filename_lower for kw in _RULES[0][0]):
            confidence = min(confidence + 0.1, 1.0)

        return ClassificationResult(
            category=category,
            doc_type=doc_type,
            confidence=confidence,
            display_name=display_name,
            requires_expiry_check=expiry,
            typical_fields=fields,
        )
