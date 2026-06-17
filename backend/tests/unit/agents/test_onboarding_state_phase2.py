"""Phase 2 characterization tests — OnboardingState split into typed core + extension bag.

These tests were written BEFORE the Phase 2 refactor to capture expected behavior,
and RE-RUN after to verify behavioral equivalence (diff must be empty).

Covers:
- OnboardingState round-trip serialization with wealth extension fields
- WealthExtension accessor correctness
- Backward-compatibility migration (old flat shared_context → extra bag)
- priority_tier field default and propagation
- OnboardingStateDict extra key layout for LangGraph compatibility
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest


# ── 1. Core field contract ─────────────────────────────────────────────────────


def test_onboarding_state_core_fields() -> None:
    from app.agents.base.a2a_types import OnboardingState

    case_id = uuid4()
    client_id = uuid4()
    state = OnboardingState(case_id=case_id, client_id=client_id)

    assert state.case_id == case_id
    assert state.client_id == client_id
    assert state.stage == "INTAKE"
    assert state.selected_products == []
    assert state.product_tracks == {}
    assert state.client_data == {}
    assert state.documents_required == []
    assert state.documents_received == []
    assert state.version == 0
    assert state.priority_tier == "standard"


def test_onboarding_state_priority_tier_default() -> None:
    from app.agents.base.a2a_types import OnboardingState

    state = OnboardingState(case_id=uuid4(), client_id=uuid4())
    assert state.priority_tier == "standard"


def test_onboarding_state_priority_tier_custom() -> None:
    from app.agents.base.a2a_types import OnboardingState

    state = OnboardingState(case_id=uuid4(), client_id=uuid4(), priority_tier="premium")
    assert state.priority_tier == "premium"


# ── 2. WealthExtension accessor ───────────────────────────────────────────────


def test_wealth_extension_defaults() -> None:
    from app.agents.base.a2a_types import OnboardingState, WealthExtension

    state = OnboardingState(case_id=uuid4(), client_id=uuid4())
    ext = WealthExtension.from_state(state)

    assert ext.kyc_status == "PENDING"
    assert ext.kyc_risk_score is None
    assert ext.sales_review_id is None
    assert ext.sales_review_decision == "PENDING"
    assert ext.escalation_reason is None
    assert ext.human_review_id is None


def test_wealth_extension_reads_from_extra() -> None:
    from app.agents.base.a2a_types import OnboardingState, WealthExtension

    review_id = uuid4()
    human_id = uuid4()
    state = OnboardingState(
        case_id=uuid4(),
        client_id=uuid4(),
        extra={
            "kyc_status": "PASSED",
            "kyc_risk_score": 0.42,
            "sales_review_id": str(review_id),
            "sales_review_decision": "APPROVED",
            "escalation_reason": "High risk customer",
            "human_review_id": str(human_id),
        },
    )
    ext = WealthExtension.from_state(state)

    assert ext.kyc_status == "PASSED"
    assert ext.kyc_risk_score == pytest.approx(0.42)
    assert ext.sales_review_id == review_id
    assert ext.sales_review_decision == "APPROVED"
    assert ext.escalation_reason == "High risk customer"
    assert ext.human_review_id == human_id


# ── 3. Round-trip serialization ───────────────────────────────────────────────


def test_onboarding_state_round_trip_with_wealth_fields() -> None:
    """Wealth fields stored in extra survive model_dump → model_validate."""
    from app.agents.base.a2a_types import OnboardingState, WealthExtension

    original = OnboardingState(
        case_id=uuid4(),
        client_id=uuid4(),
        stage="KYC",
        priority_tier="premium",
        extra={
            "kyc_status": "FAILED",
            "kyc_risk_score": 0.85,
            "escalation_reason": "AML flag",
        },
    )

    serialized = original.model_dump(mode="json")
    restored = OnboardingState.model_validate(serialized)

    ext = WealthExtension.from_state(restored)
    assert restored.stage == "KYC"
    assert restored.priority_tier == "premium"
    assert ext.kyc_status == "FAILED"
    assert ext.kyc_risk_score == pytest.approx(0.85)
    assert ext.escalation_reason == "AML flag"


def test_priority_tier_survives_round_trip() -> None:
    from app.agents.base.a2a_types import OnboardingState

    original = OnboardingState(case_id=uuid4(), client_id=uuid4(), priority_tier="sme")
    data = original.model_dump(mode="json")
    restored = OnboardingState.model_validate(data)
    assert restored.priority_tier == "sme"


# ── 4. Backward-compat migration (old flat shared_context) ────────────────────


def test_backward_compat_flat_wealth_fields_migrated_to_extra() -> None:
    """Old shared_context rows with kyc_status at top level are migrated to extra on load."""
    from app.agents.base.a2a_types import OnboardingState, WealthExtension

    # Simulate old shared_context JSONB format (pre-Phase-2)
    old_ctx = {
        "case_id": str(uuid4()),
        "client_id": str(uuid4()),
        "stage": "KYC",
        "selected_products": ["equity_fund"],
        "product_tracks": {},
        "client_data": {},
        "documents_required": [],
        "documents_received": [],
        "kyc_status": "ESCALATED",
        "kyc_risk_score": 0.91,
        "sales_review_id": None,
        "sales_review_decision": "PENDING",
        "escalation_reason": "Sanctions match",
        "human_review_id": None,
        "version": 3,
    }

    state = OnboardingState.model_validate(old_ctx)
    ext = WealthExtension.from_state(state)

    assert state.stage == "KYC"
    assert state.version == 3
    assert ext.kyc_status == "ESCALATED"
    assert ext.kyc_risk_score == pytest.approx(0.91)
    assert ext.escalation_reason == "Sanctions match"


def test_backward_compat_extra_wins_over_flat_fields() -> None:
    """If both extra and flat fields present, extra takes precedence (no overwrite)."""
    from app.agents.base.a2a_types import OnboardingState, WealthExtension

    ambiguous = {
        "case_id": str(uuid4()),
        "client_id": str(uuid4()),
        "stage": "KYC",
        "selected_products": [],
        "product_tracks": {},
        "client_data": {},
        "documents_required": [],
        "documents_received": [],
        "kyc_status": "FAILED",           # top-level (old)
        "extra": {"kyc_status": "PASSED"},  # nested (new)
        "version": 1,
    }

    state = OnboardingState.model_validate(ambiguous)
    ext = WealthExtension.from_state(state)

    # extra takes precedence
    assert ext.kyc_status == "PASSED"


# ── 5. OnboardingStateDict extra layout ───────────────────────────────────────


def test_onboarding_state_dict_has_extra_key() -> None:
    """After Phase 2 the TypedDict gains extra and priority_tier; wealth fields removed."""
    from app.agents.base.a2a_types import OnboardingStateDict

    annotations = OnboardingStateDict.__annotations__
    assert "extra" in annotations, "OnboardingStateDict must have 'extra' key"
    assert "priority_tier" in annotations, "OnboardingStateDict must have 'priority_tier' key"

    # Wealth fields must NOT be top-level keys any more
    for field in ("kyc_status", "kyc_risk_score", "sales_review_id",
                  "sales_review_decision", "escalation_reason", "human_review_id"):
        assert field not in annotations, (
            f"Wealth field {field!r} must be in extra, not top-level OnboardingStateDict"
        )


def test_onboarding_state_dict_keeps_temporal_routing_hints() -> None:
    """_product_code and _product_track_status must remain in typed core (Temporal guard)."""
    from app.agents.base.a2a_types import OnboardingStateDict

    annotations = OnboardingStateDict.__annotations__
    assert "_product_code" in annotations, "_product_code must be in typed core"
    assert "_product_track_status" in annotations, "_product_track_status must be in typed core"
