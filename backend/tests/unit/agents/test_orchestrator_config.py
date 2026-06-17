"""
Phase 0 snapshot test — asserts the orchestrator config JSON encodes exactly the
same transition graph and resume routing that was previously hardcoded in Python.
"""
from app.agents.base.a2a_types import AgentID, OnboardingStage, TaskType
from app.agents.orchestrator.workflow_state_machine import _TRANSITIONS
from app.agents.orchestrator.orchestrator_agent import _RESUME_ROUTING

# The authoritative graph that existed before Phase 0 (verbatim from git history).
_EXPECTED_TRANSITIONS: dict[OnboardingStage, set[OnboardingStage]] = {
    OnboardingStage.INTAKE: {
        OnboardingStage.REVIEW,
    },
    OnboardingStage.REVIEW: {
        OnboardingStage.SALES_REVIEW,
        OnboardingStage.KYC,
        OnboardingStage.COMPLETE,
        OnboardingStage.ESCALATED,
    },
    OnboardingStage.SALES_REVIEW: {
        OnboardingStage.KYC,
        OnboardingStage.REVIEW,
    },
    OnboardingStage.KYC: {
        OnboardingStage.PARALLEL_PRODUCTS,
        OnboardingStage.ESCALATED,
    },
    OnboardingStage.PARALLEL_PRODUCTS: {
        OnboardingStage.REVIEW,
        OnboardingStage.COMPLETE,
        OnboardingStage.ESCALATED,
    },
    OnboardingStage.COMPLETE: set(),
    OnboardingStage.ESCALATED: {
        OnboardingStage.REVIEW,
        OnboardingStage.KYC,
        OnboardingStage.COMPLETE,
    },
}

_EXPECTED_RESUME_ROUTING: dict[OnboardingStage, tuple[AgentID, TaskType]] = {
    OnboardingStage.INTAKE: (AgentID.CUSTOMER_SERVICE, TaskType.COLLECT_CLIENT_DATA),
    OnboardingStage.SALES_REVIEW: (AgentID.SALES_MANAGER, TaskType.SALES_MANAGER_REVIEW),
    OnboardingStage.KYC: (AgentID.KYC_COMPLIANCE, TaskType.RUN_KYC_CHECK),
    OnboardingStage.PARALLEL_PRODUCTS: (AgentID.PRODUCT_ONBOARDING, TaskType.ONBOARD_PRODUCT),
}


def test_fsm_transitions_match_expected_graph() -> None:
    assert _TRANSITIONS == _EXPECTED_TRANSITIONS


def test_resume_routing_matches_expected() -> None:
    assert _RESUME_ROUTING == _EXPECTED_RESUME_ROUTING


def test_all_stages_present_in_transitions() -> None:
    for stage in OnboardingStage:
        assert stage in _TRANSITIONS, f"Stage {stage!r} missing from loaded transitions"


def test_no_dangling_transition_targets() -> None:
    valid_stages = set(OnboardingStage)
    for from_stage, targets in _TRANSITIONS.items():
        for to_stage in targets:
            assert to_stage in valid_stages, (
                f"Transition {from_stage!r} → {to_stage!r} references unknown stage"
            )
