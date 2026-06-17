"""Translation helpers: MCP tool outputs → verification dict shape.

Extracted to a separate module so unit tests can import without requiring langgraph.
"""
from __future__ import annotations

from typing import Any


def parse_income(raw: Any) -> float:
    """Convert income strings like '$50,000 - $100,000' to a float midpoint."""
    _MAP = {
        "under $25,000": 20_000.0,
        "$25,000 - $50,000": 37_500.0,
        "$50,000 - $100,000": 75_000.0,
        "$100,000 - $200,000": 150_000.0,
        "over $200,000": 250_000.0,
    }
    if isinstance(raw, (int, float)):
        return float(raw)
    return _MAP.get(str(raw).strip().lower(), 0.0)


def build_verification_dict(
    verify_result: dict[str, Any],
    sanctions_result: dict[str, Any],
    aml_result: dict[str, Any],
    client_data: dict[str, Any],
) -> dict[str, Any]:
    """Translate MCP tool outputs into the verification dict shape expected by
    RiskScorer and CheckpointRuleEngine (preserves output equivalence with the
    former _simulate_identity_verification() shape).
    """
    flags: list[str] = verify_result.get("flags", [])
    verified: bool = verify_result.get("verified", False)
    confidence: float = float(verify_result.get("confidence_score", 0.5))

    is_sanctioned: bool = sanctions_result.get("is_sanctioned", False)
    pep_status: bool = bool(client_data.get("pep_status", False))

    aml_risk_band: str = aml_result.get("risk_band", "LOW")
    # Normalise VERY_HIGH → HIGH so RiskScorer._aml_score() picks the right branch
    aml_risk_level = "HIGH" if aml_risk_band in ("HIGH", "VERY_HIGH") else aml_risk_band

    # Flat list of high-scoring AML risk factor names
    aml_risk_factors: list[str] = [
        f.get("factor", "")
        for f in aml_result.get("risk_factors", [])
        if float(f.get("score", 0)) > 0.3
    ]

    return {
        "verification_id": verify_result.get("provider_reference", ""),
        "name_match_confidence": confidence,
        "document_authentic": verified and "DOCUMENT_EXPIRED" not in flags,
        "document_valid": verified,
        "sanctions_match": is_sanctioned,
        "pep_match": pep_status,
        "aml_risk_factors": aml_risk_factors,
        "aml_risk_level": aml_risk_level,
        "checked_at": verify_result.get("verified_at", ""),
        "provider": verify_result.get("provider", "mcp_identity_verification"),
        "is_simulated": True,
    }
