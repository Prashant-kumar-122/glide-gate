from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class CheckpointRule(BaseModel):
    rule_id: str
    description: str
    # Dimension filters (None = match any)
    product_type: str | None = None
    risk_level: str | None = None
    account_value_band: str | None = None
    jurisdiction: str | None = None
    action: Literal["ESCALATE", "ENHANCED_DD", "REQUIRE_DOCUMENTS"]
    required_documents: list[str] = []
    reason_template: str = ""


class CheckpointDecision(BaseModel):
    rule_id: str
    action: str
    triggered: bool
    reason: str
    required_documents: list[str] = []


class CheckpointResult(BaseModel):
    should_escalate: bool
    decisions: list[CheckpointDecision]
    required_documents: list[str]
    escalation_reasons: list[str]


_HIGH_RISK_NATIONALITIES = {
    "iran", "north korea", "syria", "cuba", "venezuela",
    "myanmar", "belarus", "russia",
}

_DEFAULT_RULES: list[CheckpointRule] = [
    CheckpointRule(
        rule_id="HIGH_RISK_SCORE",
        description="Escalate cases with HIGH or VERY_HIGH composite risk score",
        action="ESCALATE",
        reason_template="Composite risk score in {risk_band} band ({composite_score:.1f})",
    ),
    CheckpointRule(
        rule_id="SANCTIONS_MATCH",
        description="Escalate any sanctions list match",
        action="ESCALATE",
        reason_template="Sanctions list match detected during identity verification",
    ),
    CheckpointRule(
        rule_id="PEP_MATCH",
        description="Enhanced due diligence for politically exposed persons",
        action="ENHANCED_DD",
        required_documents=["source_of_wealth_declaration", "pep_attestation"],
        reason_template="Politically Exposed Person (PEP) identified",
    ),
    CheckpointRule(
        rule_id="LARGE_CASH_ACCOUNT",
        description="Enhanced DD for Cash Account initial deposit > $1M",
        product_type="cash_account",
        account_value_band="LARGE",
        action="ENHANCED_DD",
        required_documents=["source_of_wealth_declaration", "bank_statement"],
        reason_template="Initial Cash Account deposit exceeds $1,000,000",
    ),
    CheckpointRule(
        rule_id="HIGH_RISK_NATIONALITY",
        description="Additional documents required for high-risk nationality",
        action="REQUIRE_DOCUMENTS",
        required_documents=[
            "certified_id",
            "proof_of_address",
            "source_of_wealth_declaration",
        ],
        reason_template="High-risk nationality/jurisdiction detected: {jurisdiction}",
    ),
]


class CheckpointRuleEngine:
    """
    Evaluates configurable checkpoint rules across four dimensions:
    product_type, risk_level, account_value_band, jurisdiction (BRD FR-15).
    """

    def __init__(self, rules: list[CheckpointRule] | None = None) -> None:
        self._rules = rules if rules is not None else list(_DEFAULT_RULES)

    @property
    def rules(self) -> list[CheckpointRule]:
        return list(self._rules)

    def add_rule(self, rule: CheckpointRule) -> None:
        self._rules.append(rule)

    def remove_rule(self, rule_id: str) -> None:
        self._rules = [r for r in self._rules if r.rule_id != rule_id]

    def evaluate(
        self,
        risk_score: dict[str, Any],
        client_data: dict[str, Any],
        verification_result: dict[str, Any],
        selected_products: list[str],
    ) -> CheckpointResult:
        composite = float(risk_score.get("composite_score", 0))
        risk_band: str = risk_score.get("risk_band", "LOW")
        sanctions_match: bool = verification_result.get("sanctions_match", False)
        pep_match: bool = verification_result.get("pep_match", False)
        nationality = (client_data.get("country_of_citizenship") or client_data.get("nationality") or "").lower()
        is_high_risk_nationality = nationality in _HIGH_RISK_NATIONALITIES

        try:
            ca_initial = float(client_data.get("ca_initial_deposit") or 0)
        except (TypeError, ValueError):
            ca_initial = 0.0
        account_band = "LARGE" if ca_initial > 1_000_000 else "NORMAL"

        decisions: list[CheckpointDecision] = []
        all_docs: set[str] = set()
        escalation_reasons: list[str] = []
        should_escalate = False

        ctx = dict(
            risk_band=risk_band,
            composite_score=composite,
            jurisdiction=nationality or "unknown",
        )

        for rule in self._rules:
            triggered = self._triggered(
                rule=rule,
                risk_band=risk_band,
                composite=composite,
                sanctions_match=sanctions_match,
                pep_match=pep_match,
                is_high_risk_nationality=is_high_risk_nationality,
                selected_products=selected_products,
                account_band=account_band,
            )
            reason = rule.reason_template.format(**ctx) if triggered else ""
            if triggered:
                all_docs.update(rule.required_documents)
                if rule.action == "ESCALATE":
                    should_escalate = True
                    escalation_reasons.append(reason)

            decisions.append(CheckpointDecision(
                rule_id=rule.rule_id,
                action=rule.action,
                triggered=triggered,
                reason=reason,
                required_documents=rule.required_documents if triggered else [],
            ))

        return CheckpointResult(
            should_escalate=should_escalate,
            decisions=decisions,
            required_documents=sorted(all_docs),
            escalation_reasons=escalation_reasons,
        )

    def _triggered(
        self,
        rule: CheckpointRule,
        risk_band: str,
        composite: float,
        sanctions_match: bool,
        pep_match: bool,
        is_high_risk_nationality: bool,
        selected_products: list[str],
        account_band: str,
    ) -> bool:
        rid = rule.rule_id
        if rid == "HIGH_RISK_SCORE":
            return risk_band in ("HIGH", "VERY_HIGH")
        if rid == "SANCTIONS_MATCH":
            return sanctions_match
        if rid == "PEP_MATCH":
            return pep_match
        if rid == "LARGE_CASH_ACCOUNT":
            return "cash_account" in selected_products and account_band == "LARGE"
        if rid == "HIGH_RISK_NATIONALITY":
            return is_high_risk_nationality

        # Generic dimension matching for custom rules added via admin UI
        if rule.risk_level and rule.risk_level != risk_band:
            return False
        if rule.product_type and rule.product_type not in selected_products:
            return False
        if rule.account_value_band and rule.account_value_band != account_band:
            return False
        return True
