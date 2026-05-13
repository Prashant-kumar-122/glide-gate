from __future__ import annotations

import hashlib
import random
from datetime import date, datetime
from typing import Any


# High-risk nationalities for AML scoring simulation
_HIGH_RISK_COUNTRIES = {
    "AF", "BY", "CF", "CG", "CD", "CU", "ER", "ET", "GN", "GW", "HT",
    "IR", "IQ", "KP", "LB", "LY", "ML", "MM", "NI", "PK", "RU", "SO",
    "SS", "SD", "SY", "UA", "VE", "YE", "ZW",
}

# Sanctioned-name fragments for deterministic demo hits
_SANCTIONS_FRAGMENTS = ["NAZAROV", "AL-RASHID", "PETROV", "CHUKWU", "IBRAHIM AL"]


def _seed_from(value: str) -> random.Random:
    """Return a seeded Random instance so results are stable per input."""
    digest = int(hashlib.md5(value.encode()).hexdigest(), 16)
    return random.Random(digest)


def simulate_verify_identity(inputs: dict[str, Any]) -> dict[str, Any]:
    full_name: str = inputs.get("full_name", "")
    document_number: str = inputs.get("document_number", "")
    document_expiry: str = inputs.get("document_expiry", "2099-12-31")
    nationality: str = inputs.get("nationality", "")

    rng = _seed_from(f"{full_name}:{document_number}")
    confidence = round(rng.uniform(0.72, 0.99), 4)

    try:
        expiry = date.fromisoformat(document_expiry)
        doc_not_expired = expiry >= date.today()
    except ValueError:
        doc_not_expired = True

    name_match = confidence >= 0.80
    dob_match = confidence >= 0.75
    doc_valid = document_number.isalnum() and len(document_number) >= 6
    verified = name_match and dob_match and doc_valid and doc_not_expired

    flags: list[str] = []
    if not doc_not_expired:
        flags.append("DOCUMENT_EXPIRED")
    if not doc_valid:
        flags.append("INVALID_DOCUMENT_NUMBER")
    if nationality.upper() in _HIGH_RISK_COUNTRIES:
        flags.append("HIGH_RISK_NATIONALITY")
    if confidence < 0.80:
        flags.append("LOW_CONFIDENCE_MATCH")

    return {
        "verified": verified,
        "confidence_score": confidence,
        "identity_match": {
            "name_match": name_match,
            "dob_match": dob_match,
            "doc_valid": doc_valid,
            "doc_not_expired": doc_not_expired,
        },
        "flags": flags,
        "provider": "GlideVerify-SIM",
        "provider_reference": f"GV-{rng.randint(100000, 999999)}",
        "verified_at": datetime.utcnow().isoformat(),
    }


def simulate_check_sanctions(inputs: dict[str, Any]) -> dict[str, Any]:
    full_name: str = inputs.get("full_name", "").upper()
    aliases: list[str] = [a.upper() for a in inputs.get("aliases", [])]
    nationality: str = inputs.get("nationality", "")

    rng = _seed_from(full_name)

    # Check for demo-scenario name fragments
    hit_fragment = next(
        (f for f in _SANCTIONS_FRAGMENTS if f in full_name), None
    )
    is_sanctioned = hit_fragment is not None

    matches: list[dict[str, Any]] = []
    if is_sanctioned and hit_fragment:
        score = round(rng.uniform(0.85, 0.98), 4)
        matches.append({
            "name": hit_fragment,
            "list_name": "UN Security Council Consolidated List",
            "match_score": score,
            "match_type": "FUZZY_NAME",
        })
    elif nationality.upper() in _HIGH_RISK_COUNTRIES:
        score = round(rng.uniform(0.10, 0.35), 4)
        matches.append({
            "name": full_name,
            "list_name": "OFAC SDN List",
            "match_score": score,
            "match_type": "COUNTRY_RISK",
        })

    screening_score = matches[0]["match_score"] if matches else round(rng.uniform(0.0, 0.08), 4)

    return {
        "is_sanctioned": is_sanctioned,
        "screening_score": screening_score,
        "matches": matches,
        "lists_screened": [
            "UN Security Council Consolidated List",
            "OFAC SDN List",
            "EU Consolidated Sanctions List",
            "UK HMT Financial Sanctions",
        ],
        "screened_at": datetime.utcnow().isoformat(),
        "provider": "GlideScreen-SIM",
        "provider_reference": f"GS-{rng.randint(100000, 999999)}",
    }


