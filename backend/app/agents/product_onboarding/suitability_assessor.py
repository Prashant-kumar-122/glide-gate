from __future__ import annotations

from datetime import date as _date
from typing import Any

from pydantic import BaseModel


class SuitabilityOutcome(BaseModel):
    product_code: str
    is_suitable: bool
    suitability_score: float  # 0.0 – 1.0
    reasons: list[str]
    conditions: list[str]  # requirements that must be met before account opening
    risk_warnings: list[str]


_RISK_CAPACITY_MAP: dict[str, int] = {
    "conservative": 1,
    "moderately_conservative": 2,
    "balanced": 3,
    "moderately_aggressive": 4,
    "aggressive": 5,
}

_PRODUCT_MIN_RISK: dict[str, int] = {
    "cash_account": 1,
    "retirement_account": 1,
}

_PRODUCT_MIN_AGE: dict[str, int] = {
    "cash_account": 18,
    "retirement_account": 18,
}

_PRODUCT_MIN_INCOME: dict[str, float] = {
    "cash_account": 0.0,
    "retirement_account": 0.0,
}

# Maps the investment_objective form field to internal risk tolerance strings.
_OBJECTIVE_TO_RISK: dict[str, str] = {
    "capital preservation": "conservative",
    "income": "moderately_conservative",
    "growth and income": "balanced",
    "growth": "moderately_aggressive",
    "speculation": "aggressive",
    "aggressive growth": "aggressive",
}

# Maps investment_objective to an investment horizon category.
_OBJECTIVE_TO_HORIZON: dict[str, str] = {
    "capital preservation": "short_term",
    "income": "short_term",
    "growth and income": "medium_term",
    "growth": "long_term",
    "speculation": "long_term",
    "aggressive growth": "long_term",
}

# Maps the annual_income range string (from the form) to a representative float.
_INCOME_RANGE_TO_FLOAT: dict[str, float] = {
    "under $25,000": 20_000.0,
    "$25,000 - $50,000": 37_500.0,
    "$50,000 - $100,000": 75_000.0,
    "$100,000 - $200,000": 150_000.0,
    "over $200,000": 250_000.0,
}


