"""
Phase 0.5 snapshot tests — assert Temporal workflow structure without
starting a Temporal server.

Tests that import from onboarding_workflow.py call pytest.importorskip("temporalio")
so they are skipped gracefully in envs without the SDK installed.
LangGraph graph tests similarly skip if langgraph is absent.
"""
import inspect

import pytest


# ── 1. a2a_types type contracts (no Temporal dependency) ─────────────────────


def test_onboarding_state_dict_importable() -> None:
    from app.agents.base.a2a_types import OnboardingStateDict

    required_keys = {
        "case_id", "client_id", "stage", "selected_products",
        "product_tracks", "kyc_status", "kyc_risk_score",
        "sales_review_id", "sales_review_decision", "escalation_reason",
        "human_review_id", "version", "created_at", "updated_at",
    }
    missing = required_keys - OnboardingStateDict.__annotations__.keys()
    assert not missing, f"OnboardingStateDict missing fields: {missing}"


def test_signal_models_importable() -> None:
    from app.agents.base.a2a_types import (
        HumanReviewSignal,
        OnboardingWorkflowInput,
        OnboardingWorkflowResult,
        StageAdvanceSignal,
    )

    assert "to_stage" in StageAdvanceSignal.model_fields
    assert "payload" in StageAdvanceSignal.model_fields
    assert "decision" in HumanReviewSignal.model_fields
    assert "reviewer_id" in HumanReviewSignal.model_fields
    assert "case_id" in OnboardingWorkflowInput.model_fields
    assert "client_id" in OnboardingWorkflowInput.model_fields
    assert "final_stage" in OnboardingWorkflowResult.model_fields
    assert "case_id" in OnboardingWorkflowResult.model_fields


# ── 2. Activity registry (requires temporalio) ───────────────────────────────

_EXPECTED_ACTIVITY_NAMES = {
    "initialize_case_activity",
    "customer_service_kickoff_activity",
    "kyc_compliance_activity",
    "product_onboarding_activity",
    "sales_manager_kickoff_activity",
    "collaboration_kickoff_activity",
    "notification_activity",
    "escalation_alert_activity",
    "completion_activity",
    "persist_stage_activity",
    "_contact_centre_summary_activity",
}


def test_all_activities_returns_expected_set() -> None:
    pytest.importorskip("temporalio")
    from app.workflows.onboarding_workflow import get_all_activities

    activities = get_all_activities()
    defn_names: set[str] = set()
    for fn in activities:
        defn = getattr(fn, "_defn", None)
        if defn is not None:
            defn_names.add(defn.name)
        else:
            defn_names.add(getattr(fn, "__wrapped__", fn).__name__)

    missing = _EXPECTED_ACTIVITY_NAMES - defn_names
    assert not missing, f"get_all_activities() missing: {missing}"


def test_activity_functions_are_coroutines() -> None:
    pytest.importorskip("temporalio")
    from app.workflows.onboarding_workflow import (
        collaboration_kickoff_activity,
        completion_activity,
        customer_service_kickoff_activity,
        escalation_alert_activity,
        initialize_case_activity,
        kyc_compliance_activity,
        notification_activity,
        persist_stage_activity,
        product_onboarding_activity,
        sales_manager_kickoff_activity,
    )

    for fn in [
        initialize_case_activity,
        customer_service_kickoff_activity,
        kyc_compliance_activity,
        product_onboarding_activity,
        sales_manager_kickoff_activity,
        collaboration_kickoff_activity,
        notification_activity,
        escalation_alert_activity,
        completion_activity,
        persist_stage_activity,
    ]:
        underlying = getattr(fn, "__wrapped__", fn)
        assert inspect.iscoroutinefunction(underlying), (
            f"{fn} must be a coroutine function"
        )


# ── 3. Workflow class structure (requires temporalio) ────────────────────────


def test_workflow_classes_importable() -> None:
    pytest.importorskip("temporalio")
    from app.workflows.onboarding_workflow import (
        OnboardingWorkflow,
        ProductOnboardingWorkflow,
    )

    assert inspect.isclass(OnboardingWorkflow)
    assert inspect.isclass(ProductOnboardingWorkflow)


def test_onboarding_workflow_has_signal_handlers() -> None:
    pytest.importorskip("temporalio")
    from app.workflows.onboarding_workflow import OnboardingWorkflow

    assert hasattr(OnboardingWorkflow, "advance_stage"), (
        "OnboardingWorkflow must expose an advance_stage signal handler"
    )
    assert hasattr(OnboardingWorkflow, "human_review_completed"), (
        "OnboardingWorkflow must expose a human_review_completed signal handler"
    )


def test_product_workflow_run_is_coroutine() -> None:
    pytest.importorskip("temporalio")
    from app.workflows.onboarding_workflow import ProductOnboardingWorkflow

    assert hasattr(ProductOnboardingWorkflow, "run")
    assert inspect.iscoroutinefunction(ProductOnboardingWorkflow.run)


# ── 4. LangGraph graph builders (requires langgraph) ─────────────────────────


def test_agent_graph_builders_importable() -> None:
    pytest.importorskip("langgraph")
    from app.agents.collaboration.graph import build_collaboration_graph
    from app.agents.contact_centre.graph import build_contact_centre_graph
    from app.agents.customer_service.graph import build_customer_service_kickoff_graph
    from app.agents.document_intelligence.graph import build_document_intelligence_graph
    from app.agents.kyc_compliance.graph import build_kyc_graph
    from app.agents.notification.graph import (
        build_escalation_alert_graph,
        build_notification_graph,
    )
    from app.agents.product_onboarding.graph import build_product_onboarding_graph
    from app.agents.sales_manager.graph import build_sales_manager_kickoff_graph

    for builder in [
        build_kyc_graph,
        build_customer_service_kickoff_graph,
        build_notification_graph,
        build_escalation_alert_graph,
        build_product_onboarding_graph,
        build_collaboration_graph,
        build_contact_centre_graph,
        build_sales_manager_kickoff_graph,
        build_document_intelligence_graph,
    ]:
        assert callable(builder), f"{builder} must be callable"


def test_agent_graphs_compile_without_error() -> None:
    pytest.importorskip("langgraph")
    from app.agents.collaboration.graph import build_collaboration_graph
    from app.agents.customer_service.graph import build_customer_service_kickoff_graph
    from app.agents.kyc_compliance.graph import build_kyc_graph
    from app.agents.notification.graph import (
        build_escalation_alert_graph,
        build_notification_graph,
    )
    from app.agents.product_onboarding.graph import build_product_onboarding_graph
    from app.agents.sales_manager.graph import build_sales_manager_kickoff_graph

    for builder in [
        build_kyc_graph,
        build_customer_service_kickoff_graph,
        build_notification_graph,
        build_escalation_alert_graph,
        build_product_onboarding_graph,
        build_collaboration_graph,
        build_sales_manager_kickoff_graph,
    ]:
        graph = builder()
        assert graph is not None, f"{builder.__name__} returned None"
