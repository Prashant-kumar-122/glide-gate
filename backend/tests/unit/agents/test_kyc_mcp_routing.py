"""Phase 6 — unit tests for KYC MCP routing and MCPRegistry grant-checking.

All tests are pure Python (no live DB required).  They verify:

  1. _build_verification_dict() correctly translates three MCP tool outputs into
     the verification dict shape expected by RiskScorer / CheckpointRuleEngine
     (snapshot-equivalence check).
  2. RiskScorer.compute() and CheckpointRuleEngine.evaluate() produce valid output
     when given a verification dict built from _build_verification_dict().
  3. MCPRegistry.invoke() raises PermissionError when the domain exists but the
     agent has no grant row (fail-closed, ADR-007).
  4. MCPRegistry.invoke() allows through when agent_id == "unknown" (legacy bypass).
  5. MCPRegistry.invoke() allows through when the domain is not found in the DB
     (migration-order safety — logs warning, does not raise).
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ── Helpers imported from the graph module ────────────────────────────────────

from app.agents.kyc_compliance.verification_translation import (
    build_verification_dict as _build_verification_dict,
    parse_income as _parse_income,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_VERIFY_RESULT = {
    "verified": True,
    "confidence_score": 0.92,
    "identity_match": {
        "name_match": True,
        "dob_match": True,
        "doc_valid": True,
        "doc_not_expired": True,
    },
    "flags": [],
    "provider": "GlideVerify-SIM",
    "provider_reference": "GV-123456",
    "verified_at": "2026-06-16T00:00:00",
}

_VERIFY_RESULT_EXPIRED = {
    **_VERIFY_RESULT,
    "verified": False,
    "flags": ["DOCUMENT_EXPIRED"],
}

_SANCTIONS_CLEAR = {
    "is_sanctioned": False,
    "screening_score": 0.02,
    "matches": [],
    "lists_screened": ["OFAC SDN List"],
    "screened_at": "2026-06-16T00:00:00",
}

_SANCTIONS_HIT = {
    "is_sanctioned": True,
    "screening_score": 0.93,
    "matches": [{"name": "TEST HIT", "match_score": 0.93}],
    "lists_screened": ["OFAC SDN List"],
    "screened_at": "2026-06-16T00:00:00",
}

_AML_LOW = {
    "risk_score": 0.08,
    "risk_band": "LOW",
    "risk_factors": [
        {"factor": "pep_status", "weight": 0.35, "score": 0.05},
        {"factor": "country_risk", "weight": 0.30, "score": 0.05},
        {"factor": "source_of_wealth", "weight": 0.20, "score": 0.10},
        {"factor": "occupation", "weight": 0.15, "score": 0.10},
    ],
    "recommended_action": "SIMPLIFIED_DUE_DILIGENCE",
}

_AML_VERY_HIGH = {
    "risk_score": 0.82,
    "risk_band": "VERY_HIGH",
    "risk_factors": [
        {"factor": "pep_status", "weight": 0.35, "score": 0.90},
        {"factor": "country_risk", "weight": 0.30, "score": 0.80},
    ],
    "recommended_action": "MANDATORY_ENHANCED_DUE_DILIGENCE",
}

_CLIENT_DATA = {
    "full_name": "Test Client",
    "nationality": "IN",
    "pep_status": False,
    "annual_income": "$50,000 - $100,000",
}


# ── _build_verification_dict ──────────────────────────────────────────────────


def test_build_verification_dict_passed_shape():
    """Result contains all fields expected by RiskScorer and CheckpointRuleEngine."""
    result = _build_verification_dict(
        _VERIFY_RESULT, _SANCTIONS_CLEAR, _AML_LOW, _CLIENT_DATA
    )
    assert result["document_authentic"] is True
    assert result["document_valid"] is True
    assert result["sanctions_match"] is False
    assert result["pep_match"] is False
    assert result["name_match_confidence"] == pytest.approx(0.92)
    assert result["aml_risk_level"] == "LOW"
    assert isinstance(result["aml_risk_factors"], list)


def test_build_verification_dict_sanctions_hit():
    """sanctions_match=True when check_sanctions reports is_sanctioned."""
    result = _build_verification_dict(
        _VERIFY_RESULT, _SANCTIONS_HIT, _AML_LOW, _CLIENT_DATA
    )
    assert result["sanctions_match"] is True


def test_build_verification_dict_document_expired():
    """document_authentic=False when verify_identity flags DOCUMENT_EXPIRED."""
    result = _build_verification_dict(
        _VERIFY_RESULT_EXPIRED, _SANCTIONS_CLEAR, _AML_LOW, _CLIENT_DATA
    )
    assert result["document_authentic"] is False


def test_build_verification_dict_very_high_aml_normalised():
    """VERY_HIGH risk_band is normalised to HIGH for RiskScorer compatibility."""
    result = _build_verification_dict(
        _VERIFY_RESULT, _SANCTIONS_CLEAR, _AML_VERY_HIGH, _CLIENT_DATA
    )
    assert result["aml_risk_level"] == "HIGH"


def test_build_verification_dict_pep_from_client_data():
    """pep_match reflects client_data.pep_status, not AML risk score."""
    pep_client = {**_CLIENT_DATA, "pep_status": True}
    result = _build_verification_dict(
        _VERIFY_RESULT, _SANCTIONS_CLEAR, _AML_LOW, pep_client
    )
    assert result["pep_match"] is True


# ── RiskScorer + CheckpointRuleEngine accept mcp-translated verification ──────

from app.agents.kyc_compliance.risk_scorer import RiskScorer
from app.agents.kyc_compliance.checkpoint_rule_engine import CheckpointRuleEngine


def test_risk_scorer_accepts_mcp_verification_dict():
    """RiskScorer.compute() returns a valid RiskScore from MCP-translated dict."""
    verification = _build_verification_dict(
        _VERIFY_RESULT, _SANCTIONS_CLEAR, _AML_LOW, _CLIENT_DATA
    )
    score = RiskScorer().compute(_CLIENT_DATA, verification)
    assert score.composite_score >= 0.0
    assert score.risk_band in ("LOW", "MEDIUM", "HIGH", "VERY_HIGH")


def test_risk_scorer_sanctions_hit_yields_high_risk_band():
    """Sanctions match drives identity + AML scores to 100 → HIGH or VERY_HIGH band."""
    verification = _build_verification_dict(
        _VERIFY_RESULT, _SANCTIONS_HIT, _AML_LOW, _CLIENT_DATA
    )
    score = RiskScorer().compute(_CLIENT_DATA, verification)
    # composite = 100×0.4 + 100×0.4 + profile×0.2; profile~0 → composite ≈ 80 → HIGH
    assert score.risk_band in ("HIGH", "VERY_HIGH")
    assert score.composite_score >= 60.0


def test_checkpoint_engine_escalates_on_sanctions():
    """CheckpointRuleEngine triggers ESCALATE rule when sanctions_match=True."""
    verification = _build_verification_dict(
        _VERIFY_RESULT, _SANCTIONS_HIT, _AML_LOW, _CLIENT_DATA
    )
    score = RiskScorer().compute(_CLIENT_DATA, verification)
    result = CheckpointRuleEngine().evaluate(
        risk_score=score.model_dump(),
        client_data=_CLIENT_DATA,
        verification_result=verification,
        selected_products=[],
    )
    assert result.should_escalate is True


def test_checkpoint_engine_passes_clean_client():
    """Clean client (verified, no sanctions, low AML) does not trigger escalation."""
    verification = _build_verification_dict(
        _VERIFY_RESULT, _SANCTIONS_CLEAR, _AML_LOW, _CLIENT_DATA
    )
    score = RiskScorer().compute(_CLIENT_DATA, verification)
    result = CheckpointRuleEngine().evaluate(
        risk_score=score.model_dump(),
        client_data=_CLIENT_DATA,
        verification_result=verification,
        selected_products=[],
    )
    assert result.should_escalate is False


# ── _parse_income ─────────────────────────────────────────────────────────────


def test_parse_income_range_string():
    assert _parse_income("$50,000 - $100,000") == pytest.approx(75_000.0)


def test_parse_income_numeric():
    assert _parse_income(120_000) == pytest.approx(120_000.0)


def test_parse_income_unknown_returns_zero():
    assert _parse_income("not a real value") == pytest.approx(0.0)


# ── MCPRegistry grant-checking ────────────────────────────────────────────────

from app.mcp.mcp_connector import MCPRegistry, _grant_cache


@pytest.fixture(autouse=True)
def clear_grant_cache():
    _grant_cache.clear()
    yield
    _grant_cache.clear()


@pytest.mark.asyncio
async def test_mcp_registry_unknown_agent_bypasses_grant_check():
    """agent_id='unknown' skips grant check (legacy callers)."""
    registry = MCPRegistry()
    fake_connector = MagicMock()
    fake_connector.connector_name = "test_conn"
    fake_connector.invoke = AsyncMock(return_value={"ok": True})
    registry.register(fake_connector)

    result = await registry.invoke(
        "test_conn", "some_tool", {},
        agent_id="unknown",
    )
    assert result == {"ok": True}
    fake_connector.invoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_mcp_registry_raises_permission_error_when_domain_exists_no_grant():
    """Raises PermissionError when domain is seeded but agent has no grant row."""
    registry = MCPRegistry()
    fake_connector = MagicMock()
    fake_connector.connector_name = "identity_verification"
    registry.register(fake_connector)

    # First session scalar: grant check returns False (no grant)
    # Second session scalar: domain existence check returns True (domain exists)
    with patch("app.database.AsyncSessionLocal", _make_mock_session_ctx([False, True])):
        with pytest.raises(PermissionError, match="not granted"):
            await registry.invoke(
                "identity_verification", "verify_identity", {},
                agent_id="kyc_compliance",
                domain_code="wealth_management",
            )


@pytest.mark.asyncio
async def test_mcp_registry_allows_when_domain_not_found():
    """Logs warning and allows through when domain row doesn't exist yet."""
    registry = MCPRegistry()
    fake_connector = MagicMock()
    fake_connector.connector_name = "identity_verification"
    fake_connector.invoke = AsyncMock(return_value={"ok": True})
    registry.register(fake_connector)

    # grant check: False; domain existence: False (domain not seeded)
    with patch("app.database.AsyncSessionLocal", _make_mock_session_ctx([False, False])):
        result = await registry.invoke(
            "identity_verification", "verify_identity", {},
            agent_id="kyc_compliance",
            domain_code="unknown_domain",
        )
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_mcp_registry_allows_when_grant_exists():
    """Proceeds normally when grant row is present in DB."""
    registry = MCPRegistry()
    fake_connector = MagicMock()
    fake_connector.connector_name = "identity_verification"
    fake_connector.invoke = AsyncMock(return_value={"verified": True})
    registry.register(fake_connector)

    # grant check: True (grant exists)
    with patch("app.database.AsyncSessionLocal", _make_mock_session_ctx([True])):
        result = await registry.invoke(
            "identity_verification", "verify_identity", {},
            agent_id="kyc_compliance",
            domain_code="wealth_management",
        )
    assert result == {"verified": True}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_mock_session_ctx(scalar_sequence: list):
    """Build a context manager whose session.scalar() returns values from the list."""
    values = iter(scalar_sequence)

    class _Session:
        async def scalar(self, *args, **kwargs):
            try:
                return next(values)
            except StopIteration:
                return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class _Ctx:
        def __call__(self):
            return self

        async def __aenter__(self):
            return _Session()

        async def __aexit__(self, *args):
            pass

    return _Ctx()