def simulate_score_aml_risk(inputs: dict[str, Any]) -> dict[str, Any]:
    nationality: str = inputs.get("nationality", "")
    country_of_residence: str = inputs.get("country_of_residence", "")
    occupation: str = inputs.get("occupation", "").lower()
    annual_income: float = float(inputs.get("annual_income", 0))
    source_of_wealth: str = inputs.get("source_of_wealth", "").lower()
    pep_status: bool = bool(inputs.get("pep_status", False))
    full_name: str = inputs.get("full_name", "")

    rng = _seed_from(f"{full_name}:{nationality}")

    risk_factors: list[dict[str, Any]] = []
    cumulative = 0.0

    # PEP check (weight 0.35)
    pep_score = 0.90 if pep_status else 0.05
    risk_factors.append({
        "factor": "pep_status",
        "weight": 0.35,
        "score": pep_score,
        "description": "Politically Exposed Person" if pep_status else "Not a PEP",
    })
    cumulative += 0.35 * pep_score

    # Country risk (weight 0.30)
    is_high_risk_country = (
        nationality.upper() in _HIGH_RISK_COUNTRIES
        or country_of_residence.upper() in _HIGH_RISK_COUNTRIES
    )
    country_score = round(rng.uniform(0.70, 0.95), 4) if is_high_risk_country else round(rng.uniform(0.02, 0.25), 4)
    risk_factors.append({
        "factor": "country_risk",
        "weight": 0.30,
        "score": country_score,
        "description": "High-risk jurisdiction" if is_high_risk_country else "Low-risk jurisdiction",
    })
    cumulative += 0.30 * country_score

    # Income / source of wealth (weight 0.20)
    suspicious_sow = any(kw in source_of_wealth for kw in ["cash", "gambling", "crypto", "unknown"])
    sow_score = round(rng.uniform(0.55, 0.85), 4) if suspicious_sow else round(rng.uniform(0.02, 0.30), 4)
    high_income = annual_income > 500_000
    if high_income:
        sow_score = min(sow_score + 0.10, 1.0)
    risk_factors.append({
        "factor": "source_of_wealth",
        "weight": 0.20,
        "score": round(sow_score, 4),
        "description": "Unusual source of wealth" if suspicious_sow else "Standard source of wealth",
    })
    cumulative += 0.20 * sow_score

    # Occupation (weight 0.15)
    sensitive_occupations = {"politician", "judge", "military", "diplomat", "banker", "dealer"}
    occ_hit = any(kw in occupation for kw in sensitive_occupations)
    occ_score = round(rng.uniform(0.40, 0.70), 4) if occ_hit else round(rng.uniform(0.02, 0.25), 4)
    risk_factors.append({
        "factor": "occupation",
        "weight": 0.15,
        "score": occ_score,
        "description": f"Sensitive occupation: {occupation}" if occ_hit else "Standard occupation",
    })
    cumulative += 0.15 * occ_score

    risk_score = round(min(cumulative, 1.0), 4)

    if risk_score >= 0.70:
        risk_band, action = "VERY_HIGH", "MANDATORY_ENHANCED_DUE_DILIGENCE"
    elif risk_score >= 0.50:
        risk_band, action = "HIGH", "ENHANCED_DUE_DILIGENCE"
    elif risk_score >= 0.25:
        risk_band, action = "MEDIUM", "STANDARD_DUE_DILIGENCE"
    else:
        risk_band, action = "LOW", "SIMPLIFIED_DUE_DILIGENCE"

    return {
        "risk_score": risk_score,
        "risk_band": risk_band,
        "risk_factors": risk_factors,
        "recommended_action": action,
        "scored_at": datetime.utcnow().isoformat(),
        "provider": "GlideAML-SIM",
        "provider_reference": f"GA-{rng.randint(100000, 999999)}",
    }
