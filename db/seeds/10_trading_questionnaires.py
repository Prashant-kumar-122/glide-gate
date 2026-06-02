"""Seed: 4 institutional trading questionnaires from Trading_Field_Metadata.docx.

Each questionnaire is linked to its corresponding institutional product via product_id
on each OnboardingQuestion. Product-specific prefixes (pb_, dvp_, fcm_, ib_) are
stripped from question_key values since product_id already scopes them.
"""
from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.questionnaire import OnboardingQuestion, OnboardingQuestionnaire
from seed_constants import (
    DVP_PRODUCT_ID,
    DVP_QUESTIONNAIRE_ID,
    FCM_PRODUCT_ID,
    FCM_QUESTIONNAIRE_ID,
    IBCASH_PRODUCT_ID,
    IBCASH_QUESTIONNAIRE_ID,
    PB_PRODUCT_ID,
    PB_QUESTIONNAIRE_ID,
)

# ---------------------------------------------------------------------------
# Prime Brokerage — 40 questions
# ---------------------------------------------------------------------------
PB_QUESTIONS = [
    # applicant_information
    {"question_key": "legal_entity_name", "question_text": "Legal entity name", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 1},
    {"question_key": "trading_dba_name", "question_text": "Trading / DBA name", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 2},
    {"question_key": "entity_type", "question_text": "Entity type", "question_type": "select", "section": "applicant_information", "options": ["Hedge Fund", "Family Office", "Asset Manager", "Prop Trading Firm", "Pension Fund", "SWF", "Other"], "validation_rules": {"required": True}, "show_if": None, "order_index": 3},
    {"question_key": "jurisdiction_of_incorporation", "question_text": "Jurisdiction of incorporation", "question_type": "select", "section": "applicant_information", "options": ["United States", "Cayman Islands", "UK", "Luxembourg", "Ireland", "Singapore", "Other"], "validation_rules": {"required": True}, "show_if": None, "order_index": 4},
    {"question_key": "date_of_incorporation", "question_text": "Date of incorporation", "question_type": "date", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 5},
    {"question_key": "lei", "question_text": "LEI (Legal Entity Identifier)", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": False, "max_length": 20}, "show_if": None, "order_index": 6},
    {"question_key": "registered_address", "question_text": "Registered address", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 7},
    {"question_key": "principal_place_of_business", "question_text": "Principal place of business", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 8},
    # regulatory_compliance
    {"question_key": "primary_regulator", "question_text": "Primary regulator", "question_type": "select", "section": "regulatory_compliance", "options": ["SEC", "CFTC", "FCA", "ESMA", "MAS", "ASIC", "Unregulated"], "validation_rules": {"required": True}, "show_if": None, "order_index": 9},
    {"question_key": "registration_licence_number", "question_text": "Registration / licence number", "question_type": "text", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 10},
    {"question_key": "fatca_status", "question_text": "FATCA status", "question_type": "select", "section": "regulatory_compliance", "options": ["US Person", "Non-US FATCA FFI", "Non-US Exempt", "GIIN Registered"], "validation_rules": {"required": True}, "show_if": None, "order_index": 11},
    {"question_key": "giin", "question_text": "GIIN (if applicable)", "question_type": "text", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": False, "max_length": 19}, "show_if": {"field": "fatca_status", "value": "GIIN Registered", "operator": "eq"}, "order_index": 12},
    {"question_key": "subject_to_sanctions", "question_text": "Subject to sanctions or restrictions?", "question_type": "select", "section": "regulatory_compliance", "options": ["No", "Yes — provide details"], "validation_rules": {"required": True}, "show_if": None, "order_index": 13},
    {"question_key": "aml_programme", "question_text": "AML programme in place?", "question_type": "select", "section": "regulatory_compliance", "options": ["Yes — formal policy", "Yes — informal", "No"], "validation_rules": {"required": True}, "show_if": None, "order_index": 14},
    {"question_key": "mifid_emir_classification", "question_text": "MiFID II / EMIR classification", "question_type": "select", "section": "regulatory_compliance", "options": ["ECP", "Financial Counterparty", "Non-Financial", "N/A"], "validation_rules": {"required": False}, "show_if": None, "order_index": 15},
    {"question_key": "reporting_counterparty_otc", "question_text": "Reporting counterparty for OTC?", "question_type": "select", "section": "regulatory_compliance", "options": ["Yes", "No", "Not applicable"], "validation_rules": {"required": False}, "show_if": None, "order_index": 16},
    {"question_key": "compliance_notes", "question_text": "Compliance notes / disclosures", "question_type": "text", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 17},
    # financial_profile
    {"question_key": "estimated_aum", "question_text": "Estimated AUM (USD)", "question_type": "select", "section": "financial_profile", "options": ["Under $50M", "$50M-$250M", "$250M-$1B", "$1B-$5B", "$5B+"], "validation_rules": {"required": True}, "show_if": None, "order_index": 18},
    {"question_key": "expected_monthly_turnover", "question_text": "Expected monthly notional turnover", "question_type": "select", "section": "financial_profile", "options": ["Under $10M", "$10M-$100M", "$100M-$1B", "$1B+"], "validation_rules": {"required": False}, "show_if": None, "order_index": 19},
    {"question_key": "target_gross_leverage", "question_text": "Target gross leverage", "question_type": "select", "section": "financial_profile", "options": ["1x-2x", "2x-5x", "5x-10x", "10x+"], "validation_rules": {"required": False}, "show_if": None, "order_index": 20},
    {"question_key": "asset_classes_traded", "question_text": "Asset classes traded", "question_type": "multi_select", "section": "financial_profile", "options": ["Equities", "Fixed Income", "OTC Derivatives", "Listed Derivatives", "FX", "Commodities", "Crypto", "Structured Products"], "validation_rules": {"required": True, "min_items": 1}, "show_if": None, "order_index": 21},
    # services_requested
    {"question_key": "services_required", "question_text": "Prime brokerage services required", "question_type": "multi_select", "section": "services_requested", "options": ["Securities Lending", "Margin Financing", "Custody & Settlement", "Synthetic Prime", "Capital Introduction", "Risk Reporting", "FX Execution", "Technology"], "validation_rules": {"required": True, "min_items": 1}, "show_if": None, "order_index": 22},
    {"question_key": "preferred_execution_venues", "question_text": "Preferred execution venues", "question_type": "text", "section": "services_requested", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 23},
    {"question_key": "existing_pb_relationships", "question_text": "Existing prime broker relationships", "question_type": "text", "section": "services_requested", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 24},
    {"question_key": "multi_prime_strategy", "question_text": "Multi-prime strategy?", "question_type": "select", "section": "services_requested", "options": ["No", "Yes — describe allocation"], "validation_rules": {"required": False}, "show_if": None, "order_index": 25},
    # authorised_contacts
    {"question_key": "primary_contact_name", "question_text": "Primary contact name", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 26},
    {"question_key": "primary_contact_title", "question_text": "Title / role", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 27},
    {"question_key": "primary_contact_email", "question_text": "Email address", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 28},
    {"question_key": "primary_contact_phone", "question_text": "Direct phone", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 29},
    {"question_key": "compliance_officer_name", "question_text": "Compliance officer name", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 30},
    {"question_key": "compliance_officer_email", "question_text": "Compliance officer email", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 31},
    {"question_key": "operations_contact_name", "question_text": "Operations contact name", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 32},
    {"question_key": "operations_contact_email", "question_text": "Operations contact email", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 33},
    # declarations
    {"question_key": "info_accurate", "question_text": "All information is accurate and complete", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 34},
    {"question_key": "kyc_authorise", "question_text": "Authorise KYC / AML due diligence", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 35},
    {"question_key": "agreement_subject", "question_text": "Services subject to Prime Brokerage Agreement", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 36},
    {"question_key": "privacy_consent", "question_text": "Consent to data privacy policy", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 37},
    {"question_key": "signatory_name", "question_text": "Authorised signatory name", "question_type": "text", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 38},
    {"question_key": "signatory_title", "question_text": "Capacity / title", "question_type": "text", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 39},
    {"question_key": "sign_date", "question_text": "Date", "question_type": "date", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 40},
]

# ---------------------------------------------------------------------------
# DVP — 40 questions
# ---------------------------------------------------------------------------
DVP_QUESTIONS = [
    # applicant_information
    {"question_key": "institution_name", "question_text": "Institution name", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 1},
    {"question_key": "institution_type", "question_text": "Institution type", "question_type": "select", "section": "applicant_information", "options": ["Broker-Dealer", "Custodian Bank", "Asset Manager", "Insurance", "Pension Fund", "Central Bank"], "validation_rules": {"required": True}, "show_if": None, "order_index": 2},
    {"question_key": "lei", "question_text": "LEI", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True, "max_length": 20}, "show_if": None, "order_index": 3},
    {"question_key": "jurisdiction", "question_text": "Jurisdiction", "question_type": "select", "section": "applicant_information", "options": ["United States", "UK", "EU", "Singapore", "Japan", "Other"], "validation_rules": {"required": True}, "show_if": None, "order_index": 4},
    {"question_key": "registered_address", "question_text": "Registered address", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 5},
    {"question_key": "principal_office", "question_text": "Principal office address", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 6},
    # regulatory_compliance
    {"question_key": "regulatory_body", "question_text": "Regulatory body", "question_type": "select", "section": "regulatory_compliance", "options": ["SEC", "FCA", "ESMA", "MAS", "FSA Japan", "Other"], "validation_rules": {"required": True}, "show_if": None, "order_index": 7},
    {"question_key": "registration_number", "question_text": "Registration number", "question_type": "text", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 8},
    {"question_key": "sanctions_screening_status", "question_text": "Sanctions screening status", "question_type": "select", "section": "regulatory_compliance", "options": ["Cleared — no restrictions", "Subject to restrictions"], "validation_rules": {"required": True}, "show_if": None, "order_index": 9},
    {"question_key": "ofac_un_listed", "question_text": "OFAC / UN listed entity?", "question_type": "boolean", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 10},
    {"question_key": "cross_border_eligible", "question_text": "Eligible for cross-border settlement?", "question_type": "boolean", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 11},
    {"question_key": "csdr_discipline", "question_text": "Subject to CSDR settlement discipline?", "question_type": "select", "section": "regulatory_compliance", "options": ["Yes", "No", "Not applicable"], "validation_rules": {"required": False}, "show_if": None, "order_index": 12},
    # custodian_details
    {"question_key": "custodian_bank_name", "question_text": "Custodian bank name", "question_type": "text", "section": "custodian_details", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 13},
    {"question_key": "custodian_account_number", "question_text": "Custodian account number", "question_type": "text", "section": "custodian_details", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 14},
    {"question_key": "dtc_participant_number", "question_text": "DTC participant number", "question_type": "text", "section": "custodian_details", "options": [], "validation_rules": {"required": False, "max_length": 4}, "show_if": None, "order_index": 15},
    {"question_key": "euroclear_clearstream_account", "question_text": "Euroclear / Clearstream account", "question_type": "text", "section": "custodian_details", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 16},
    {"question_key": "bic_swift_code", "question_text": "BIC / SWIFT code", "question_type": "text", "section": "custodian_details", "options": [], "validation_rules": {"required": True, "min_length": 8, "max_length": 11}, "show_if": None, "order_index": 17},
    {"question_key": "iban", "question_text": "IBAN (if applicable)", "question_type": "text", "section": "custodian_details", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 18},
    {"question_key": "csd_membership", "question_text": "CSD membership", "question_type": "text", "section": "custodian_details", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 19},
    {"question_key": "sub_custodian_name", "question_text": "Sub-custodian name (if applicable)", "question_type": "text", "section": "custodian_details", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 20},
    # settlement_instructions
    {"question_key": "settlement_currency", "question_text": "Settlement currency", "question_type": "select", "section": "settlement_instructions", "options": ["USD", "EUR", "GBP", "JPY", "CHF", "SGD", "Other"], "validation_rules": {"required": True}, "show_if": None, "order_index": 21},
    {"question_key": "settlement_cycle", "question_text": "Settlement cycle", "question_type": "select", "section": "settlement_instructions", "options": ["T+0 (Same day)", "T+1", "T+2"], "validation_rules": {"required": True}, "show_if": None, "order_index": 22},
    {"question_key": "fail_trade_handling", "question_text": "Fail trade handling", "question_type": "select", "section": "settlement_instructions", "options": ["Auto buy-in", "Manual resolution", "Bilateral agreement"], "validation_rules": {"required": True}, "show_if": None, "order_index": 23},
    {"question_key": "cash_account_aba_routing", "question_text": "Cash account / ABA routing details", "question_type": "text", "section": "settlement_instructions", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 24},
    {"question_key": "special_settlement_instructions", "question_text": "Special settlement instructions", "question_type": "text", "section": "settlement_instructions", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 25},
    {"question_key": "daylight_overdraft", "question_text": "Daylight overdraft facility?", "question_type": "boolean", "section": "settlement_instructions", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 26},
    {"question_key": "auto_borrow", "question_text": "Auto-borrow for short settlement?", "question_type": "boolean", "section": "settlement_instructions", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 27},
    # authorised_contacts
    {"question_key": "ops_contact_name", "question_text": "Operations contact name", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 28},
    {"question_key": "ops_email", "question_text": "Email", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 29},
    {"question_key": "ops_phone", "question_text": "Phone (direct)", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 30},
    {"question_key": "settlement_escalation_contact", "question_text": "Settlement escalation contact", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 31},
    {"question_key": "escalation_email", "question_text": "Escalation email", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 32},
    {"question_key": "emergency_line_24hr", "question_text": "24hr emergency line", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 33},
    # declarations
    {"question_key": "instructions_accurate", "question_text": "Settlement instructions are accurate and authorised", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 34},
    {"question_key": "csd_rules", "question_text": "DVP settlement subject to applicable CSD rules", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 35},
    {"question_key": "electronic_confirm", "question_text": "Consent to electronic settlement confirmations", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 36},
    {"question_key": "fail_charges", "question_text": "Acknowledge responsibility for failed settlement charges", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 37},
    {"question_key": "signatory_name", "question_text": "Authorised signatory name", "question_type": "text", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 38},
    {"question_key": "signatory_title", "question_text": "Title", "question_type": "text", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 39},
    {"question_key": "sign_date", "question_text": "Date", "question_type": "date", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 40},
]

# ---------------------------------------------------------------------------
# FCM — 41 questions
# ---------------------------------------------------------------------------
FCM_QUESTIONS = [
    # applicant_information
    {"question_key": "legal_name", "question_text": "Legal name", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 1},
    {"question_key": "client_type", "question_text": "Client type", "question_type": "select", "section": "applicant_information", "options": ["Individual", "Corporation", "Partnership", "Trust", "CPO", "CTA"], "validation_rules": {"required": True}, "show_if": None, "order_index": 2},
    {"question_key": "tax_id", "question_text": "Tax ID / EIN / SSN", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 3},
    {"question_key": "country_of_residence", "question_text": "Country of residence / domicile", "question_type": "select", "section": "applicant_information", "options": ["United States", "UK", "EU", "Singapore", "India", "Other"], "validation_rules": {"required": True}, "show_if": None, "order_index": 4},
    {"question_key": "business_address", "question_text": "Principal business address", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 5},
    {"question_key": "dob", "question_text": "Date of birth / incorporation", "question_type": "date", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 6},
    {"question_key": "nationality", "question_text": "Nationality / country of registration", "question_type": "select", "section": "applicant_information", "options": ["United States", "UK", "EU", "Singapore", "India", "Other"], "validation_rules": {"required": True}, "show_if": None, "order_index": 7},
    # regulatory_compliance
    {"question_key": "nfa_cftc_id", "question_text": "NFA ID / CFTC registration number", "question_type": "text", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 8},
    {"question_key": "registration_category", "question_text": "Registration category", "question_type": "select", "section": "regulatory_compliance", "options": ["CPO", "CTA", "IB", "Floor Broker", "Not registered"], "validation_rules": {"required": False}, "show_if": None, "order_index": 9},
    {"question_key": "is_ecp", "question_text": "Are you an ECP (Eligible Contract Participant)?", "question_type": "boolean", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 10},
    {"question_key": "cftc_dodd_frank", "question_text": "CFTC / Dodd-Frank reporting obligations?", "question_type": "select", "section": "regulatory_compliance", "options": ["Yes — swap dealer", "Yes — major swap participant", "No"], "validation_rules": {"required": False}, "show_if": None, "order_index": 11},
    {"question_key": "subject_to_position_limits", "question_text": "Subject to position limits?", "question_type": "select", "section": "regulatory_compliance", "options": ["No", "Yes — provide details"], "validation_rules": {"required": True}, "show_if": None, "order_index": 12},
    {"question_key": "experienced_investor_declaration", "question_text": "Experienced investor declaration", "question_type": "select", "section": "regulatory_compliance", "options": ["Yes — on file", "Not yet — request to be sent"], "validation_rules": {"required": True}, "show_if": None, "order_index": 13},
    {"question_key": "exchange_memberships", "question_text": "Relevant exchange memberships", "question_type": "text", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 14},
    {"question_key": "clearing_member", "question_text": "Clearing member (if applicable)", "question_type": "text", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 15},
    # financial_profile
    {"question_key": "net_worth_aum", "question_text": "Net worth / AUM (USD)", "question_type": "select", "section": "financial_profile", "options": ["Under $1M", "$1M-$10M", "$10M-$100M", "$100M+"], "validation_rules": {"required": True}, "show_if": None, "order_index": 16},
    {"question_key": "initial_margin_deposit", "question_text": "Initial margin deposit (USD)", "question_type": "number", "section": "financial_profile", "options": [], "validation_rules": {"required": True, "min_value": 0}, "show_if": None, "order_index": 17},
    {"question_key": "funding_method", "question_text": "Funding method", "question_type": "select", "section": "financial_profile", "options": ["Wire transfer", "ACH", "Securities transfer", "T-bills", "Treasuries"], "validation_rules": {"required": True}, "show_if": None, "order_index": 18},
    {"question_key": "tbill_collateral", "question_text": "T-bill / Treasury collateral accepted?", "question_type": "boolean", "section": "financial_profile", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 19},
    {"question_key": "futures_products_of_interest", "question_text": "Futures products of interest", "question_type": "multi_select", "section": "financial_profile", "options": ["Interest Rate", "Equity Index", "Agriculture", "Energy", "Metals", "FX", "Crypto", "Volatility (VIX)"], "validation_rules": {"required": True, "min_items": 1}, "show_if": None, "order_index": 20},
    # trading_services
    {"question_key": "years_futures_experience", "question_text": "Years of futures trading experience", "question_type": "select", "section": "trading_services", "options": ["Under 1 yr", "1-3 yrs", "3-5 yrs", "5+ yrs"], "validation_rules": {"required": True}, "show_if": None, "order_index": 21},
    {"question_key": "avg_monthly_contract_volume", "question_text": "Average monthly contract volume", "question_type": "select", "section": "trading_services", "options": ["Under 100", "100-1,000", "1,000-10,000", "10,000+"], "validation_rules": {"required": False}, "show_if": None, "order_index": 22},
    {"question_key": "execution_method", "question_text": "Execution method", "question_type": "select", "section": "trading_services", "options": ["Electronic DMA", "Electronic via IB", "Voice", "Algo", "Automated"], "validation_rules": {"required": True}, "show_if": None, "order_index": 23},
    {"question_key": "giveup_stepout", "question_text": "Give-up / step-out arrangements required?", "question_type": "select", "section": "trading_services", "options": ["No", "Yes — provide clearing firm details"], "validation_rules": {"required": True}, "show_if": None, "order_index": 24},
    {"question_key": "preferred_exchanges", "question_text": "Preferred exchanges", "question_type": "text", "section": "trading_services", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 25},
    {"question_key": "algo_trading", "question_text": "Algorithmic trading in use?", "question_type": "select", "section": "trading_services", "options": ["No", "Yes — proprietary", "Yes — third-party system"], "validation_rules": {"required": False}, "show_if": None, "order_index": 26},
    {"question_key": "strategy_type", "question_text": "Strategy type", "question_type": "select", "section": "trading_services", "options": ["Hedging", "Speculative", "Both"], "validation_rules": {"required": False}, "show_if": None, "order_index": 27},
    {"question_key": "intraday_or_overnight", "question_text": "Intraday or overnight positions?", "question_type": "select", "section": "trading_services", "options": ["Intraday only", "Overnight", "Both"], "validation_rules": {"required": False}, "show_if": None, "order_index": 28},
    # authorised_contacts
    {"question_key": "primary_contact", "question_text": "Primary contact name", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 29},
    {"question_key": "contact_title", "question_text": "Title", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 30},
    {"question_key": "contact_phone", "question_text": "Phone", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 31},
    {"question_key": "contact_email", "question_text": "Email", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 32},
    {"question_key": "margin_call_contact", "question_text": "Margin call contact name", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 33},
    {"question_key": "margin_call_email_sms", "question_text": "Margin call email / SMS", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 34},
    # declarations
    {"question_key": "risk_disclosure", "question_text": "Read and understood risk disclosure statement", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 35},
    {"question_key": "risk_of_loss", "question_text": "Acknowledge substantial risk of loss in futures", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 36},
    {"question_key": "liquidation_auth", "question_text": "Authorise FCM to liquidate positions for margin", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 37},
    {"question_key": "info_accurate", "question_text": "All information is accurate and signatory is authorised", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 38},
    {"question_key": "signatory_name", "question_text": "Authorised signatory name", "question_type": "text", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 39},
    {"question_key": "signatory_title", "question_text": "Title", "question_type": "text", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 40},
    {"question_key": "sign_date", "question_text": "Date", "question_type": "date", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 41},
]

# ---------------------------------------------------------------------------
# IBCash — 50 questions
# ---------------------------------------------------------------------------
IBCASH_QUESTIONS = [
    # applicant_information
    {"question_key": "firm_name", "question_text": "IB firm name", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 1},
    {"question_key": "registration_number", "question_text": "IB registration number", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 2},
    {"question_key": "clearing_firm", "question_text": "Clearing firm", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 3},
    {"question_key": "clearing_agreement_date", "question_text": "Clearing agreement date", "question_type": "date", "section": "applicant_information", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 4},
    {"question_key": "type", "question_text": "IB type", "question_type": "select", "section": "applicant_information", "options": ["Fully disclosed IB", "Omnibus IB", "Independent IB"], "validation_rules": {"required": True}, "show_if": None, "order_index": 5},
    {"question_key": "office_address", "question_text": "IB office address", "question_type": "text", "section": "applicant_information", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 6},
    {"question_key": "net_capital_last_filing", "question_text": "Net capital as of last filing (USD)", "question_type": "number", "section": "applicant_information", "options": [], "validation_rules": {"required": False, "min_value": 0}, "show_if": None, "order_index": 7},
    {"question_key": "supervising_regulator", "question_text": "Supervising regulator", "question_type": "select", "section": "applicant_information", "options": ["FINRA", "SEC", "FCA", "SEBI", "MAS", "Other"], "validation_rules": {"required": True}, "show_if": None, "order_index": 8},
    # regulatory_compliance
    {"question_key": "current_disciplinary_actions", "question_text": "Current disciplinary actions?", "question_type": "select", "section": "regulatory_compliance", "options": ["None", "Yes — disclose details"], "validation_rules": {"required": False}, "show_if": None, "order_index": 9},
    {"question_key": "client_money_segregation", "question_text": "Client money / segregation model", "question_type": "select", "section": "regulatory_compliance", "options": ["Fully segregated", "Cleared via carrying broker", "Omnibus daily rec"], "validation_rules": {"required": True}, "show_if": None, "order_index": 10},
    {"question_key": "finra_brokercheck", "question_text": "FINRA BrokerCheck disclosure?", "question_type": "select", "section": "regulatory_compliance", "options": ["No", "Yes — details below"], "validation_rules": {"required": False}, "show_if": None, "order_index": 11},
    {"question_key": "ofac_restrictions", "question_text": "Subject to OFAC restrictions?", "question_type": "boolean", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 12},
    {"question_key": "disclosure_details", "question_text": "Details of any disclosures", "question_type": "text", "section": "regulatory_compliance", "options": [], "validation_rules": {"required": False}, "show_if": {"field": "current_disciplinary_actions", "value": "Yes — disclose details", "operator": "eq"}, "order_index": 13},
    # end_client_details
    {"question_key": "client_full_name", "question_text": "Client full name", "question_type": "text", "section": "end_client_details", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 14},
    {"question_key": "client_account_type", "question_text": "Client account type", "question_type": "select", "section": "end_client_details", "options": ["Individual", "Joint", "Corporate", "Trust", "IRA", "Retirement"], "validation_rules": {"required": True}, "show_if": None, "order_index": 15},
    {"question_key": "client_dob", "question_text": "Date of birth / incorporation", "question_type": "date", "section": "end_client_details", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 16},
    {"question_key": "client_country_of_citizenship", "question_text": "Country of citizenship / registration", "question_type": "select", "section": "end_client_details", "options": ["United States", "UK", "India", "Singapore", "Canada", "Other"], "validation_rules": {"required": True}, "show_if": None, "order_index": 17},
    {"question_key": "government_id_type", "question_text": "Government ID type", "question_type": "select", "section": "end_client_details", "options": ["Passport", "National ID card", "Driver's licence", "Company reg. cert."], "validation_rules": {"required": True}, "show_if": None, "order_index": 18},
    {"question_key": "client_id_number", "question_text": "ID number", "question_type": "text", "section": "end_client_details", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 19},
    {"question_key": "client_address", "question_text": "Residential / registered address", "question_type": "text", "section": "end_client_details", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 20},
    {"question_key": "client_email", "question_text": "Email address", "question_type": "text", "section": "end_client_details", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 21},
    {"question_key": "client_mobile", "question_text": "Mobile number", "question_type": "text", "section": "end_client_details", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 22},
    # financial_profile
    {"question_key": "annual_income", "question_text": "Annual income (USD)", "question_type": "select", "section": "financial_profile", "options": ["Under $50K", "$50K-$150K", "$150K-$500K", "$500K+"], "validation_rules": {"required": True}, "show_if": None, "order_index": 23},
    {"question_key": "liquid_net_worth", "question_text": "Estimated liquid net worth (USD)", "question_type": "select", "section": "financial_profile", "options": ["Under $50K", "$50K-$250K", "$250K-$1M", "$1M+"], "validation_rules": {"required": True}, "show_if": None, "order_index": 24},
    {"question_key": "total_net_worth", "question_text": "Total net worth (USD)", "question_type": "select", "section": "financial_profile", "options": ["Under $100K", "$100K-$500K", "$500K-$2M", "$2M+"], "validation_rules": {"required": False}, "show_if": None, "order_index": 25},
    {"question_key": "source_of_funds", "question_text": "Source of funds", "question_type": "select", "section": "financial_profile", "options": ["Employment", "Business income", "Investment returns", "Inheritance", "Other"], "validation_rules": {"required": True}, "show_if": None, "order_index": 26},
    {"question_key": "employer_name", "question_text": "Employer / business name", "question_type": "text", "section": "financial_profile", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 27},
    {"question_key": "years_employment", "question_text": "Years of employment", "question_type": "number", "section": "financial_profile", "options": [], "validation_rules": {"required": False, "min_value": 0}, "show_if": None, "order_index": 28},
    # suitability_profile
    {"question_key": "investment_objective", "question_text": "Investment objective", "question_type": "select", "section": "suitability_profile", "options": ["Capital preservation", "Income", "Growth", "Aggressive growth", "Speculation"], "validation_rules": {"required": True}, "show_if": None, "order_index": 29},
    {"question_key": "risk_tolerance", "question_text": "Risk tolerance", "question_type": "select", "section": "suitability_profile", "options": ["Conservative", "Moderate", "Aggressive", "Speculative"], "validation_rules": {"required": True}, "show_if": None, "order_index": 30},
    {"question_key": "time_horizon", "question_text": "Investment time horizon", "question_type": "select", "section": "suitability_profile", "options": ["Short term (under 1 yr)", "Medium term (1-5 yrs)", "Long term (5+ yrs)"], "validation_rules": {"required": True}, "show_if": None, "order_index": 31},
    {"question_key": "prior_experience", "question_text": "Prior investment experience", "question_type": "select", "section": "suitability_profile", "options": ["None", "Limited 1-2 yrs", "Moderate 3-5 yrs", "Extensive 5+ yrs"], "validation_rules": {"required": True}, "show_if": None, "order_index": 32},
    {"question_key": "options_approval", "question_text": "Options trading approval requested?", "question_type": "select", "section": "suitability_profile", "options": ["No", "Level 1 (covered calls)", "Level 2 (buying puts & calls)"], "validation_rules": {"required": False}, "show_if": None, "order_index": 33},
    {"question_key": "discretionary_advisory", "question_text": "Discretionary or advisory relationship?", "question_type": "select", "section": "suitability_profile", "options": ["Self-directed", "Discretionary managed", "Non-discretionary advisory"], "validation_rules": {"required": False}, "show_if": None, "order_index": 34},
    {"question_key": "preferred_comm_channel", "question_text": "Preferred communication channel", "question_type": "select", "section": "suitability_profile", "options": ["Email", "Phone", "Portal", "Online"], "validation_rules": {"required": False}, "show_if": None, "order_index": 35},
    {"question_key": "special_instructions", "question_text": "Special instructions or restrictions", "question_type": "text", "section": "suitability_profile", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 36},
    # authorised_contacts
    {"question_key": "primary_contact_name", "question_text": "IB primary contact name", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 37},
    {"question_key": "contact_email", "question_text": "IB contact email", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 38},
    {"question_key": "contact_phone", "question_text": "IB contact phone", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 39},
    {"question_key": "client_preferred_email", "question_text": "Client preferred email", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 40},
    {"question_key": "client_mobile_alerts", "question_text": "Client mobile (for alerts)", "question_type": "text", "section": "authorised_contacts", "options": [], "validation_rules": {"required": False}, "show_if": None, "order_index": 41},
    {"question_key": "preferred_communication", "question_text": "Preferred communication", "question_type": "select", "section": "authorised_contacts", "options": ["Email", "Phone", "Portal", "Online"], "validation_rules": {"required": False}, "show_if": None, "order_index": 42},
    # declarations
    {"question_key": "client_info_accurate", "question_text": "Client information is accurate and verified by IB", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 43},
    {"question_key": "cash_account_ack", "question_text": "Acknowledge cash account — no margin / no short selling", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 44},
    {"question_key": "kyc_aml", "question_text": "KYC / AML checks conducted by IB", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 45},
    {"question_key": "suitability_responsibility", "question_text": "Suitability assessment responsibility of IB", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 46},
    {"question_key": "agreements_accepted", "question_text": "Client has received and accepted all agreements", "question_type": "boolean", "section": "declarations", "options": [], "validation_rules": {"required": True, "must_be_true": True}, "show_if": None, "order_index": 47},
    {"question_key": "signatory_name", "question_text": "IB authorised signatory name", "question_type": "text", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 48},
    {"question_key": "signatory_title", "question_text": "Title", "question_type": "text", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 49},
    {"question_key": "sign_date", "question_text": "Date", "question_type": "date", "section": "declarations", "options": [], "validation_rules": {"required": True}, "show_if": None, "order_index": 50},
]

# ---------------------------------------------------------------------------
# Questionnaire definitions
# ---------------------------------------------------------------------------
QUESTIONNAIRES = [
    {
        "id": PB_QUESTIONNAIRE_ID,
        "name": "Prime Brokerage Enrollment Form",
        "description": "Institutional onboarding questionnaire for prime brokerage clients.",
        "product_id": PB_PRODUCT_ID,
        "questions": PB_QUESTIONS,
        "product_type_label": "Prime Brokerage",
    },
    {
        "id": DVP_QUESTIONNAIRE_ID,
        "name": "DVP Settlement Enrollment Form",
        "description": "Institutional onboarding questionnaire for DVP settlement clients.",
        "product_id": DVP_PRODUCT_ID,
        "questions": DVP_QUESTIONS,
        "product_type_label": "DVP",
    },
    {
        "id": FCM_QUESTIONNAIRE_ID,
        "name": "FCM Futures Account Enrollment Form",
        "description": "Institutional onboarding questionnaire for FCM futures trading clients.",
        "product_id": FCM_PRODUCT_ID,
        "questions": FCM_QUESTIONS,
        "product_type_label": "FCM",
    },
    {
        "id": IBCASH_QUESTIONNAIRE_ID,
        "name": "IBCash Account Enrollment Form",
        "description": "Institutional onboarding questionnaire for IB-introduced cash account clients.",
        "product_id": IBCASH_PRODUCT_ID,
        "questions": IBCASH_QUESTIONS,
        "product_type_label": "IBCash",
    },
]


async def seed(session: AsyncSession) -> None:
    from sqlalchemy import select

    for qdata in QUESTIONNAIRES:
        q_id: UUID = qdata["id"]
        product_id: UUID = qdata["product_id"]
        label: str = qdata["product_type_label"]

        # Upsert questionnaire
        existing_q = await session.get(OnboardingQuestionnaire, q_id)
        if existing_q:
            print(f"  [skip] questionnaire '{qdata['name']}' already exists")
        else:
            questionnaire = OnboardingQuestionnaire(
                id=q_id,
                name=qdata["name"],
                description=qdata["description"],
                version=1,
                is_active=True,
                sections=[],
                extra_metadata={"product_type": label},
            )
            session.add(questionnaire)
            print(f"  [seed] questionnaire '{qdata['name']}'")

        await session.flush()

        # Upsert questions
        for qrow in qdata["questions"]:
            result = await session.execute(
                select(OnboardingQuestion).where(
                    OnboardingQuestion.questionnaire_id == q_id,
                    OnboardingQuestion.question_key == qrow["question_key"],
                )
            )
            existing_question = result.scalar_one_or_none()
            if existing_question:
                continue

            question = OnboardingQuestion(
                questionnaire_id=q_id,
                product_id=product_id,
                section=qrow["section"],
                question_key=qrow["question_key"],
                question_text=qrow["question_text"],
                question_type=qrow["question_type"],
                options=qrow["options"],
                validation_rules=qrow["validation_rules"],
                show_if=qrow["show_if"],
                order_index=qrow["order_index"],
                is_required=qrow["validation_rules"].get("required", True),
                extra_metadata={"product_type": label},
            )
            session.add(question)

        total = len(qdata["questions"])
        print(f"  [seed] {total} questions for '{qdata['name']}'")

    await session.commit()


if __name__ == "__main__":
    async def main() -> None:
        async with AsyncSessionLocal() as session:
            await seed(session)

    asyncio.run(main())
