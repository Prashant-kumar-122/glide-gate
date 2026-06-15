"""Phase 3 snapshot tests for StageDispatcher.

Verifies that StageDispatcher.resolve() maps every wealth-domain stage to the
same Temporal activity name that the old hardcoded if/elif chain (in
orchestrator_agent.py) would have dispatched for that stage.

All tests are pure Python — no DB, no Temporal server required.
DomainDefinition is constructed from the same constants used in the
0014_wealth_domain_seed migration so the test self-documents the
config-to-code mapping.
"""
from __future__ import annotations

import pytest

from app.services.orchestration.stage_dispatcher import (
    SLAHook,
    StageDispatch,
    StageDispatcher,
    _resolve_payload_template,
    _TASK_TYPE_TO_ACTIVITY_NAME,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_domain_def() -> "DomainDefinition":
    """Build a minimal DomainDefinition from the wealth-domain seed constants.

    Mirrors the data in 0014_wealth_domain_seed.py so the snapshot test is
    authoritative without hitting the DB.
    """
    from app.domain.domain_definition import (
        DomainDefinition,
        StageActionSpec,
        StageSpec,
    )

    stages = {
        code: StageSpec(
            stage_code=code,
            display_name=code,
            is_terminal=is_term,
            is_human_pending=is_human,
        )
        for code, is_term, is_human in [
            ("INTAKE",            False, False),
            ("REVIEW",            False, True),
            ("SALES_REVIEW",      False, True),
            ("KYC",               False, False),
            ("PARALLEL_PRODUCTS", False, False),
            ("COMPLETE",          True,  False),
            ("ESCALATED",         True,  False),
        ]
    }

    # Mirrors _TASK_ROUTING in 0014_wealth_domain_seed.py
    task_routing = {
        stage_code: StageActionSpec(
            stage_code=stage_code,
            target_agent=agent,
            task_type=task_type,
            priority=priority,
        )
        for stage_code, agent, task_type, priority in [
            ("INTAKE",            "customer_service",   "collect_client_data",       "NORMAL"),
            ("REVIEW",            "collaboration",      "create_collaboration_room", "HIGH"),
            ("SALES_REVIEW",      "sales_manager",      "sales_manager_review",      "HIGH"),
            ("KYC",               "kyc_compliance",     "run_kyc_check",             "HIGH"),
            ("PARALLEL_PRODUCTS", "product_onboarding", "onboard_product",           "NORMAL"),
            ("COMPLETE",          "notification",       "send_notification",         "NORMAL"),
            ("ESCALATED",         "notification",       "send_escalation_alert",     "CRITICAL"),
        ]
    }

    transitions = {
        "INTAKE":            ["REVIEW"],
        "REVIEW":            ["SALES_REVIEW", "KYC", "COMPLETE", "ESCALATED"],
        "SALES_REVIEW":      ["KYC", "REVIEW"],
        "KYC":               ["PARALLEL_PRODUCTS", "ESCALATED"],
        "PARALLEL_PRODUCTS": ["REVIEW", "COMPLETE", "ESCALATED"],
        "COMPLETE":          [],
        "ESCALATED":         ["REVIEW", "KYC", "COMPLETE"],
    }

    return DomainDefinition(
        domain_id="00000000-0000-0000-0000-000000000001",
        domain_code="wealth_management",
        display_name="Wealth Management",
        is_active=True,
        stages=stages,
        transitions=transitions,
        task_routing=task_routing,
        agent_roster={},
        agent_capabilities={},
        agent_prompts={},
        agent_skills={},
        agent_tool_grants={},
        product_pipelines={},
        slas=[],
        personas={},
        permissions={},
        products={},
        display_config={},
    )


_MOCK_STATE: dict = {
    "case_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "client_id": "bbbbbbbb-0000-0000-0000-000000000001",
    "stage": "INTAKE",
    "selected_products": ["gcf", "ecm"],
    "product_tracks": {},
    "priority_tier": "standard",
    "client_data": {},
    "documents_required": [],
    "documents_received": [],
    "version": 0,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
    "next_stage": None,
    "extra": {},
}


# ── Snapshot: StageDispatcher vs old hardcoded routing ───────────────────────


# Ground-truth mapping: stage_code → expected Temporal activity name.
# Derived from the _RESUME_ROUTING dict (orchestrator_agent.py) and the
# _route_to_stage if/elif chain — what each stage used to dispatch.
_EXPECTED_DISPATCH: dict[str, str] = {
    "INTAKE":            "customer_service_kickoff_activity",
    "REVIEW":            "collaboration_kickoff_activity",
    "SALES_REVIEW":      "sales_manager_kickoff_activity",
    "KYC":               "kyc_compliance_activity",
    "PARALLEL_PRODUCTS": "product_onboarding_activity",
    "COMPLETE":          "notification_activity",       # send_notification per seed
    "ESCALATED":         "escalation_alert_activity",   # send_escalation_alert per seed
}


@pytest.fixture(scope="module")
def dispatcher() -> StageDispatcher:
    return StageDispatcher.from_domain_def(_make_domain_def())


def test_dispatcher_resolve_returns_stage_dispatch(dispatcher: StageDispatcher) -> None:
    result = dispatcher.resolve("KYC", _MOCK_STATE)
    assert isinstance(result, StageDispatch)
    assert result.stage_code == "KYC"


@pytest.mark.parametrize("stage_code,expected_activity", _EXPECTED_DISPATCH.items())
def test_dispatcher_snapshot_all_stages(
    dispatcher: StageDispatcher, stage_code: str, expected_activity: str
) -> None:
    """For every wealth-domain stage, StageDispatcher must return the same
    activity name that the old hardcoded routing chain produced.
    """
    result = dispatcher.resolve(stage_code, _MOCK_STATE)
    assert result is not None, (
        f"StageDispatcher.resolve({stage_code!r}) returned None — "
        f"check that {stage_code!r} has a task_routing entry in the domain"
    )
    assert result.activity_name == expected_activity, (
        f"Stage {stage_code!r}: expected activity {expected_activity!r} "
        f"but got {result.activity_name!r}"
    )


def test_dispatcher_action_spec_carries_correct_task_type(dispatcher: StageDispatcher) -> None:
    """StageDispatch.action_spec mirrors the domain_task_routing row."""
    result = dispatcher.resolve("KYC", _MOCK_STATE)
    assert result is not None
    assert result.action_spec.task_type == "run_kyc_check"
    assert result.action_spec.target_agent == "kyc_compliance"
    assert result.action_spec.priority == "HIGH"


def test_dispatcher_action_spec_escalated(dispatcher: StageDispatcher) -> None:
    result = dispatcher.resolve("ESCALATED", _MOCK_STATE)
    assert result is not None
    assert result.action_spec.task_type == "send_escalation_alert"
    assert result.action_spec.priority == "CRITICAL"


def test_dispatcher_resolve_unknown_stage_returns_none(dispatcher: StageDispatcher) -> None:
    result = dispatcher.resolve("NONEXISTENT_STAGE", _MOCK_STATE)
    assert result is None


def test_dispatcher_is_human_pending(dispatcher: StageDispatcher) -> None:
    assert dispatcher.is_human_pending("REVIEW") is True
    assert dispatcher.is_human_pending("SALES_REVIEW") is True
    assert dispatcher.is_human_pending("KYC") is False
    assert dispatcher.is_human_pending("INTAKE") is False


def test_dispatcher_is_terminal(dispatcher: StageDispatcher) -> None:
    assert dispatcher.is_terminal("COMPLETE") is True
    assert dispatcher.is_terminal("ESCALATED") is True
    assert dispatcher.is_terminal("KYC") is False


def test_all_registered_task_types_covered_by_seed() -> None:
    """Every task_type in the wealth seed must have an entry in the registry."""
    seed_task_types = {
        "collect_client_data",
        "create_collaboration_room",
        "sales_manager_review",
        "run_kyc_check",
        "onboard_product",
        "send_notification",
        "send_escalation_alert",
    }
    missing = seed_task_types - set(_TASK_TYPE_TO_ACTIVITY_NAME.keys())
    assert not missing, f"task_types missing from _TASK_TYPE_TO_ACTIVITY_NAME: {missing}"


# ── Payload template resolver ─────────────────────────────────────────────────


def test_resolve_payload_template_substitutes_known_keys() -> None:
    template = {"id": "{case_id}", "client": "{client_id}", "tier": "{priority_tier}"}
    result = _resolve_payload_template(template, _MOCK_STATE)
    assert result["id"] == "aaaaaaaa-0000-0000-0000-000000000001"
    assert result["client"] == "bbbbbbbb-0000-0000-0000-000000000001"
    assert result["tier"] == "standard"


def test_resolve_payload_template_passes_through_non_strings() -> None:
    template = {"count": 42, "flag": True, "nested": {"a": 1}}
    result = _resolve_payload_template(template, _MOCK_STATE)
    assert result["count"] == 42
    assert result["flag"] is True
    assert result["nested"] == {"a": 1}


def test_resolve_payload_template_leaves_unknown_placeholder() -> None:
    template = {"val": "{unknown_key}"}
    result = _resolve_payload_template(template, _MOCK_STATE)
    # Unrecognised placeholder is left as-is (no KeyError raised)
    assert result["val"] == "{unknown_key}"


def test_resolve_payload_template_empty_returns_empty() -> None:
    assert _resolve_payload_template({}, _MOCK_STATE) == {}


# ── SLAHook stub ─────────────────────────────────────────────────────────────


def test_sla_hook_on_stage_entered_is_callable() -> None:
    # Must not raise — Phase 3 stub is a guaranteed no-op
    SLAHook.on_stage_entered("some-case-id", "KYC", None)


def test_sla_hook_on_stage_entered_returns_none() -> None:
    result = SLAHook.on_stage_entered("x", "ESCALATED", None)
    assert result is None


def test_sla_hook_called_for_every_stage() -> None:
    """SLAHook must accept every valid wealth-domain stage without error."""
    stages = ["INTAKE", "REVIEW", "SALES_REVIEW", "KYC", "PARALLEL_PRODUCTS",
              "COMPLETE", "ESCALATED"]
    for stage in stages:
        SLAHook.on_stage_entered("case-id", stage, None)
