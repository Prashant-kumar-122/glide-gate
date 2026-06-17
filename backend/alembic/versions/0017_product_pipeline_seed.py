"""Seed domain_product_pipelines + add retail products with suitability_criteria (Phase 4)

Revision ID: 0017_product_pipeline_seed
Revises: 0016_decision_log
Create Date: 2026-06-15

Phase 4 activates Product.step_sequence / suitability_criteria as the live
source of truth.  This migration:

  1. Inserts retail products (cash_account, retirement_account) into
     domain_products for the wealth_management domain.
  2. Populates domain_product_pipelines with step sequences for all 6 wealth
     products (2 retail + 4 institutional).
  3. Updates suitability_criteria on all domain_products rows so that
     SuitabilityAssessor.assess_with_criteria() can read thresholds from DB.
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0017_product_pipeline_seed"
down_revision = "0016_decision_log"
branch_labels = None
depends_on = None

_WEALTH_CODE = "wealth_management"

# ── Shared scoring maps (same for all wealth products) ────────────────────────
# Stored inline per product so each product row is self-contained; a future
# admin portal can allow domain-level defaults to override these.

_SHARED_MAPS = {
    "risk_capacity_map": {
        "conservative": 1,
        "moderately_conservative": 2,
        "balanced": 3,
        "moderately_aggressive": 4,
        "aggressive": 5,
    },
    "objective_to_risk": {
        "capital preservation": "conservative",
        "income": "moderately_conservative",
        "growth and income": "balanced",
        "growth": "moderately_aggressive",
        "speculation": "aggressive",
        "aggressive growth": "aggressive",
    },
    "objective_to_horizon": {
        "capital preservation": "short_term",
        "income": "short_term",
        "growth and income": "medium_term",
        "growth": "long_term",
        "speculation": "long_term",
        "aggressive growth": "long_term",
    },
    "income_range_to_float": {
        "under $25,000": 20_000.0,
        "$25,000 - $50,000": 37_500.0,
        "$50,000 - $100,000": 75_000.0,
        "$100,000 - $200,000": 150_000.0,
        "over $200,000": 250_000.0,
    },
}

_STD_WEIGHTS = {"risk": 0.40, "income": 0.30, "age": 0.20, "horizon": 0.10}


def _criteria(
    *,
    min_risk_level: int = 1,
    min_age: int = 18,
    min_income: float = 0.0,
    ideal_horizons: list[str],
    is_retirement_account: bool = False,
) -> str:
    return json.dumps({
        "min_risk_level": min_risk_level,
        "min_age": min_age,
        "min_income": min_income,
        "ideal_horizons": ideal_horizons,
        "is_retirement_account": is_retirement_account,
        "scoring_weights": _STD_WEIGHTS,
        **_SHARED_MAPS,
    })


# ── Retail products to INSERT ─────────────────────────────────────────────────

_RETAIL_PRODUCTS = [
    {
        "product_code": "cash_account",
        "display_name": "Cash Management Account",
        "product_type": "retail",
        "suitability_criteria": _criteria(
            min_risk_level=1,
            min_age=18,
            min_income=0.0,
            ideal_horizons=["short_term", "medium_term", "long_term"],
        ),
    },
    {
        "product_code": "retirement_account",
        "display_name": "Retirement Savings Account",
        "product_type": "retail",
        "suitability_criteria": _criteria(
            min_risk_level=1,
            min_age=18,
            min_income=0.0,
            ideal_horizons=["long_term"],
            is_retirement_account=True,
        ),
    },
]

# ── Suitability criteria for existing institutional products ──────────────────

_INSTITUTIONAL_CRITERIA = {
    "gcf": _criteria(min_risk_level=3, min_age=21, min_income=100_000.0, ideal_horizons=["long_term"]),
    "ecm": _criteria(min_risk_level=4, min_age=21, min_income=100_000.0, ideal_horizons=["long_term"]),
    "dcm": _criteria(min_risk_level=3, min_age=21, min_income=100_000.0, ideal_horizons=["medium_term", "long_term"]),
    "tfe": _criteria(min_risk_level=3, min_age=21, min_income=75_000.0,  ideal_horizons=["short_term", "medium_term"]),
}

# ── Pipeline step definitions ─────────────────────────────────────────────────
# step_config carries simulated latency bounds and an optional description used
# by the frontend step-detail panel.

_PIPELINES: dict[str, list[dict]] = {
    "cash_account": [
        {"step_id": "suitability_assessment",  "step_label": "Suitability Assessment",    "step_order": 0, "step_config": {"min_ms": 200, "max_ms": 600}},
        {"step_id": "account_funding_setup",   "step_label": "Account Funding Setup",     "step_order": 1, "step_config": {"min_ms": 200, "max_ms": 500}},
        {"step_id": "account_provisioning",    "step_label": "Account Provisioning",      "step_order": 2, "step_config": {"min_ms": 300, "max_ms": 700}},
        {"step_id": "welcome_kit",             "step_label": "Welcome Kit",               "step_order": 3, "step_config": {"min_ms": 100, "max_ms": 250}},
    ],
    "retirement_account": [
        {"step_id": "suitability_assessment",  "step_label": "Suitability Assessment",    "step_order": 0, "step_config": {"min_ms": 200, "max_ms": 600}},
        {"step_id": "contribution_limits_check","step_label": "Contribution Limits Check","step_order": 1, "step_config": {"min_ms": 100, "max_ms": 300}},
        {"step_id": "beneficiary_designation", "step_label": "Beneficiary Designation",   "step_order": 2, "step_config": {"min_ms": 150, "max_ms": 400}},
        {"step_id": "investment_selection",    "step_label": "Investment Selection",      "step_order": 3, "step_config": {"min_ms": 400, "max_ms": 900}},
        {"step_id": "account_provisioning",    "step_label": "Account Provisioning",      "step_order": 4, "step_config": {"min_ms": 300, "max_ms": 700}},
        {"step_id": "welcome_kit",             "step_label": "Welcome Kit",               "step_order": 5, "step_config": {"min_ms": 100, "max_ms": 250}},
    ],
    # Institutional products share a simpler default pipeline
    "gcf": [
        {"step_id": "suitability_assessment",  "step_label": "Suitability Assessment",    "step_order": 0, "step_config": {"min_ms": 200, "max_ms": 600}},
        {"step_id": "account_provisioning",    "step_label": "Account Provisioning",      "step_order": 1, "step_config": {"min_ms": 300, "max_ms": 700}},
        {"step_id": "welcome_kit",             "step_label": "Welcome Kit",               "step_order": 2, "step_config": {"min_ms": 100, "max_ms": 250}},
    ],
    "ecm": [
        {"step_id": "suitability_assessment",  "step_label": "Suitability Assessment",    "step_order": 0, "step_config": {"min_ms": 200, "max_ms": 600}},
        {"step_id": "account_provisioning",    "step_label": "Account Provisioning",      "step_order": 1, "step_config": {"min_ms": 300, "max_ms": 700}},
        {"step_id": "welcome_kit",             "step_label": "Welcome Kit",               "step_order": 2, "step_config": {"min_ms": 100, "max_ms": 250}},
    ],
    "dcm": [
        {"step_id": "suitability_assessment",  "step_label": "Suitability Assessment",    "step_order": 0, "step_config": {"min_ms": 200, "max_ms": 600}},
        {"step_id": "account_provisioning",    "step_label": "Account Provisioning",      "step_order": 1, "step_config": {"min_ms": 300, "max_ms": 700}},
        {"step_id": "welcome_kit",             "step_label": "Welcome Kit",               "step_order": 2, "step_config": {"min_ms": 100, "max_ms": 250}},
    ],
    "tfe": [
        {"step_id": "suitability_assessment",  "step_label": "Suitability Assessment",    "step_order": 0, "step_config": {"min_ms": 200, "max_ms": 600}},
        {"step_id": "account_provisioning",    "step_label": "Account Provisioning",      "step_order": 1, "step_config": {"min_ms": 300, "max_ms": 700}},
        {"step_id": "welcome_kit",             "step_label": "Welcome Kit",               "step_order": 2, "step_config": {"min_ms": 100, "max_ms": 250}},
    ],
}


def upgrade() -> None:
    conn = op.get_bind()

    domain_id = conn.execute(sa.text(
        "SELECT id FROM domains WHERE domain_code = :code"
    ), {"code": _WEALTH_CODE}).scalar()

    if domain_id is None:
        raise RuntimeError(
            f"Domain {_WEALTH_CODE!r} not found — run 0014_wealth_domain_seed first"
        )

    # ── INSERT retail products ────────────────────────────────────────────────
    for p in _RETAIL_PRODUCTS:
        conn.execute(sa.text(
            "INSERT INTO domain_products "
            "(domain_id, product_code, display_name, product_type, is_active, suitability_criteria) "
            "VALUES (:domain_id, :product_code, :display_name, :product_type, true, "
            "        CAST(:suitability_criteria AS jsonb)) "
            "ON CONFLICT (domain_id, product_code) DO UPDATE "
            "SET suitability_criteria = CAST(EXCLUDED.suitability_criteria AS jsonb)"
        ), {
            "domain_id": domain_id,
            "product_code": p["product_code"],
            "display_name": p["display_name"],
            "product_type": p["product_type"],
            "suitability_criteria": p["suitability_criteria"],
        })

    # ── UPDATE institutional products suitability_criteria ───────────────────
    for product_code, criteria_json in _INSTITUTIONAL_CRITERIA.items():
        conn.execute(sa.text(
            "UPDATE domain_products "
            "SET suitability_criteria = CAST(:criteria AS jsonb) "
            "WHERE domain_id = :domain_id AND product_code = :product_code"
        ), {"domain_id": domain_id, "criteria": criteria_json, "product_code": product_code})

    # ── INSERT pipeline steps ─────────────────────────────────────────────────
    for product_code, steps in _PIPELINES.items():
        for step in steps:
            conn.execute(sa.text(
                "INSERT INTO domain_product_pipelines "
                "(domain_id, product_code, step_id, step_label, step_order, is_parallel, step_config) "
                "VALUES (:domain_id, :product_code, :step_id, :step_label, :step_order, false, "
                "        CAST(:step_config AS jsonb)) "
                "ON CONFLICT (domain_id, product_code, step_id) DO UPDATE "
                "SET step_label  = EXCLUDED.step_label, "
                "    step_order  = EXCLUDED.step_order, "
                "    step_config = EXCLUDED.step_config"
            ), {
                "domain_id": domain_id,
                "product_code": product_code,
                "step_id": step["step_id"],
                "step_label": step["step_label"],
                "step_order": step["step_order"],
                "step_config": json.dumps(step["step_config"]),
            })


def downgrade() -> None:
    conn = op.get_bind()

    domain_id = conn.execute(sa.text(
        "SELECT id FROM domains WHERE domain_code = :code"
    ), {"code": _WEALTH_CODE}).scalar()

    if domain_id is None:
        return

    conn.execute(sa.text(
        "DELETE FROM domain_product_pipelines WHERE domain_id = :domain_id"
    ), {"domain_id": domain_id})

    for product_code in ("cash_account", "retirement_account"):
        conn.execute(sa.text(
            "DELETE FROM domain_products "
            "WHERE domain_id = :domain_id AND product_code = :product_code"
        ), {"domain_id": domain_id, "product_code": product_code})

    for product_code in _INSTITUTIONAL_CRITERIA:
        conn.execute(sa.text(
            "UPDATE domain_products SET suitability_criteria = '{}'::jsonb "
            "WHERE domain_id = :domain_id AND product_code = :product_code"
        ), {"domain_id": domain_id, "product_code": product_code})
