from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class RiskScore(BaseModel):
    identity_score: float   # 0–100, higher = more risk
    aml_score: float        # 0–100
    profile_score: float    # 0–100
    composite_score: float  # identity×0.4 + aml×0.4 + profile×0.2
    risk_band: Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]


class RiskScorer:
    """
    Weighted risk scorer (BRD Section 6.1, FR-04).

    composite = identity × 0.4 + AML × 0.4 + profile × 0.2
    Band thresholds: LOW (0–30), MEDIUM (31–60), HIGH (61–80), VERY_HIGH (81–100)
    """

    IDENTITY_WEIGHT = 0.4
    AML_WEIGHT = 0.4
    PROFILE_WEIGHT = 0.2

    HIGH_RISK_NATIONALITIES = {
        "iran", "north korea", "syria", "cuba", "venezuela",
        "myanmar", "belarus", "russia",
    }

    def compute(
        self,
        client_data: dict[str, Any],
        verification_result: dict[str, Any],
    ) -> RiskScore:
        identity = self._identity_score(verification_result)
        aml = self._aml_score(verification_result)
        profile = self._profile_score(client_data)
        composite = round(
            min(
                identity * self.IDENTITY_WEIGHT
                + aml * self.AML_WEIGHT
                + profile * self.PROFILE_WEIGHT,
                100.0,
            ),
            2,
        )
        return RiskScore(
            identity_score=round(identity, 2),
            aml_score=round(aml, 2),
            profile_score=round(profile, 2),
            composite_score=composite,
            risk_band=self._band(composite),
        )

    def _identity_score(self, v: dict[str, Any]) -> float:
        if v.get("sanctions_match"):
            return 100.0
        if not v.get("document_authentic", True):
            return 90.0
        score = 0.0
        # Lower name-match confidence → higher risk (0–50 pts)
        confidence = float(v.get("name_match_confidence", 0.95))
        score += (1.0 - confidence) * 50.0
        if not v.get("document_valid", True):
            score += 25.0
        return min(score, 100.0)

    def _aml_score(self, v: dict[str, Any]) -> float:
        if v.get("sanctions_match"):
            return 100.0
        score = 0.0
        if v.get("pep_match"):
            score += 70.0
        aml_level = v.get("aml_risk_level", "LOW")
        if aml_level == "HIGH":
            score = max(score, 60.0)
        elif aml_level == "MEDIUM":
            score = max(score, 30.0)
        else:
            score = max(score, 10.0)
        score += len(v.get("aml_risk_factors", [])) * 5.0
        return min(score, 100.0)

    def _profile_score(self, d: dict[str, Any]) -> float:
        score = 0.0
        nationality = (d.get("nationality") or "").lower()
        if nationality in self.HIGH_RISK_NATIONALITIES:
            score += 40.0
        if d.get("source_of_funds") == "Other":
            score += 20.0
        try:
            net_worth = float(d.get("net_worth") or 0)
        except (TypeError, ValueError):
            net_worth = 0.0
        try:
            annual_income = float(d.get("annual_income") or 0)
        except (TypeError, ValueError):
            annual_income = 0.0
        if net_worth > 5_000_000:
            score += 15.0
        # Wealth-income mismatch (net worth > 10× annual income)
        if annual_income > 0 and net_worth > annual_income * 10:
            score += 10.0
        # High earner with no source-of-wealth detail
        if annual_income > 250_000 and not d.get("source_of_wealth_detail"):
            score += 10.0
        return min(score, 100.0)

    @staticmethod
    def _band(score: float) -> Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]:
        if score <= 30:
            return "LOW"
        if score <= 60:
            return "MEDIUM"
        if score <= 80:
            return "HIGH"
        return "VERY_HIGH"
