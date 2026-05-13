"""Seed: Onboarding questionnaire with 12 sections and show_if conditional rules.

BRD: Section 15.3
Conditional show_if rules:
  - Cash Account suitability:   {"field": "selected_products", "operator": "contains", "value": "cash_account"}
  - Retirement Account:         {"field": "selected_products", "operator": "contains", "value": "retirement_account"}
  - Source of wealth (detail):  {"field": "annual_income", "operator": "gt", "value": 250000}
"""
from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.questionnaire import OnboardingQuestionnaire, OnboardingQuestion, OnboardingQuestionRule

QUESTIONNAIRE_ID = UUID("c0000000-0001-0001-0001-000000000001")

SECTIONS = [
    "personal_information",
    "contact_details",
    "address",
    "identity_verification",
    "employment",
    "financial_profile",
    "investment_profile",
    "product_selection",
    "cash_account_suitability",
    "retirement_account_suitability",
    "source_of_wealth",
    "consents_and_declarations",
]

# Each question: (section, key, text, type, options, validation, show_if, order)
QUESTIONS: list[dict] = [
    # ── personal_information ────────────────────────────────────────────────
    {"section": "personal_information", "question_key": "first_name", "question_text": "What is your first name?", "question_type": "text", "options": [], "validation_rules": {"required": True, "max_length": 100}, "show_if": None, "order_index": 1},
    {"section": "personal_information", "question_key": "last_name", "question_text": "What is your last name?", "question_type": "text", "options": [], "validation_rules": {"required": True, "max_length": 100}, "show_if": None, "order_index": 2},
    {"section": "personal_information", "question_key": "date_of_birth", "question_text": "What is your date of birth?", "question_type": "date", "options": [], "validation_rules": {"required": True, "min_age": 18}, "show_if": None, "order_index": 3},
    {"section": "personal_information", "question_key": "nationality", "question_text": "What is your nationality?", "question_type": "text", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 4},
    {"section": "personal_information", "question_key": "tax_residency", "question_text": "What is your country of tax residency?", "question_type": "text", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 5},
    # ── contact_details ────────────────────────────────────────────────────
    {"section": "contact_details", "question_key": "email", "question_text": "What is your email address?", "question_type": "text", "options": [], "validation_rules": {"required": True, "format": "email"}, "show_if": None, "order_index": 6},
    {"section": "contact_details", "question_key": "phone", "question_text": "What is your mobile phone number?", "question_type": "text", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 7},
    # ── address ────────────────────────────────────────────────────────────
    {"section": "address", "question_key": "address_line1", "question_text": "Street address (line 1)?", "question_type": "text", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 8},
    {"section": "address", "question_key": "address_city", "question_text": "City?", "question_type": "text", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 9},
    {"section": "address", "question_key": "address_country", "question_text": "Country of residence?", "question_type": "text", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 10},
    # ── identity_verification ──────────────────────────────────────────────
    {"section": "identity_verification", "question_key": "id_document_type", "question_text": "Which identity document will you provide?", "question_type": "select", "options": ["passport", "national_id", "driving_licence"], "validation_rules": {"required": True}, "show_if": None, "order_index": 11},
    {"section": "identity_verification", "question_key": "id_document_number", "question_text": "What is your document number?", "question_type": "text", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 12},
    # ── employment ─────────────────────────────────────────────────────────
    {"section": "employment", "question_key": "employment_status", "question_text": "What is your employment status?", "question_type": "select", "options": ["employed", "self_employed", "retired", "student", "unemployed"], "validation_rules": {"required": True}, "show_if": None, "order_index": 13},
    {"section": "employment", "question_key": "employer_name", "question_text": "What is the name of your employer or business?", "question_type": "text", "options": [], "validation_rules": {"required": False}, "show_if": {"field": "employment_status", "operator": "in", "value": ["employed", "self_employed"]}, "order_index": 14},
    {"section": "employment", "question_key": "occupation", "question_text": "What is your occupation / job title?", "question_type": "text", "options": [], "validation_rules": {"required": False}, "show_if": {"field": "employment_status", "operator": "in", "value": ["employed", "self_employed"]}, "order_index": 15},
    # ── financial_profile ──────────────────────────────────────────────────
    {"section": "financial_profile", "question_key": "annual_income", "question_text": "What is your approximate annual income (USD)?", "question_type": "currency", "options": [], "validation_rules": {"required": True, "min": 0}, "show_if": None, "order_index": 16},
    {"section": "financial_profile", "question_key": "net_worth", "question_text": "What is your approximate net worth (USD)?", "question_type": "currency", "options": [], "validation_rules": {"required": True, "min": 0}, "show_if": None, "order_index": 17},
    # ── investment_profile ─────────────────────────────────────────────────
    {"section": "investment_profile", "question_key": "risk_appetite", "question_text": "How would you describe your risk appetite?", "question_type": "select", "options": ["conservative", "moderate", "aggressive"], "validation_rules": {"required": True}, "show_if": None, "order_index": 18},
    {"section": "investment_profile", "question_key": "investment_experience", "question_text": "What is your level of investment experience?", "question_type": "select", "options": ["none", "limited", "moderate", "extensive"], "validation_rules": {"required": True}, "show_if": None, "order_index": 19},
    {"section": "investment_profile", "question_key": "investment_horizon", "question_text": "What is your investment time horizon?", "question_type": "select", "options": ["short", "medium", "long"], "validation_rules": {"required": True}, "show_if": None, "order_index": 20},
    # ── product_selection ─────────────────────────────────────────────────
    {"section": "product_selection", "question_key": "selected_products", "question_text": "Which products would you like to open?", "question_type": "multi_select", "options": ["cash_account", "retirement_account"], "validation_rules": {"required": True, "min_items": 1}, "show_if": None, "order_index": 21},
    # ── cash_account_suitability (show_if cash_account selected) ──────────
    {"section": "cash_account_suitability", "question_key": "cash_account_purpose", "question_text": "What is the primary purpose of your Cash Account?", "question_type": "select", "options": ["daily_transactions", "savings", "investment_vehicle", "business_payments"], "validation_rules": {"required": True}, "show_if": {"field": "selected_products", "operator": "contains", "value": "cash_account"}, "order_index": 22},
    {"section": "cash_account_suitability", "question_key": "expected_monthly_transactions", "question_text": "How many transactions do you expect per month?", "question_type": "select", "options": ["1_to_10", "11_to_50", "51_to_200", "over_200"], "validation_rules": {"required": True}, "show_if": {"field": "selected_products", "operator": "contains", "value": "cash_account"}, "order_index": 23},
    # ── retirement_account_suitability (show_if retirement selected) ───────
    {"section": "retirement_account_suitability", "question_key": "retirement_age_target", "question_text": "At what age do you plan to retire?", "question_type": "number", "options": [], "validation_rules": {"required": True, "min": 45, "max": 80}, "show_if": {"field": "selected_products", "operator": "contains", "value": "retirement_account"}, "order_index": 24},
    {"section": "retirement_account_suitability", "question_key": "monthly_contribution", "question_text": "How much do you plan to contribute monthly (USD)?", "question_type": "currency", "options": [], "validation_rules": {"required": True, "min": 100}, "show_if": {"field": "selected_products", "operator": "contains", "value": "retirement_account"}, "order_index": 25},
    # ── source_of_wealth (show_if annual_income > 250000) ──────────────────
    {"section": "source_of_wealth", "question_key": "primary_wealth_source", "question_text": "What is the primary source of your wealth?", "question_type": "select", "options": ["salary_income", "business_ownership", "investments", "inheritance", "property_sales", "other"], "validation_rules": {"required": True}, "show_if": {"field": "annual_income", "operator": "gt", "value": 250000}, "order_index": 26},
    {"section": "source_of_wealth", "question_key": "wealth_source_details", "question_text": "Please provide additional details about the source of your wealth.", "question_type": "text", "options": [], "validation_rules": {"required": True, "min_length": 50}, "show_if": {"field": "annual_income", "operator": "gt", "value": 250000}, "order_index": 27},
    # ── consents_and_declarations ─────────────────────────────────────────
    {"section": "consents_and_declarations", "question_key": "consent_data_processing", "question_text": "Do you consent to the processing of your personal data for onboarding purposes?", "question_type": "boolean", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 28},
    {"section": "consents_and_declarations", "question_key": "consent_marketing", "question_text": "Do you consent to receive marketing communications?", "question_type": "boolean", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 29},
    {"section": "consents_and_declarations", "question_key": "declaration_accuracy", "question_text": "I declare that all information provided is accurate and complete to the best of my knowledge.", "question_type": "boolean", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 30},
]


async def seed(session: AsyncSession) -> None:
    existing = await session.get(OnboardingQuestionnaire, QUESTIONNAIRE_ID)
    if existing:
        print("  [skip] questionnaire already exists")
        return

    questionnaire = OnboardingQuestionnaire(
        id=QUESTIONNAIRE_ID,
        name="GlideGate Standard Onboarding Questionnaire",
        description="Comprehensive client data collection questionnaire for all CADF onboarding flows.",
        version=1,
        is_active=True,
        sections=SECTIONS,
        metadata={"brd_ref": "Section 15.3"},
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
    print(f"  [done] {len(QUESTIONS)} questions seeded")


if __name__ == "__main__":
    async def main() -> None:
        async with AsyncSessionLocal() as session:
            await seed(session)

    asyncio.run(main())
