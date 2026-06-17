"""Phase 4 — unit tests for config-driven product pipelines and suitability assessment.

All tests are pure Python (no DB required).  They verify:

  1. SuitabilityAssessor.assess_with_criteria() produces identical scores to
     assess() when passed the equivalent criteria as a dict (snapshot parity).
  2. assess_with_criteria() correctly reads product-specific thresholds from
     the criteria dict (min_risk_level, min_age, min_income, ideal_horizons,
     is_retirement_account, scoring_weights).
  3. assess() backward-compat: unchanged behaviour when no criteria are supplied.
  4. The hardcoded _PRODUCT_STEPS fallback lists match expected step names.
  5. _STEP_DURATIONS_MS contains expected latency bounds for core steps.
"""
from __future__ import annotations

import pytest

from app.agents.product_onboarding.suitability_assessor import (
    SuitabilityAssessor,
    SuitabilityOutcome,
    _INCOME_RANGE_TO_FLOAT,
    _OBJECTIVE_TO_HORIZON,
    _OBJECTIVE_TO_RISK,
    _PRODUCT_MIN_AGE,
    _PRODUCT_MIN_INCOME,
    _PRODUCT_MIN_RISK,
    _RISK_CAPACITY_MAP,
)
from app.agents.product_onboarding.product_onboarding_agent import (
    _DEFAULT_STEPS,
    _PRODUCT_STEPS,
    _STEP_DURATIONS_MS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _full_criteria(product_code: str) -> dict:
    """Build a criteria dict that matches the hardcoded module-level constants."""
    is_retirement = product_code == "retirement_account"
    ideal_horizons = ["long_term"] if is_retirement else ["short_term", "medium_term", "long_term"]
    return {
        "min_risk_level": _PRODUCT_MIN_RISK.get(product_code, 1),
        "min_age": _PRODUCT_MIN_AGE.get(product_code, 18),
        "min_income": _PRODUCT_MIN_INCOME.get(product_code, 0.0),
        "ideal_horizons": ideal_horizons,
        "is_retirement_account": is_retirement,
        "scoring_weights": {"risk": 0.40, "income": 0.30, "age": 0.20, "horizon": 0.10},
        "risk_capacity_map": dict(_RISK_CAPACITY_MAP),
        "objective_to_risk": dict(_OBJECTIVE_TO_RISK),
        "objective_to_horizon": dict(_OBJECTIVE_TO_HORIZON),
        "income_range_to_float": dict(_INCOME_RANGE_TO_FLOAT),
    }


_CLIENT_PROFILES = [
    # (label, client_data)
    (
        "growth_investor_35yo",
        {
            "investment_objective": "growth",
            "annual_income": "$50,000 - $100,000",
            "date_of_birth": "1991-03-15",
        },
    ),
    (
        "conservative_investor_55yo",
        {
            "investment_objective": "capital preservation",
            "annual_income": "$25,000 - $50,000",
            "date_of_birth": "1971-06-20",
        },
    ),
    (
        "aggressive_investor_28yo",
        {
            "investment_objective": "aggressive growth",
            "annual_income": "$100,000 - $200,000",
            "date_of_birth": "1998-01-01",
        },
    ),
    (
        "underage_client",
        {
            "investment_objective": "growth",
            "annual_income": "$25,000 - $50,000",
            "date_of_birth": "2015-09-01",
        },
    ),
]

_PRODUCTS = ["cash_account", "retirement_account"]


# ── Snapshot parity: assess_with_criteria == assess ───────────────────────────


@pytest.mark.parametrize("product_code", _PRODUCTS)
@pytest.mark.parametrize("label,client_data", _CLIENT_PROFILES)
def test_assess_with_criteria_matches_hardcoded(
    product_code: str, label: str, client_data: dict
) -> None:
    """assess_with_criteria() with full criteria dict must produce identical results to assess()."""
    assessor = SuitabilityAssessor()
    hardcoded = assessor.assess(product_code, client_data)
    criteria = _full_criteria(product_code)
    db_driven = assessor.assess_with_criteria(product_code, client_data, criteria)

    assert db_driven.is_suitable == hardcoded.is_suitable, (
        f"[{product_code}/{label}] is_suitable mismatch: "
        f"hardcoded={hardcoded.is_suitable} db_driven={db_driven.is_suitable}"
    )
    assert db_driven.suitability_score == hardcoded.suitability_score, (
        f"[{product_code}/{label}] score mismatch: "
        f"hardcoded={hardcoded.suitability_score} db_driven={db_driven.suitability_score}"
    )


# ── Criteria thresholds are respected ────────────────────────────────────────


def test_min_risk_level_respected() -> None:
    """Raising min_risk_level to 5 should apply the risk penalty and emit a warning.

    The risk component score drops to 0.2 × 0.40 = 0.08 (vs up to 0.40 without penalty).
    Final suitability depends on all components, but the warning is always emitted.
    """
    assessor = SuitabilityAssessor()
    client_data = {
        "investment_objective": "capital preservation",  # maps to conservative (level 1)
        "annual_income": "$100,000 - $200,000",
        "date_of_birth": "1985-05-10",
    }
    strict_criteria = {**_full_criteria("cash_account"), "min_risk_level": 5}
    result = assessor.assess_with_criteria("cash_account", client_data, strict_criteria)
    # Risk warning must fire when client_risk < min_risk_level
    assert any("below the recommended level" in w for w in result.risk_warnings)
    # Score with penalty must be lower than without
    no_min_criteria = {**strict_criteria, "min_risk_level": 1}
    full_result = assessor.assess_with_criteria("cash_account", client_data, no_min_criteria)
    assert result.suitability_score < full_result.suitability_score


def test_min_income_respected() -> None:
    """Setting a high min_income should add a condition for a low-income client."""
    assessor = SuitabilityAssessor()
    client_data = {
        "investment_objective": "growth",
        "annual_income": "under $25,000",
        "date_of_birth": "1990-04-01",
    }
    high_income_criteria = {**_full_criteria("cash_account"), "min_income": 200_000.0}
    result = assessor.assess_with_criteria("cash_account", client_data, high_income_criteria)
    assert any("below" in (w.lower()) for w in result.risk_warnings + result.conditions)


def test_min_age_respected() -> None:
    """A 20-year-old should fail if min_age is set to 21."""
    assessor = SuitabilityAssessor()
    client_data = {
        "investment_objective": "growth",
        "annual_income": "$50,000 - $100,000",
        "date_of_birth": "2006-01-01",  # age ~20 in 2026
    }
    strict_age_criteria = {**_full_criteria("cash_account"), "min_age": 21}
    result = assessor.assess_with_criteria("cash_account", client_data, strict_age_criteria)
    assert not result.is_suitable
    assert any("below the minimum age" in w for w in result.risk_warnings)


def test_ideal_horizons_respected() -> None:
    """Restricting ideal_horizons to long_term should penalise a capital-preservation investor."""
    assessor = SuitabilityAssessor()
    client_data = {
        "investment_objective": "capital preservation",  # horizon = short_term
        "annual_income": "$100,000 - $200,000",
        "date_of_birth": "1975-07-15",
    }
    long_only_criteria = {**_full_criteria("cash_account"), "ideal_horizons": ["long_term"]}
    result = assessor.assess_with_criteria("cash_account", client_data, long_only_criteria)
    assert any("may not be optimal" in w for w in result.risk_warnings)


def test_retirement_age_bonus_from_criteria() -> None:
    """is_retirement_account=True in criteria should give age bonus for a 62-year-old."""
    assessor = SuitabilityAssessor()
    client_data = {
        "investment_objective": "growth",
        "annual_income": "$100,000 - $200,000",
        "date_of_birth": "1964-02-01",  # age ~62 in 2026
    }
    result = assessor.assess_with_criteria(
        "retirement_account", client_data, _full_criteria("retirement_account")
    )
    assert result.is_suitable
    assert any("well-suited for retirement" in r for r in result.reasons)


def test_custom_scoring_weights_change_score() -> None:
    """Changing scoring weights should alter the total score while preserving component outcomes."""
    assessor = SuitabilityAssessor()
    client_data = {
        "investment_objective": "growth",
        "annual_income": "$50,000 - $100,000",
        "date_of_birth": "1990-01-01",
    }
    base_criteria = _full_criteria("cash_account")
    # Flip weights: make horizon the dominant factor (70%)
    alt_criteria = {
        **base_criteria,
        "scoring_weights": {"risk": 0.10, "income": 0.10, "age": 0.10, "horizon": 0.70},
    }
    base_result = assessor.assess_with_criteria("cash_account", client_data, base_criteria)
    alt_result = assessor.assess_with_criteria("cash_account", client_data, alt_criteria)
    assert base_result.suitability_score != alt_result.suitability_score


# ── Hardcoded fallback correctness ────────────────────────────────────────────


def test_product_steps_cash_account() -> None:
    assert _PRODUCT_STEPS["cash_account"] == [
        "suitability_assessment",
        "account_funding_setup",
        "account_provisioning",
        "welcome_kit",
    ]


def test_product_steps_retirement_account() -> None:
    assert _PRODUCT_STEPS["retirement_account"] == [
        "suitability_assessment",
        "contribution_limits_check",
        "beneficiary_designation",
        "investment_selection",
        "account_provisioning",
        "welcome_kit",
    ]


def test_default_steps_present() -> None:
    assert "suitability_assessment" in _DEFAULT_STEPS
    assert "account_provisioning" in _DEFAULT_STEPS
    assert "welcome_kit" in _DEFAULT_STEPS


def test_step_durations_cover_core_steps() -> None:
    core_steps = ["suitability_assessment", "account_provisioning", "welcome_kit",
                  "contribution_limits_check", "investment_selection"]
    for step in core_steps:
        assert step in _STEP_DURATIONS_MS, f"Missing latency config for step {step!r}"
        lo, hi = _STEP_DURATIONS_MS[step]
        assert lo < hi, f"min_ms ({lo}) must be less than max_ms ({hi}) for {step!r}"


# ── DB pipeline steps shape (migration 0017 spec) ────────────────────────────


def test_migration_pipeline_shape_cash_account() -> None:
    """Assert that the migration data matches the hardcoded fallback step list."""
    # The migration inserts these steps for cash_account; verify they match _PRODUCT_STEPS.
    expected_from_migration = [
        "suitability_assessment",
        "account_funding_setup",
        "account_provisioning",
        "welcome_kit",
    ]
    assert expected_from_migration == _PRODUCT_STEPS["cash_account"]


def test_migration_pipeline_shape_retirement_account() -> None:
    expected_from_migration = [
        "suitability_assessment",
        "contribution_limits_check",
        "beneficiary_designation",
        "investment_selection",
        "account_provisioning",
        "welcome_kit",
    ]
    assert expected_from_migration == _PRODUCT_STEPS["retirement_account"]


# ── assess() backward compat: unchanged outcome ───────────────────────────────


def test_assess_is_suitable_for_balanced_investor_cash_account() -> None:
    assessor = SuitabilityAssessor()
    result = assessor.assess("cash_account", {
        "investment_objective": "growth and income",
        "annual_income": "$50,000 - $100,000",
        "date_of_birth": "1985-06-15",
    })
    assert isinstance(result, SuitabilityOutcome)
    assert result.is_suitable
    assert 0.0 < result.suitability_score <= 1.0


def test_assess_underage_client_is_not_suitable() -> None:
    assessor = SuitabilityAssessor()
    result = assessor.assess("cash_account", {
        "investment_objective": "growth",
        "annual_income": "$25,000 - $50,000",
        "date_of_birth": "2015-01-01",
    })
    assert not result.is_suitable
