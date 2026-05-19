from __future__ import annotations

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


class SuitabilityAssessor:
    """
    Evaluates whether a client profile is suitable for a specific product.

    Scoring weights:
    - Risk alignment:   40 %
    - Income adequacy:  30 %
    - Age appropriateness: 20 %
    - Investment horizon: 10 %
    """

    def assess(self, product_code: str, client_data: dict[str, Any]) -> SuitabilityOutcome:
        reasons: list[str] = []
        conditions: list[str] = []
        risk_warnings: list[str] = []
        score_components: list[float] = []

        # ── Risk alignment ────────────────────────────────────────────────────
        risk_tolerance = (client_data.get("risk_tolerance") or "balanced").lower()
        client_risk = _RISK_CAPACITY_MAP.get(risk_tolerance, 3)
        min_risk = _PRODUCT_MIN_RISK.get(product_code, 1)

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
        score_components.append(risk_score * 0.40)

        # ── Income adequacy ───────────────────────────────────────────────────
        try:
            annual_income = float(client_data.get("annual_income") or 0.0)
        except (TypeError, ValueError):
            annual_income = 0.0
        min_income = _PRODUCT_MIN_INCOME.get(product_code, 0.0)

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
        score_components.append(income_score * 0.30)

        # ── Age appropriateness ───────────────────────────────────────────────
        age = int(client_data.get("age") or 0)
        min_age = _PRODUCT_MIN_AGE.get(product_code, 18)

        if age >= min_age:
            if product_code == "retirement_account" and age > 60:
                age_score = 1.0
                reasons.append("Age is well-suited for retirement planning.")
            elif product_code == "retirement_account" and age > 45:
                age_score = 0.9
                reasons.append("Age is suitable for retirement account planning.")
            else:
                age_score = 0.8
                reasons.append("Client meets the minimum age requirement.")
        else:
            age_score = 0.0
            risk_warnings.append(f"Client age ({age}) is below the minimum age ({min_age}).")
        score_components.append(age_score * 0.20)

        # ── Investment horizon ────────────────────────────────────────────────
        horizon = (client_data.get("investment_horizon") or "medium_term").lower()
        if product_code == "cash_account":
            ideal_horizons = {"short_term", "medium_term", "long_term"}
        else:  # retirement_account
            ideal_horizons = {"long_term"}

        if any(h in horizon for h in ideal_horizons):
            horizon_score = 1.0
            reasons.append(f"Investment horizon '{horizon}' is well-matched to {product_code}.")
        else:
            horizon_score = 0.4
            risk_warnings.append(
                f"Investment horizon '{horizon}' may not be optimal for {product_code}."
            )
        score_components.append(horizon_score * 0.10)

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
