"""Seed: GlideGate standard onboarding questionnaire — 11 sections, 49 questions.

Sections (in order):
    1.  personal_information     (10 questions)
    2.  trusted_contact          (5 questions)
    3.  employment_status        (4 questions)
    4.  financial_information    (5 questions)
    5.  investment_objective     (4 questions)
    6.  background               (5 questions)
    7.  regulatory_questions     (5 questions)
    8.  identity                 (3 questions)
    9.  tax                      (4 questions)
    10. acknowledgement          (1 question)
    11. sign                     (3 questions)

Running this script purges any existing questionnaire, answers, and sessions
for QUESTIONNAIRE_ID before re-seeding, so it is safe to run repeatedly.
"""
from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.questionnaire import (
    OnboardingAnswer,
    OnboardingQuestion,
    OnboardingQuestionnaire,
    OnboardingQuestionRule,
    OnboardingQuestionSession,
)

QUESTIONNAIRE_ID = UUID("c0000000-0001-0001-0001-000000000001")

SECTIONS = [
    "personal_information",
    "trusted_contact",
    "employment_status",
    "financial_information",
    "investment_objective",
    "background",
    "regulatory_questions",
    "identity",
    "tax",
    "acknowledgement",
    "sign",
]

QUESTIONS: list[dict] = [
    # ── Section 1: personal_information (10 questions) ──────────────────────
    {
        "section": "personal_information",
        "question_key": "first_name",
        "question_text": "First Name",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True, "max_length": 100},
        "show_if": None,
        "order_index": 1,
    },
    {
        "section": "personal_information",
        "question_key": "last_name",
        "question_text": "Last Name",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True, "max_length": 100},
        "show_if": None,
        "order_index": 2,
    },
    {
        "section": "personal_information",
        "question_key": "date_of_birth",
        "question_text": "Date Of Birth",
        "question_type": "date",
        "options": [],
        "validation_rules": {"required": True, "min_age": 18},
        "show_if": None,
        "order_index": 3,
    },
    {
        "section": "personal_information",
        "question_key": "country_of_citizenship",
        "question_text": "Country of Citizenship",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 4,
    },
    {
        "section": "personal_information",
        "question_key": "phone_number",
        "question_text": "Phone Number",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True, "min_digits": 7, "max_digits": 15},
        "show_if": None,
        "order_index": 5,
    },
    {
        "section": "personal_information",
        "question_key": "country",
        "question_text": "Country",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 6,
    },
    {
        "section": "personal_information",
        "question_key": "address_line_1",
        "question_text": "Address Line 1",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 7,
    },
    {
        "section": "personal_information",
        "question_key": "city",
        "question_text": "City",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 8,
    },
    {
        "section": "personal_information",
        "question_key": "state",
        "question_text": "State",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 9,
    },
    {
        "section": "personal_information",
        "question_key": "postal_code",
        "question_text": "Postal Code",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True, "postal_code": True},
        "show_if": None,
        "order_index": 10,
    },
    # ── Section 2: trusted_contact (5 questions) ────────────────────────────
    {
        "section": "trusted_contact",
        "question_key": "will_name_trusted_contact",
        "question_text": "Will you name a trusted contact?",
        "question_type": "boolean",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 11,
    },
    {
        "section": "trusted_contact",
        "question_key": "trusted_contact_first_name",
        "question_text": "Trusted Contact First Name",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": {"field": "will_name_trusted_contact", "operator": "eq", "value": "Yes"},
        "order_index": 12,
    },
    {
        "section": "trusted_contact",
        "question_key": "trusted_contact_last_name",
        "question_text": "Trusted Contact Last Name",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": {"field": "will_name_trusted_contact", "operator": "eq", "value": "Yes"},
        "order_index": 13,
    },
    {
        "section": "trusted_contact",
        "question_key": "trusted_contact_phone_number",
        "question_text": "Trusted Contact Phone Number",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": {"field": "will_name_trusted_contact", "operator": "eq", "value": "Yes"},
        "order_index": 14,
    },
    {
        "section": "trusted_contact",
        "question_key": "trusted_contact_relationship",
        "question_text": "Trusted Contact Relationship",
        "question_type": "select",
        "options": ["Brother", "Father", "Son", "Mother", "Spouse", "Sister", "Daughter"],
        "validation_rules": {"required": True},
        "show_if": {"field": "will_name_trusted_contact", "operator": "eq", "value": "Yes"},
        "order_index": 15,
    },
    # ── Section 3: employment_status (4 questions) ──────────────────────────
    {
        "section": "employment_status",
        "question_key": "employment_status",
        "question_text": "What's your employment status?",
        "question_type": "select",
        "options": ["Employed", "Self-Employed", "Retired", "Student", "Unemployed"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 16,
    },
    {
        "section": "employment_status",
        "question_key": "employment_industry",
        "question_text": "Employment Industry",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": False},
        "show_if": {"field": "employment_status", "operator": "in", "value": ["Employed", "Self-Employed"]},
        "order_index": 17,
    },
    {
        "section": "employment_status",
        "question_key": "occupation",
        "question_text": "Occupation",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": False},
        "show_if": {"field": "employment_status", "operator": "in", "value": ["Employed", "Self-Employed"]},
        "order_index": 18,
    },
    {
        "section": "employment_status",
        "question_key": "employer_name",
        "question_text": "Employer Name",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": False},
        "show_if": {"field": "employment_status", "operator": "in", "value": ["Employed", "Self-Employed"]},
        "order_index": 19,
    },
    # ── Section 4: financial_information (5 questions) ──────────────────────
    {
        "section": "financial_information",
        "question_key": "relationship_status",
        "question_text": "What's your relationship status?",
        "question_type": "select",
        "options": ["Single", "Married", "Divorced", "Widowed", "Domestic Partnership"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 20,
    },
    {
        "section": "financial_information",
        "question_key": "annual_income",
        "question_text": "What's your annual income?",
        "question_type": "select",
        "options": ["Under $25,000", "$25,000 - $50,000", "$50,000 - $100,000", "$100,000 - $250,000", "$250,000 - $500,000", "Over $500,000"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 21,
    },
    {
        "section": "financial_information",
        "question_key": "net_worth",
        "question_text": "What's your net worth?",
        "question_type": "select",
        "options": ["Under $50,000", "$50,000 - $100,000", "$100,000 - $250,000", "$250,000 - $500,000", "$500,000 - $1,000,000", "Over $1,000,000"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 22,
    },
    {
        "section": "financial_information",
        "question_key": "net_worth_source",
        "question_text": "What's the main source of your net worth?",
        "question_type": "select",
        "options": ["Income", "Inheritance", "Savings", "Business Ownership", "Investments", "Property Sales", "Other"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 23,
    },
    {
        "section": "financial_information",
        "question_key": "liquid_net_worth",
        "question_text": "What's your liquid net worth?",
        "question_type": "select",
        "options": ["Under $50,000", "$50,000 - $100,000", "$100,000 - $250,000", "$250,000 - $500,000", "$500,000 - $1,000,000", "Over $1,000,000"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 24,
    },
    # ── Section 5: investment_objective (4 questions) ────────────────────────
    {
        "section": "investment_objective",
        "question_key": "account_type",
        "question_text": "Would you like a margin account or a cash account?",
        "question_type": "select",
        "options": ["Cash Account", "Margin Account"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 25,
    },
    {
        "section": "investment_objective",
        "question_key": "source_of_funds",
        "question_text": "What is the source of funds for this account?",
        "question_type": "multi_select",
        "options": ["Income", "Pension / Retirement Savings", "Savings", "Inheritance", "Business Revenue", "Gift", "Other"],
        "validation_rules": {"required": True, "min_items": 1},
        "show_if": None,
        "order_index": 26,
    },
    {
        "section": "investment_objective",
        "question_key": "estimated_initial_funding",
        "question_text": "Estimated Initial Funding",
        "question_type": "select",
        "options": ["Under $10,000", "$10,000 - $25,000", "$25,000 - $50,000", "$50,000 - $100,000", "$100,000 - $250,000", "Over $250,000"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 27,
    },
    {
        "section": "investment_objective",
        "question_key": "investment_objective",
        "question_text": "Investment Objective",
        "question_type": "select",
        "options": ["Growth", "Income", "Speculation", "Capital Preservation", "Trading"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 28,
    },
    # ── Section 6: background (5 questions) ─────────────────────────────────
    {
        "section": "background",
        "question_key": "prior_investments",
        "question_text": "Have you previously invested in the following? (Options / Equities)",
        "question_type": "multi_select",
        "options": ["Options", "Equities", "Bonds", "Mutual Funds", "ETFs", "Futures", "None"],
        "validation_rules": {"required": True, "min_items": 1},
        "show_if": None,
        "order_index": 29,
    },
    {
        "section": "background",
        "question_key": "is_accredited_investor",
        "question_text": "Are you an accredited investor?",
        "question_type": "boolean",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 30,
    },
    {
        "section": "background",
        "question_key": "has_large_trader_id",
        "question_text": "Large Trader ID?",
        "question_type": "boolean",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 31,
    },
    {
        "section": "background",
        "question_key": "large_trader_id_number",
        "question_text": "Large Trader ID Number",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True, "alphanumeric": True, "max_alphanumeric": 20},
        "show_if": {"field": "has_large_trader_id", "operator": "eq", "value": "Yes"},
        "order_index": 32,
    },
    {
        "section": "background",
        "question_key": "current_broker",
        "question_text": "Current Broker",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": False},
        "show_if": None,
        "order_index": 33,
    },
    # ── Section 7: regulatory_questions (5 questions) ───────────────────────
    {
        "section": "regulatory_questions",
        "question_key": "employed_by_finra",
        "question_text": "Is any account holder employed by FINRA, a registered broker-dealer, or a securities exchange?",
        "question_type": "boolean",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 34,
    },
    {
        "section": "regulatory_questions",
        "question_key": "is_senior_political_figure",
        "question_text": "Is any account holder a senior political figure or politically exposed person?",
        "question_type": "boolean",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 35,
    },
    {
        "section": "regulatory_questions",
        "question_key": "is_senior_financial_officer",
        "question_text": "Is any account holder a senior officer at a bank, savings and loan institution, investment company, investment advisory firm, or other financial institutions?",
        "question_type": "boolean",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 36,
    },
    {
        "section": "regulatory_questions",
        "question_key": "is_director_or_major_shareholder",
        "question_text": "Is any account holder a director, someone with similar policy-making authority, or a 10% or more shareholder of public traded company?",
        "question_type": "boolean",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 37,
    },
    {
        "section": "regulatory_questions",
        "question_key": "subject_to_backup_withholding",
        "question_text": "Is any account holder subject to backup tax withholding?",
        "question_type": "boolean",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 38,
    },
    # ── Section 8: identity (3 questions) ───────────────────────────────────
    {
        "section": "identity",
        "question_key": "id_type",
        "question_text": "ID Type",
        "question_type": "select",
        "options": ["Driver's License", "Passport", "National ID", "State ID"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 39,
    },
    {
        "section": "identity",
        "question_key": "id_number",
        "question_text": "ID Number",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 40,
    },
    {
        "section": "identity",
        "question_key": "id_expiration_date",
        "question_text": "ID Expiration Date",
        "question_type": "date",
        "options": [],
        "validation_rules": {"required": True, "future_date": True},
        "show_if": None,
        "order_index": 41,
    },
    # ── Section 9: tax (4 questions) ─────────────────────────────────────────
    {
        "section": "tax",
        "question_key": "tax_residency_country",
        "question_text": "Tax Residency Country",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 42,
    },
    {
        "section": "tax",
        "question_key": "tax_id_type",
        "question_text": "Identity Type",
        "question_type": "select",
        "options": ["SSN", "ITIN", "Foreign Tax ID"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 43,
    },
    {
        "section": "tax",
        "question_key": "social_security_number",
        "question_text": "Tax ID Number",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True},
        "show_if": {"field": "tax_id_type", "operator": "in", "value": ["SSN", "ITIN", "Foreign Tax ID"]},
        "order_index": 44,
    },
    {
        "section": "tax",
        "question_key": "tax_lot_method",
        "question_text": "Tax Lot Method",
        "question_type": "select",
        "options": ["FIFO", "LIFO", "Highest Cost", "Lowest Cost", "Average Cost"],
        "validation_rules": {"required": True},
        "show_if": None,
        "order_index": 45,
    },
    # ── Section 10: acknowledgement (1 question) ─────────────────────────────
    {
        "section": "acknowledgement",
        "question_key": "account_agreement_accepted",
        "question_text": "Account Agreement Accepted",
        "question_type": "boolean",
        "options": [],
        "validation_rules": {"required": True, "must_be_true": True},
        "show_if": None,
        "order_index": 46,
    },
    # ── Section 11: sign (3 questions) ───────────────────────────────────────
    {
        "section": "sign",
        "question_key": "full_name_signature",
        "question_text": "Full Name",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True, "match_fields": ["first_name", "last_name"]},
        "show_if": None,
        "order_index": 47,
    },
    {
        "section": "sign",
        "question_key": "initials",
        "question_text": "Initials",
        "question_type": "text",
        "options": [],
        "validation_rules": {"required": True, "min_length": 1, "max_length": 10},
        "show_if": None,
        "order_index": 48,
    },
    {
        "section": "sign",
        "question_key": "final_confirmation",
        "question_text": "Final Confirmation",
        "question_type": "boolean",
        "options": [],
        "validation_rules": {"required": True, "must_be_true": True},
        "show_if": None,
        "order_index": 49,
    },
]


async def seed(session: AsyncSession) -> None:
    existing = await session.get(OnboardingQuestionnaire, QUESTIONNAIRE_ID)
    if existing:
        print("  [purge] removing existing questionnaire, answers, and sessions")
        await session.execute(
            delete(OnboardingAnswer).where(OnboardingAnswer.questionnaire_id == QUESTIONNAIRE_ID)
        )
        await session.execute(
            delete(OnboardingQuestionSession).where(OnboardingQuestionSession.questionnaire_id == QUESTIONNAIRE_ID)
        )
        await session.delete(existing)
        await session.commit()

    questionnaire = OnboardingQuestionnaire(
        id=QUESTIONNAIRE_ID,
        name="GlideGate Standard Onboarding Questionnaire",
        description="Comprehensive client data collection questionnaire for all CADF onboarding flows.",
        version=1,
        is_active=True,
        sections=SECTIONS,
        extra_metadata={"brd_ref": "Section 15.3"},
    )
    session.add(questionnaire)
    print(f"  [seed] questionnaire '{questionnaire.name}'")

    for q_data in QUESTIONS:
        question = OnboardingQuestion(
            questionnaire_id=QUESTIONNAIRE_ID,
            **q_data,
        )
        session.add(question)
        print(f"    [seed] question {q_data['question_key']}")

    await session.commit()
    print(f"  [done] {len(QUESTIONS)} questions seeded across {len(SECTIONS)} sections")  # 49 questions


if __name__ == "__main__":
    async def main() -> None:
        async with AsyncSessionLocal() as session:
            await seed(session)

    asyncio.run(main())
