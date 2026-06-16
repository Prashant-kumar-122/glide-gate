"""Phase 4.6 — unit tests for ActivationGateService._evaluate_policy.

All tests are pure Python (no DB required). They exercise the in-process
policy function that mirrors policies/activation.rego.

Coverage:
  1.  Pipeline incomplete → DECLINED
  2.  KYC not passed → DECLINED (is_adverse_action depends on is_credit_product)
  3.  Fraud flagged → DECLINED, is_adverse_action=False
  4.  All criteria clear → ACTIVATED
  5.  KYC PENDING (not PASSED) → DECLINED
  6.  min_risk_level: client below threshold → DECLINED
  7.  min_risk_level: client meets threshold → ACTIVATED
  8.  Credit product decline sets is_adverse_action=True
  9.  Non-credit decline does not set is_adverse_action
  10. UNSUITABLE track_status → DECLINED
  11. fraud_screened=CLEARED does not block activation
  12. Empty activation_criteria with clear state → ACTIVATED
"""
from __future__ import annotations

import pytest

from app.services.activation.activation_gate_service import _evaluate_policy


# ── Helpers ───────────────────────────────────────────────────────────────────

def _state(
    kyc_status: str = "PASSED",
    fraud_screened: str = "CLEARED",
    kyc_risk_band: str = "low",
) -> dict:
    return {"extra": {
        "kyc_status": kyc_status,
        "fraud_screened": fraud_screened,
        "kyc_risk_band": kyc_risk_band,
    }}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_pipeline_incomplete_declined():
    allowed, reason, adverse = _evaluate_policy(_state(), {}, track_status="FAILED")
    assert not allowed
    assert reason is not None and "FAILED" in reason
    assert not adverse


def test_unsuitable_pipeline_declined():
    allowed, reason, adverse = _evaluate_policy(_state(), {}, track_status="UNSUITABLE")
    assert not allowed
    assert "UNSUITABLE" in (reason or "")
    assert not adverse


def test_kyc_not_passed_declined():
    allowed, reason, adverse = _evaluate_policy(
        _state(kyc_status="FAILED"), {}, track_status="COMPLETE"
    )
    assert not allowed
    assert "FAILED" in (reason or "")
    assert not adverse  # no is_credit_product in criteria


def test_kyc_pending_declined():
    allowed, reason, adverse = _evaluate_policy(
        _state(kyc_status="PENDING"), {}, track_status="COMPLETE"
    )
    assert not allowed
    assert "PENDING" in (reason or "")


def test_fraud_flagged_declined():
    allowed, reason, adverse = _evaluate_policy(
        _state(fraud_screened="FLAGGED"), {}, track_status="COMPLETE"
    )
    assert not allowed
    assert "Fraud" in (reason or "")
    assert not adverse  # fraud decline is not an adverse action (ECOA)


def test_all_criteria_clear_activated():
    allowed, reason, adverse = _evaluate_policy(_state(), {}, track_status="COMPLETE")
    assert allowed
    assert reason is None
    assert not adverse


def test_empty_criteria_with_clear_state_activated():
    allowed, reason, adverse = _evaluate_policy(_state(), activation_criteria={}, track_status="COMPLETE")
    assert allowed


def test_fraud_cleared_does_not_block():
    allowed, reason, adverse = _evaluate_policy(
        _state(fraud_screened="CLEARED"), {}, track_status="COMPLETE"
    )
    assert allowed


def test_min_risk_level_client_below_threshold_declined():
    criteria = {"min_risk_level": "high"}
    # client's kyc_risk_band is "low" (rank 1) — below "high" (rank 3)
    allowed, reason, adverse = _evaluate_policy(
        _state(kyc_risk_band="low"), criteria, track_status="COMPLETE"
    )
    assert not allowed
    assert "minimum" in (reason or "").lower()


def test_min_risk_level_client_meets_threshold_activated():
    criteria = {"min_risk_level": "medium"}
    # client's kyc_risk_band is "high" (rank 3) — above "medium" (rank 2)
    allowed, reason, adverse = _evaluate_policy(
        _state(kyc_risk_band="high"), criteria, track_status="COMPLETE"
    )
    assert allowed


def test_credit_product_kyc_decline_sets_adverse_action():
    criteria = {"is_credit_product": True}
    allowed, reason, adverse = _evaluate_policy(
        _state(kyc_status="FAILED"), criteria, track_status="COMPLETE"
    )
    assert not allowed
    assert adverse  # credit product KYC decline triggers ECOA adverse-action flag


def test_non_credit_product_kyc_decline_no_adverse_action():
    criteria = {"is_credit_product": False}
    allowed, reason, adverse = _evaluate_policy(
        _state(kyc_status="FAILED"), criteria, track_status="COMPLETE"
    )
    assert not allowed
    assert not adverse


def test_service_has_no_delete_method():
    """WORM check: ActivationGateService must not expose delete() or update()."""
    from app.services.activation.activation_gate_service import ActivationGateService

    svc = ActivationGateService()
    assert not hasattr(svc, "delete"), "ActivationGateService must not expose delete()"
    assert not hasattr(svc, "update"), "ActivationGateService must not expose update()"
