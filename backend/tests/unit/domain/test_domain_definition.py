"""Phase 1 — unit tests for DomainDefinition + DomainDefinitionLoader.validate().

All tests here are pure Python (no DB required).  They cover:
  - SLASpec rejects warning_pct >= escalation_pct
  - DomainDefinitionLoader.validate() rejects:
      * orphan stage in transition
      * unreachable terminal stage
      * SLA row referencing undefined stage
      * warning_pct >= escalation_pct (via validate, not just SLASpec)
  - Round-trip: build a DomainDefinition matching the wealth Phase-0 config
    and assert it validates cleanly and contains the expected stages/transitions.
"""
from __future__ import annotations

import pytest

from app.domain.domain_definition import (
    AgentCapabilitySpec,
    AgentRosterEntry,
    DomainDefinition,
    DomainDefinitionLoader,
    DomainValidationError,
    SLASpec,
    StageActionSpec,
    StageSpec,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _minimal_domain(**overrides) -> DomainDefinition:
    """Build a minimal valid DomainDefinition for use in negative tests."""
    base = dict(
        domain_id="00000000-0000-0000-0000-000000000001",
        domain_code="test",
        display_name="Test Domain",
        is_active=True,
        initial_stage="START",
        stages={
            "START": StageSpec(stage_code="START", display_name="Start"),
            "DONE":  StageSpec(stage_code="DONE",  display_name="Done", is_terminal=True),
        },
        transitions={
            "START": ["DONE"],
            "DONE":  [],
        },
        task_routing={},
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
    base.update(overrides)
    return DomainDefinition(**base)


# ── SLASpec validation ────────────────────────────────────────────────────────


def test_sla_spec_rejects_equal_pcts() -> None:
    with pytest.raises(ValueError, match="warning_pct"):
        SLASpec(
            stage_code="KYC",
            window_hours=24.0,
            warning_pct=80,
            escalation_pct=80,
            warning_task_type="send_notification",
            escalation_task_type="send_escalation_alert",
            escalation_target_agent="notification",
        )


def test_sla_spec_rejects_warning_greater_than_escalation() -> None:
    with pytest.raises(ValueError, match="warning_pct"):
        SLASpec(
            stage_code="KYC",
            window_hours=24.0,
            warning_pct=90,
            escalation_pct=80,
            warning_task_type="send_notification",
            escalation_task_type="send_escalation_alert",
            escalation_target_agent="notification",
        )


def test_sla_spec_accepts_valid_pcts() -> None:
    sla = SLASpec(
        stage_code="KYC",
        window_hours=24.0,
        warning_pct=70,
        escalation_pct=100,
        warning_task_type="send_notification",
        escalation_task_type="send_escalation_alert",
        escalation_target_agent="notification",
    )
    assert sla.warning_pct < sla.escalation_pct


# ── DomainDefinitionLoader.validate() ────────────────────────────────────────


def test_validate_passes_on_minimal_valid_domain() -> None:
    domain = _minimal_domain()
    DomainDefinitionLoader.validate(domain)  # must not raise


def test_validate_rejects_unknown_initial_stage() -> None:
    domain = _minimal_domain(initial_stage="NONEXISTENT")
    with pytest.raises(DomainValidationError, match="initial_stage"):
        DomainDefinitionLoader.validate(domain)


def test_validate_rejects_orphan_transition_target() -> None:
    domain = _minimal_domain(
        transitions={
            "START": ["DONE", "GHOST"],  # GHOST does not exist in stages
            "DONE":  [],
        }
    )
    with pytest.raises(DomainValidationError, match="unknown stage"):
        DomainDefinitionLoader.validate(domain)


def test_validate_rejects_orphan_transition_source() -> None:
    domain = _minimal_domain(
        transitions={
            "START": ["DONE"],
            "DONE":  [],
            "GHOST": ["START"],  # GHOST is not in stages dict
        }
    )
    with pytest.raises(DomainValidationError, match="Transition from unknown stage"):
        DomainDefinitionLoader.validate(domain)


def test_validate_rejects_no_terminal_stages() -> None:
    domain = _minimal_domain(
        stages={
            "START": StageSpec(stage_code="START", display_name="Start"),
            "LOOP":  StageSpec(stage_code="LOOP",  display_name="Loop"),
        },
        transitions={"START": ["LOOP"], "LOOP": ["START"]},
    )
    with pytest.raises(DomainValidationError, match="no terminal stages"):
        DomainDefinitionLoader.validate(domain)


def test_validate_rejects_unreachable_terminal() -> None:
    # DONE is terminal but not reachable from START
    domain = _minimal_domain(
        stages={
            "START": StageSpec(stage_code="START", display_name="Start"),
            "STUCK": StageSpec(stage_code="STUCK", display_name="Stuck"),
            "DONE":  StageSpec(stage_code="DONE",  display_name="Done",  is_terminal=True),
        },
        transitions={
            "START": ["STUCK"],
            "STUCK": [],
            "DONE":  [],
        },
    )
    with pytest.raises(DomainValidationError, match="not reachable"):
        DomainDefinitionLoader.validate(domain)


def test_validate_rejects_sla_referencing_undefined_stage() -> None:
    sla = SLASpec(
        stage_code="NONEXISTENT",
        window_hours=24.0,
        warning_pct=70,
        escalation_pct=100,
        warning_task_type="send_notification",
        escalation_task_type="send_escalation_alert",
        escalation_target_agent="notification",
    )
    domain = _minimal_domain(slas=[sla])
    with pytest.raises(DomainValidationError, match="undefined stage"):
        DomainDefinitionLoader.validate(domain)


def test_validate_rejects_sla_with_bad_pcts_direct() -> None:
    """validate() catches warning_pct >= escalation_pct for SLAs injected after
    construction (bypassing Pydantic's field-level validation)."""
    bad_sla = SLASpec.model_construct(
        stage_code="START",
        window_hours=24.0,
        warning_pct=90,
        escalation_pct=80,
        warning_task_type="t",
        escalation_task_type="t",
        escalation_target_agent="a",
        pause_on_human_review=False,
        is_enabled=True,
        priority_tier=None,
        product_code=None,
    )
    domain = _minimal_domain()
    # Inject the bad SLA after construction, bypassing Pydantic assignment validation
    object.__setattr__(domain, "slas", [bad_sla])
    with pytest.raises(DomainValidationError, match="warning_pct"):
        DomainDefinitionLoader.validate(domain)


# ── Round-trip: wealth domain shape matches the Phase-0 config ────────────────


# Expected transitions from configs/agents/orchestrator.config.json (Phase 0)
_EXPECTED_TRANSITIONS: dict[str, set[str]] = {
    "INTAKE":            {"REVIEW"},
    "REVIEW":            {"SALES_REVIEW", "KYC", "COMPLETE", "ESCALATED"},
    "SALES_REVIEW":      {"KYC", "REVIEW"},
    "KYC":               {"PARALLEL_PRODUCTS", "ESCALATED"},
    "PARALLEL_PRODUCTS": {"REVIEW", "COMPLETE", "ESCALATED"},
    "COMPLETE":          set(),
    "ESCALATED":         {"REVIEW", "KYC", "COMPLETE"},
}

_EXPECTED_STAGES = {"INTAKE", "REVIEW", "SALES_REVIEW", "KYC", "PARALLEL_PRODUCTS", "COMPLETE", "ESCALATED"}
_EXPECTED_TERMINAL = {"COMPLETE", "ESCALATED"}
_EXPECTED_HUMAN_PENDING = {"REVIEW", "SALES_REVIEW"}
_EXPECTED_TASK_ROUTING: dict[str, str] = {
    "INTAKE":            "customer_service",
    "REVIEW":            "collaboration",
    "SALES_REVIEW":      "sales_manager",
    "KYC":               "kyc_compliance",
    "PARALLEL_PRODUCTS": "product_onboarding",
    "COMPLETE":          "notification",
    "ESCALATED":         "notification",
}


def _build_wealth_domain() -> DomainDefinition:
    """Construct the wealth DomainDefinition matching the Phase-0 config (pure Python)."""
    from app.agents.base.a2a_types import AgentID

    stages: dict[str, StageSpec] = {
        "INTAKE":            StageSpec(stage_code="INTAKE",            display_name="Intake"),
        "REVIEW":            StageSpec(stage_code="REVIEW",            display_name="Review",           is_human_pending=True),
        "SALES_REVIEW":      StageSpec(stage_code="SALES_REVIEW",      display_name="Sales Review",     is_human_pending=True),
        "KYC":               StageSpec(stage_code="KYC",               display_name="KYC"),
        "PARALLEL_PRODUCTS": StageSpec(stage_code="PARALLEL_PRODUCTS", display_name="Product Onboarding"),
        "COMPLETE":          StageSpec(stage_code="COMPLETE",          display_name="Complete",         is_terminal=True),
        "ESCALATED":         StageSpec(stage_code="ESCALATED",         display_name="Escalated",        is_terminal=True),
    }
    transitions: dict[str, list[str]] = {
        "INTAKE":            ["REVIEW"],
        "REVIEW":            ["SALES_REVIEW", "KYC", "COMPLETE", "ESCALATED"],
        "SALES_REVIEW":      ["KYC", "REVIEW"],
        "KYC":               ["PARALLEL_PRODUCTS", "ESCALATED"],
        "PARALLEL_PRODUCTS": ["REVIEW", "COMPLETE", "ESCALATED"],
        "COMPLETE":          [],
        "ESCALATED":         ["REVIEW", "KYC", "COMPLETE"],
    }
    task_routing: dict[str, StageActionSpec] = {
        "INTAKE":            StageActionSpec(stage_code="INTAKE",            target_agent="customer_service",   task_type="collect_client_data"),
        "REVIEW":            StageActionSpec(stage_code="REVIEW",            target_agent="collaboration",      task_type="create_collaboration_room"),
        "SALES_REVIEW":      StageActionSpec(stage_code="SALES_REVIEW",      target_agent="sales_manager",      task_type="sales_manager_review"),
        "KYC":               StageActionSpec(stage_code="KYC",               target_agent="kyc_compliance",     task_type="run_kyc_check"),
        "PARALLEL_PRODUCTS": StageActionSpec(stage_code="PARALLEL_PRODUCTS", target_agent="product_onboarding", task_type="onboard_product"),
        "COMPLETE":          StageActionSpec(stage_code="COMPLETE",          target_agent="notification",       task_type="send_notification"),
        "ESCALATED":         StageActionSpec(stage_code="ESCALATED",         target_agent="notification",       task_type="send_escalation_alert", priority="CRITICAL"),
    }
    roster: dict[str, AgentRosterEntry] = {
        agent: AgentRosterEntry(agent_id=agent, agent_class=f"app.agents.{agent}")
        for agent in [a.value for a in AgentID]
    }
    return DomainDefinition(
        domain_id="00000000-0000-0000-0000-000000000099",
        domain_code="wealth_management",
        display_name="Wealth Management",
        is_active=True,
        stages=stages,
        transitions=transitions,
        task_routing=task_routing,
        agent_roster=roster,
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


def test_wealth_domain_stages_match_phase0_config() -> None:
    domain = _build_wealth_domain()
    assert set(domain.stages.keys()) == _EXPECTED_STAGES


def test_wealth_domain_terminal_stages_correct() -> None:
    domain = _build_wealth_domain()
    actual_terminals = {code for code, spec in domain.stages.items() if spec.is_terminal}
    assert actual_terminals == _EXPECTED_TERMINAL


def test_wealth_domain_human_pending_stages_correct() -> None:
    domain = _build_wealth_domain()
    actual_pending = {code for code, spec in domain.stages.items() if spec.is_human_pending}
    assert actual_pending == _EXPECTED_HUMAN_PENDING


def test_wealth_domain_transitions_match_phase0_config() -> None:
    domain = _build_wealth_domain()
    # Compare as sets (order-independent)
    for stage, expected_targets in _EXPECTED_TRANSITIONS.items():
        actual_targets = set(domain.transitions.get(stage, []))
        assert actual_targets == expected_targets, (
            f"Stage {stage!r}: expected transitions {expected_targets}, got {actual_targets}"
        )


def test_wealth_domain_task_routing_agents_match_config() -> None:
    domain = _build_wealth_domain()
    for stage, expected_agent in _EXPECTED_TASK_ROUTING.items():
        routing = domain.task_routing.get(stage)
        assert routing is not None, f"Missing routing for stage {stage!r}"
        assert routing.target_agent == expected_agent, (
            f"Stage {stage!r}: expected agent {expected_agent!r}, got {routing.target_agent!r}"
        )


def test_wealth_domain_validates_clean() -> None:
    domain = _build_wealth_domain()
    DomainDefinitionLoader.validate(domain)  # must not raise


def test_wealth_domain_all_transitions_have_known_targets() -> None:
    domain = _build_wealth_domain()
    stage_codes = set(domain.stages.keys())
    for from_stage, to_stages in domain.transitions.items():
        assert from_stage in stage_codes
        for to_stage in to_stages:
            assert to_stage in stage_codes, f"Unknown target stage {to_stage!r}"