class SuitabilityAssessor:
    """
    Evaluates whether a client profile is suitable for a specific product.

    Scoring weights:
    - Risk alignment:   40 %
    - Income adequacy:  30 %
    - Age appropriateness: 20 %
    - Investment horizon: 10 %

    Phase 4: assess_with_criteria() reads thresholds + maps from the
    domain_products.suitability_criteria JSONB column, falling back to the
    module-level constants for any key not present in the criteria dict.
    assess() retains hardcoded fallbacks for backward compatibility.
    """

    def assess_with_criteria(
        self, product_code: str, client_data: dict[str, Any], criteria: dict[str, Any]
    ) -> SuitabilityOutcome:
        """DB-driven assessment: thresholds and maps come from the criteria dict.

        The criteria dict is the suitability_criteria JSONB from domain_products.
        Any key absent in criteria falls back to the module-level constant so
        existing assessment behaviour is preserved for partial criteria dicts.
        """
        risk_capacity_map: dict[str, int] = criteria.get("risk_capacity_map", _RISK_CAPACITY_MAP)
        objective_to_risk: dict[str, str] = criteria.get("objective_to_risk", _OBJECTIVE_TO_RISK)
        objective_to_horizon: dict[str, str] = criteria.get("objective_to_horizon", _OBJECTIVE_TO_HORIZON)
        income_range_to_float: dict[str, float] = criteria.get("income_range_to_float", _INCOME_RANGE_TO_FLOAT)

        min_risk: int = int(criteria.get("min_risk_level", 1))
        min_age: int = int(criteria.get("min_age", 18))
        min_income: float = float(criteria.get("min_income", 0.0))
        ideal_horizons: set[str] = set(criteria.get("ideal_horizons", ["short_term", "medium_term", "long_term"]))
        is_retirement: bool = bool(criteria.get("is_retirement_account", False))
        weights: dict[str, float] = criteria.get(
            "scoring_weights", {"risk": 0.40, "income": 0.30, "age": 0.20, "horizon": 0.10}
        )

        return self._score(
            product_code=product_code,
            client_data=client_data,
            risk_capacity_map=risk_capacity_map,
            objective_to_risk=objective_to_risk,
            objective_to_horizon=objective_to_horizon,
            income_range_to_float=income_range_to_float,
            min_risk=min_risk,
            min_age=min_age,
            min_income=min_income,
            ideal_horizons=ideal_horizons,
            is_retirement=is_retirement,
            weights=weights,
        )

    def assess(self, product_code: str, client_data: dict[str, Any]) -> SuitabilityOutcome:
        """Hardcoded-constants assessment (backward compat; used when DB criteria unavailable)."""
        is_retirement = product_code == "retirement_account"
        ideal_horizons: set[str] = (
            {"long_term"} if is_retirement else {"short_term", "medium_term", "long_term"}
        )
        return self._score(
            product_code=product_code,
            client_data=client_data,
            risk_capacity_map=_RISK_CAPACITY_MAP,
            objective_to_risk=_OBJECTIVE_TO_RISK,
            objective_to_horizon=_OBJECTIVE_TO_HORIZON,
            income_range_to_float=_INCOME_RANGE_TO_FLOAT,
            min_risk=_PRODUCT_MIN_RISK.get(product_code, 1),
            min_age=_PRODUCT_MIN_AGE.get(product_code, 18),
            min_income=_PRODUCT_MIN_INCOME.get(product_code, 0.0),
            ideal_horizons=ideal_horizons,
            is_retirement=is_retirement,
            weights={"risk": 0.40, "income": 0.30, "age": 0.20, "horizon": 0.10},
        )

    # ── Core scoring (shared by assess and assess_with_criteria) ──────────────

    def _score(
        self,
        *,
        product_code: str,
        client_data: dict[str, Any],
        risk_capacity_map: dict[str, int],
        objective_to_risk: dict[str, str],
        objective_to_horizon: dict[str, str],
        income_range_to_float: dict[str, float],
        min_risk: int,
        min_age: int,
        min_income: float,
        ideal_horizons: set[str],
        is_retirement: bool,
        weights: dict[str, float],
    ) -> SuitabilityOutcome:
        reasons: list[str] = []
        conditions: list[str] = []
        risk_warnings: list[str] = []
        score_components: list[float] = []

        # ── Risk alignment ────────────────────────────────────────────────────
        objective = (client_data.get("investment_objective") or "growth").lower()
        risk_tolerance = objective_to_risk.get(objective, "balanced")
        client_risk = risk_capacity_map.get(risk_tolerance, 3)

        if client_risk >= min_risk:
            risk_score = min(1.0, (client_risk - min_risk + 1) / 3)
            reasons.append(f"Risk tolerance '{risk_tolerance}' aligns with product requirements.")
        else:
            risk_score = 0.2
            gap = min_risk - client_risk
            risk_warnings.append(
                f"Risk tolerance '{risk_tolerance}' is below the recommended level "
                f"for {product_code} (gap: {gap} level(s))."
            )
        score_components.append(risk_score * weights.get("risk", 0.40))

        # ── Income adequacy ───────────────────────────────────────────────────
        raw_income = str(client_data.get("annual_income") or "").strip().lower()
        annual_income = income_range_to_float.get(raw_income, 0.0)

        if min_income == 0.0 or annual_income >= min_income:
            income_score = 1.0
            reasons.append("Income level meets product eligibility criteria.")
        elif annual_income >= min_income * 0.7:
            income_score = 0.5
            conditions.append(
                f"Annual income (${annual_income:,.0f}) is below the typical minimum "
                f"(${min_income:,.0f}) — subject to additional review."
            )
        else:
            income_score = 0.1
            risk_warnings.append(
                f"Annual income (${annual_income:,.0f}) is significantly below the "
                f"minimum threshold (${min_income:,.0f}) for {product_code}."
            )
        score_components.append(income_score * weights.get("income", 0.30))

        # ── Age appropriateness ───────────────────────────────────────────────
        dob_str = client_data.get("date_of_birth")
        try:
            dob = _date.fromisoformat(str(dob_str)) if dob_str else None
            today = _date.today()
            age = (
                today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                if dob else 0
            )
        except ValueError:
            age = 0

        if age >= min_age:
            if is_retirement and age > 60:
                age_score = 1.0
                reasons.append("Age is well-suited for retirement planning.")
            elif is_retirement and age > 45:
                age_score = 0.9
                reasons.append("Age is suitable for retirement account planning.")
            else:
                age_score = 0.8
                reasons.append("Client meets the minimum age requirement.")
        else:
            age_score = 0.0
            risk_warnings.append(f"Client age ({age}) is below the minimum age ({min_age}).")
        score_components.append(age_score * weights.get("age", 0.20))

        # ── Investment horizon ────────────────────────────────────────────────
        horizon = objective_to_horizon.get(objective, "medium_term")

        if any(h in horizon for h in ideal_horizons):
            horizon_score = 1.0
            reasons.append(f"Investment horizon '{horizon}' is well-matched to {product_code}.")
        else:
            horizon_score = 0.4
            risk_warnings.append(
                f"Investment horizon '{horizon}' may not be optimal for {product_code}."
            )
        score_components.append(horizon_score * weights.get("horizon", 0.10))

        # ── Final decision ────────────────────────────────────────────────────
        suitability_score = round(sum(score_components), 4)
        is_suitable = suitability_score >= 0.5 and age >= min_age

        if not reasons:
            reasons.append("Assessment completed based on provided client profile.")

        return SuitabilityOutcome(
            product_code=product_code,
            is_suitable=is_suitable,
            suitability_score=suitability_score,
            reasons=reasons,
            conditions=conditions,
            risk_warnings=risk_warnings,
        )
