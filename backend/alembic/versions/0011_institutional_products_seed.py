"""Seed 4 institutional trading products (GCF, ECM, DCM, TFE) with onboarding questions

Revision ID: 0011_institutional_products_seed
Revises: 0010_add_sales_manager_role
Create Date: 2026-06-04

Changes:
- Widen oqn_type_chk to include 'textarea' and 'email' question types
- Deactivate all pre-existing institutional products
- Insert questionnaires and products for GCF, ECM, DCM, TFE
- Insert per-product onboarding questions linked via product_id
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0011_institutional_products_seed"
down_revision = "0010_add_sales_manager_role"
branch_labels = None
depends_on = None

# ── Fixed UUIDs ───────────────────────────────────────────────────────────────
_GCF_PID = "a1111111-0001-0001-0001-000000000001"
_ECM_PID = "a1111111-0001-0001-0001-000000000002"
_DCM_PID = "a1111111-0001-0001-0001-000000000003"
_TFE_PID = "a1111111-0001-0001-0001-000000000004"

_GCF_QID = "b1111111-0001-0001-0001-000000000001"
_ECM_QID = "b1111111-0001-0001-0001-000000000002"
_DCM_QID = "b1111111-0001-0001-0001-000000000003"
_TFE_QID = "b1111111-0001-0001-0001-000000000004"

_NEW_PRODUCT_CODES = ("GCF", "ECM", "DCM", "TFE")

# ── Common option arrays ──────────────────────────────────────────────────────
_ENTITY_TYPES  = json.dumps(["Hedge Fund", "Family Office", "Asset Manager", "Prop Trading Firm", "Pension Fund", "SWF", "Other"])
_JURISDICTIONS = json.dumps(["United States", "Cayman Islands", "UK", "Luxembourg", "Ireland", "Singapore", "Other"])
_REGULATORS    = json.dumps(["SEC", "CFTC", "FCA", "ESMA", "MAS", "ASIC", "Unregulated"])
_OTC_OPTS      = json.dumps(["Yes", "No", "Not applicable"])
_AUM_OPTS      = json.dumps(["Under $50M", "$50M-$250M", "$250M-$1B", "$1B-$5B", "$5B+"])
_TURNOVER_OPTS = json.dumps(["Under $10M", "$10M-$100M", "$100M-$1B", "$1B+"])
_LEVERAGE_OPTS = json.dumps(["1x-2x", "2x-5x", "5x-10x", "10x+"])
_ASSET_CLASSES = json.dumps(["Equities", "Fixed Income", "OTC Derivatives", "Listed Derivatives", "FX", "Commodities", "Crypto", "Structured Products"])
_CLIENT_TYPES  = json.dumps(["Individual", "Corporation", "Partnership", "Trust", "CPO", "CTA"])
_EMPTY_OPTS    = json.dumps([])

# ── Validation rule presets ───────────────────────────────────────────────────
_VR_REQ   = json.dumps({"required": True})
_VR_OPT   = json.dumps({"required": False})
_VR_LEI   = json.dumps({"required": False, "max_length": 20})
_VR_MULTI = json.dumps({"required": True, "min_items": 1})

# ── Question definitions ──────────────────────────────────────────────────────
# Each tuple: (section, field_key, question_text, qtype, options, validation, order_idx, is_required)

_COMMON_FIRST_9 = [
    ("applicant_information", "legal_entity_name",            "Legal entity name",                  "text",         _EMPTY_OPTS,    _VR_REQ,   1, True),
    ("applicant_information", "entity_type",                   "Entity type",                        "select",       _ENTITY_TYPES,  _VR_REQ,   2, True),
    ("applicant_information", "jurisdiction_of_incorporation", "Jurisdiction of incorporation",      "select",       _JURISDICTIONS, _VR_REQ,   3, True),
    ("applicant_information", "lei",                           "LEI (Legal Entity Identifier)",      "text",         _EMPTY_OPTS,    _VR_LEI,   4, False),
    ("regulatory_compliance", "primary_regulator",             "Primary regulator",                  "select",       _REGULATORS,    _VR_REQ,   5, True),
    ("regulatory_compliance", "reporting_counterparty_otc",    "Reporting counterparty for OTC?",    "select",       _OTC_OPTS,      _VR_OPT,   6, False),
    ("regulatory_compliance", "compliance_notes",              "Compliance notes / disclosures",     "textarea",     _EMPTY_OPTS,    _VR_OPT,   7, False),
    ("financial_profile",     "estimated_aum",                 "Estimated AUM (USD)",                "select",       _AUM_OPTS,      _VR_REQ,   8, True),
    ("financial_profile",     "expected_monthly_turnover",     "Expected monthly notional turnover", "select",       _TURNOVER_OPTS, _VR_OPT,   9, False),
]

# ECM — adds leverage + asset classes + execution/PB questions
_ECM_QUESTIONS = _COMMON_FIRST_9 + [
    ("financial_profile",  "target_gross_leverage",      "Target gross leverage",               "select",       _LEVERAGE_OPTS, _VR_OPT,   10, False),
    ("financial_profile",  "asset_classes_traded",       "Asset classes traded",                "multi_select", _ASSET_CLASSES, _VR_MULTI, 11, True),
    ("services_requested", "preferred_execution_venues", "Preferred execution venues",          "textarea",     _EMPTY_OPTS,    _VR_REQ,   12, True),
    ("services_requested", "existing_pb_relationships",  "Existing prime broker relationships", "textarea",     _EMPTY_OPTS,    _VR_REQ,   13, True),
]

# GCF — adds leverage + asset classes + custodian details
_GCF_QUESTIONS = _COMMON_FIRST_9 + [
    ("financial_profile", "target_gross_leverage",    "Target gross leverage",    "select",       _LEVERAGE_OPTS, _VR_OPT,   10, False),
    ("financial_profile", "asset_classes_traded",     "Asset classes traded",     "multi_select", _ASSET_CLASSES, _VR_MULTI, 11, True),
    ("custodian_details", "custodian_bank_name",      "Custodian bank name",      "text",         _EMPTY_OPTS,    _VR_REQ,   12, True),
    ("custodian_details", "custodian_account_number", "Custodian account number", "text",         _EMPTY_OPTS,    _VR_REQ,   13, True),
]

# DCM — adds client_type (shifts regulatory/financial by one), adds authorised contacts
_DCM_QUESTIONS = [
    ("applicant_information", "legal_entity_name",            "Legal entity name",                  "text",         _EMPTY_OPTS,    _VR_REQ,   1,  True),
    ("applicant_information", "entity_type",                   "Entity type",                        "select",       _ENTITY_TYPES,  _VR_REQ,   2,  True),
    ("applicant_information", "jurisdiction_of_incorporation", "Jurisdiction of incorporation",      "select",       _JURISDICTIONS, _VR_REQ,   3,  True),
    ("applicant_information", "lei",                           "LEI (Legal Entity Identifier)",      "text",         _EMPTY_OPTS,    _VR_LEI,   4,  False),
    ("applicant_information", "client_type",                   "Client type",                        "select",       _CLIENT_TYPES,  _VR_REQ,   5,  True),
    ("regulatory_compliance", "primary_regulator",             "Primary regulator",                  "select",       _REGULATORS,    _VR_REQ,   6,  True),
    ("regulatory_compliance", "reporting_counterparty_otc",    "Reporting counterparty for OTC?",    "select",       _OTC_OPTS,      _VR_OPT,   7,  False),
    ("regulatory_compliance", "compliance_notes",              "Compliance notes / disclosures",     "textarea",     _EMPTY_OPTS,    _VR_OPT,   8,  False),
    ("financial_profile",     "estimated_aum",                 "Estimated AUM (USD)",                "select",       _AUM_OPTS,      _VR_REQ,   9,  True),
    ("financial_profile",     "expected_monthly_turnover",     "Expected monthly notional turnover", "select",       _TURNOVER_OPTS, _VR_OPT,   10, False),
    ("financial_profile",     "target_gross_leverage",         "Target gross leverage",              "select",       _LEVERAGE_OPTS, _VR_OPT,   11, False),
    ("financial_profile",     "asset_classes_traded",          "Asset classes traded",               "multi_select", _ASSET_CLASSES, _VR_MULTI, 12, True),
    ("authorised_contacts",   "primary_contact",               "Primary contact name",               "text",         _EMPTY_OPTS,    _VR_REQ,   13, True),
    ("authorised_contacts",   "contact_title",                 "Title",                              "text",         _EMPTY_OPTS,    _VR_REQ,   14, True),
    ("authorised_contacts",   "contact_phone",                 "Phone",                              "text",         _EMPTY_OPTS,    _VR_REQ,   15, True),
    ("authorised_contacts",   "contact_email",                 "Email",                              "email",        _EMPTY_OPTS,    _VR_REQ,   16, True),
]

# TFE — no target_gross_leverage; ends with execution/PB questions
_TFE_QUESTIONS = [
    ("applicant_information", "legal_entity_name",            "Legal entity name",                  "text",         _EMPTY_OPTS,    _VR_REQ,   1,  True),
    ("applicant_information", "entity_type",                   "Entity type",                        "select",       _ENTITY_TYPES,  _VR_REQ,   2,  True),
    ("applicant_information", "jurisdiction_of_incorporation", "Jurisdiction of incorporation",      "select",       _JURISDICTIONS, _VR_REQ,   3,  True),
    ("applicant_information", "lei",                           "LEI (Legal Entity Identifier)",      "text",         _EMPTY_OPTS,    _VR_LEI,   4,  False),
    ("regulatory_compliance", "primary_regulator",             "Primary regulator",                  "select",       _REGULATORS,    _VR_REQ,   5,  True),
    ("regulatory_compliance", "reporting_counterparty_otc",    "Reporting counterparty for OTC?",    "select",       _OTC_OPTS,      _VR_OPT,   6,  False),
    ("regulatory_compliance", "compliance_notes",              "Compliance notes / disclosures",     "textarea",     _EMPTY_OPTS,    _VR_OPT,   7,  False),
    ("financial_profile",     "estimated_aum",                 "Estimated AUM (USD)",                "select",       _AUM_OPTS,      _VR_REQ,   8,  True),
    ("financial_profile",     "expected_monthly_turnover",     "Expected monthly notional turnover", "select",       _TURNOVER_OPTS, _VR_OPT,   9,  False),
    ("financial_profile",     "asset_classes_traded",          "Asset classes traded",               "multi_select", _ASSET_CLASSES, _VR_MULTI, 10, True),
    ("services_requested",    "preferred_execution_venues",    "Preferred execution venues",         "textarea",     _EMPTY_OPTS,    _VR_REQ,   11, True),
    ("services_requested",    "existing_pb_relationships",     "Existing prime broker relationships","textarea",     _EMPTY_OPTS,    _VR_REQ,   12, True),
]

_ALL_PRODUCT_DATA = [
    (_GCF_QID, _GCF_PID, "GCF", "Global Custody Facility",
     "Institutional global custody and settlement services",  _GCF_QUESTIONS),
    (_ECM_QID, _ECM_PID, "ECM", "Equity Capital Markets",
     "Equity capital markets access for institutional clients", _ECM_QUESTIONS),
    (_DCM_QID, _DCM_PID, "DCM", "Debt Capital Markets",
     "Debt capital markets services for institutional issuers", _DCM_QUESTIONS),
    (_TFE_QID, _TFE_PID, "TFE", "Trade Finance Exchange",
     "Trade finance exchange platform for institutional participants", _TFE_QUESTIONS),
]


def _esc(s: str) -> str:
    return s.replace("'", "''")


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Widen question-type constraint to allow 'textarea' and 'email'
    op.drop_constraint("oqn_type_chk", "onboarding_questions", type_="check")
    op.create_check_constraint(
        "oqn_type_chk",
        "onboarding_questions",
        "question_type IN ('text','number','select','multi_select','date','boolean','currency','textarea','email')",
    )

    # 2. Deactivate pre-existing institutional products (not our 4 new codes)
    codes_list = ", ".join(f"'{c}'" for c in _NEW_PRODUCT_CODES)
    conn.execute(sa.text(
        f"UPDATE products SET is_active = FALSE "
        f"WHERE product_type = 'institutional' AND product_code NOT IN ({codes_list})"
    ))

    # 3. Insert questionnaires
    for qid, pid, code, name, desc, _ in _ALL_PRODUCT_DATA:
        q_name = f"{name} Questionnaire"
        q_desc = f"Onboarding questionnaire for {name}"
        conn.execute(sa.text(
            f"INSERT INTO onboarding_questionnaires "
            f"  (id, name, description, version, is_active, sections, metadata) "
            f"VALUES "
            f"  ('{qid}', '{_esc(q_name)}', '{_esc(q_desc)}', 1, TRUE, '[]'::jsonb, '{{}}'::jsonb) "
            f"ON CONFLICT (id) DO NOTHING"
        ))

    # 4. Insert products (active, institutional)
    for qid, pid, code, name, desc, _ in _ALL_PRODUCT_DATA:
        conn.execute(sa.text(
            f"INSERT INTO products "
            f"  (id, product_code, name, description, is_active, product_type, "
            f"   required_documents, suitability_criteria, step_sequence, metadata) "
            f"VALUES "
            f"  ('{pid}', '{code}', '{_esc(name)}', '{_esc(desc)}', TRUE, 'institutional', "
            f"   '{{}}'::text[], '{{}}'::jsonb, '[]'::jsonb, '{{}}'::jsonb) "
            f"ON CONFLICT ON CONSTRAINT products_code_uq "
            f"DO UPDATE SET is_active = TRUE, product_type = 'institutional'"
        ))

    # 5. Insert questions per product
    for qid, pid, code, name, desc, questions in _ALL_PRODUCT_DATA:
        for (section, field_key, question_text, qtype, options, validation, order_idx, is_required) in questions:
            is_req_sql = "TRUE" if is_required else "FALSE"
            conn.execute(sa.text(
                f"INSERT INTO onboarding_questions "
                f"  (questionnaire_id, section, question_key, question_text, "
                f"   question_type, options, validation_rules, show_if, "
                f"   order_index, is_required, product_id, metadata) "
                f"VALUES ("
                f"  '{qid}', "
                f"  '{_esc(section)}', "
                f"  '{_esc(field_key)}', "
                f"  '{_esc(question_text)}', "
                f"  '{_esc(qtype)}', "
                f"  '{_esc(options)}'::jsonb, "
                f"  '{_esc(validation)}'::jsonb, "
                f"  NULL, "
                f"  {order_idx}, "
                f"  {is_req_sql}, "
                f"  '{pid}', "
                f"  '{{}}'::jsonb"
                f") ON CONFLICT ON CONSTRAINT oqn_key_uq DO NOTHING"
            ))


def downgrade() -> None:
    conn = op.get_bind()

    # Remove questions for the 4 seeded questionnaires
    for qid in (_GCF_QID, _ECM_QID, _DCM_QID, _TFE_QID):
        conn.execute(sa.text(
            f"DELETE FROM onboarding_questions WHERE questionnaire_id = '{qid}'"
        ))

    # Remove questionnaires
    for qid in (_GCF_QID, _ECM_QID, _DCM_QID, _TFE_QID):
        conn.execute(sa.text(
            f"DELETE FROM onboarding_questionnaires WHERE id = '{qid}'"
        ))

    # Remove products
    for pid in (_GCF_PID, _ECM_PID, _DCM_PID, _TFE_PID):
        conn.execute(sa.text(
            f"DELETE FROM products WHERE id = '{pid}'"
        ))

    # Restore original question-type constraint
    op.drop_constraint("oqn_type_chk", "onboarding_questions", type_="check")
    op.create_check_constraint(
        "oqn_type_chk",
        "onboarding_questions",
        "question_type IN ('text','number','select','multi_select','date','boolean','currency')",
    )
