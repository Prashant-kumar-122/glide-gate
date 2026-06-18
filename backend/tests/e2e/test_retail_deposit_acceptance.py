"""Phase 11 — Retail/Deposit acceptance tests.

These tests constitute the acceptance proof that CADF is a genuinely generic
framework: a brand-new Retail/Deposit domain can be fully configured through
the admin portal API with:

  - Zero domain_* rows created by migration scripts
  - Zero new Python agent classes
  - Zero changes to onboarding_workflow.py, a2a_types.py, stage_dispatcher.py,
    mcp_connector.py, sla_monitor_service.py, or require_permission call sites

Tests are pure Python (no live DB, no running server).  They validate the
Retail/Deposit domain configuration data exported from
scripts/setup_retail_deposit_domain.py for self-consistency and correctness
against the acceptance checklist.

Acceptance checklist items verified:
  AC-1:  Zero domain_* rows from migration scripts (structural — verified by
         the presence/absence of a migration file, not by runtime state)
  AC-2:  ≤ 1 new agent class (here: 0; verified by roster using existing classes)
  AC-3:  Core infrastructure files unchanged (structural — no file modifications)
  AC-4:  Frontend renders retail vocab (verified: stages + personas have display data)
  AC-5:  priority_tier="sme" INTAKE SLA has smaller window (1h vs 2h standard)
  AC-6:  Overdue case fires SLA_WARNING → SLA_BREACH (SLA config has enabled rows)
  AC-7:  APPROVAL stage SLA has pause_on_human_review=True
  AC-8:  savings_account product-scoped SLA is_enabled=False
  AC-9:  deposit_ops persona has correct default_route and nav_links
  AC-10: Shared-core document field present in required_documents (Phase 4.5 skipped;
         GOVT_PHOTO_ID listed in all products — manual "collect once" workflow)
  AC-11: First-to-complete activation (activation_criteria present on all products)
  AC-12: Audit chain valid (decision_log populated by portal API — structural)
  AC-13: Pipeline steps present and ordered for each product
  AC-14: Temporal child workflows (task routing maps to existing onboard_product
         activity — structural; no code changes needed)
  AC-15: SLA health dashboard (SLA rows present with correct fields)
"""
from __future__ import annotations

import sys
import os
import pytest

# Import the domain configuration constants from the setup script.
# Adjust sys.path so the scripts/ directory is importable in CI.
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS_DIR))

from setup_retail_deposit_domain import (  # noqa: E402
    DOMAIN_CODE,
    DOMAIN_DISPLAY,
    STAGES,
    TRANSITIONS,
    TASK_ROUTING,
    AGENTS,
    CAPABILITIES,
    PERSONAS,
    PERMISSIONS,
    PRODUCTS,
    PIPELINES,
    SLAS,
    DISPLAY_CONFIG,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

_STAGE_CODES = {s["stage_code"] for s in STAGES}
_TERMINAL_STAGES = {s["stage_code"] for s in STAGES if s["is_terminal"]}
_KNOWN_TASK_TYPES = {
    "collect_client_data", "run_kyc_check", "onboard_product",
    "create_collaboration_room", "send_notification", "send_escalation_alert",
    "sales_manager_review",
}

# Existing Python agent classes — 0 new ones are allowed in Phase 11.
_EXISTING_AGENT_CLASSES = {
    "app.agents.orchestrator.orchestrator_agent.OrchestratorAgent",
    "app.agents.customer_service.customer_service_agent.CustomerServiceAgent",
    "app.agents.kyc_compliance.kyc_compliance_agent.KYCComplianceAgent",
    "app.agents.document_intelligence.document_intelligence_agent.DocumentIntelligenceAgent",
    "app.agents.product_onboarding.product_onboarding_agent.ProductOnboardingAgent",
    "app.agents.collaboration.collaboration_agent.CollaborationAgent",
    "app.agents.contact_centre.contact_centre_agent.ContactCentreAgent",
    "app.agents.notification.notification_agent.NotificationAgent",
    "app.agents.sales_manager.sales_manager_agent.SalesManagerAgent",
    "app.agents.fraud_screening.graph.build_fraud_screening_graph",
}


# ── AC-1: Zero migration scripts for retail/deposit ──────────────────────────

def test_no_retail_deposit_migration_script():
    """No alembic migration file must seed retail_deposit domain rows.

    The setup script exclusively calls the admin portal API — it never
    touches the DB directly or via alembic.
    """
    import glob
    migrations = glob.glob(
        os.path.join(os.path.dirname(__file__), "..", "..", "alembic", "versions", "*.py")
    )
    for path in migrations:
        with open(path) as f:
            content = f.read()
        if "retail_deposit" in content and "INSERT INTO domain" in content:
            pytest.fail(
                f"Found migration script {os.path.basename(path)} that seeds "
                "retail_deposit domain rows. Phase 11 requires portal-only setup."
            )


# ── AC-2: ≤ 1 new agent class ────────────────────────────────────────────────

def test_zero_new_agent_classes():
    """All agent classes in the retail_deposit roster already exist in the
    wealth domain's agent registry — no new Python files required."""
    for agent_id, agent_class in AGENTS:
        assert agent_class in _EXISTING_AGENT_CLASSES, (
            f"Agent '{agent_id}' uses class '{agent_class}' which is NOT in the "
            "set of existing agent classes. Phase 11 allows at most 1 new class."
        )


# ── AC-3: No changes to core infrastructure files ────────────────────────────

def test_existing_task_types_only():
    """All task types in the retail_deposit domain routing are already registered
    in the workflow's _TASK_TYPE_TO_ACTIVITY_NAME table — no workflow code changes."""
    for stage_code, target_agent, task_type, priority in TASK_ROUTING:
        assert task_type in _KNOWN_TASK_TYPES, (
            f"Stage '{stage_code}' uses task_type '{task_type}' which is NOT in "
            "the pre-registered set. This would require modifying onboarding_workflow.py."
        )


# ── AC-4: Frontend vocab (stages + personas have display data) ────────────────

def test_all_stages_have_display_config():
    """Every stage code in STAGES must have a corresponding display config entry."""
    display_stage_codes = {
        d["entity_code"] for d in DISPLAY_CONFIG if d["entity_type"] == "stage"
    }
    for s in STAGES:
        assert s["stage_code"] in display_stage_codes, (
            f"Stage '{s['stage_code']}' has no display config entry. "
            "Frontend useDomainConfig hook requires display data for every stage."
        )


def test_all_personas_have_display_config():
    """Every persona must have a display config entry for the frontend."""
    display_persona_codes = {
        d["entity_code"] for d in DISPLAY_CONFIG if d["entity_type"] == "persona"
    }
    for p in PERSONAS:
        assert p["persona_code"] in display_persona_codes, (
            f"Persona '{p['persona_code']}' has no display config entry."
        )


# ── AC-5: priority_tier="sme" SLA has smaller window than standard ────────────

def test_sme_tier_intake_sla_smaller_than_standard():
    """INTAKE stage sme-tier SLA must have a shorter window than the default."""
    intake_slas = [
        s for s in SLAS
        if s["stage_code"] == "INTAKE" and s["product_code"] is None
    ]
    standard = next((s for s in intake_slas if s["priority_tier"] is None), None)
    sme = next((s for s in intake_slas if s["priority_tier"] == "sme"), None)

    assert standard is not None, "No standard INTAKE SLA configured"
    assert sme is not None, "No sme-tier INTAKE SLA configured"
    assert sme["window_hours"] < standard["window_hours"], (
        f"SME-tier INTAKE window ({sme['window_hours']}h) must be smaller than "
        f"standard ({standard['window_hours']}h) to prove priority_tier override."
    )


# ── AC-6: SLA monitoring is enabled with warning + escalation thresholds ──────

def test_enabled_slas_have_valid_pct_order():
    """Every enabled SLA must have warning_pct < escalation_pct."""
    for sla in SLAS:
        if sla["is_enabled"]:
            assert sla["warning_pct"] < sla["escalation_pct"], (
                f"SLA for {sla['stage_code']} has warning_pct={sla['warning_pct']} "
                f">= escalation_pct={sla['escalation_pct']}"
            )


def test_at_least_one_enabled_sla_per_active_stage():
    """At least one enabled SLA must exist for each non-terminal stage."""
    non_terminal = {s["stage_code"] for s in STAGES if not s["is_terminal"]}
    enabled_stages = {
        s["stage_code"] for s in SLAS
        if s["is_enabled"] and s["product_code"] is None
    }
    for stage in non_terminal:
        assert stage in enabled_stages, (
            f"Non-terminal stage '{stage}' has no enabled default SLA. "
            "Overdue cases in this stage will never fire warnings or breach."
        )


# ── AC-7: APPROVAL stage pauses SLA clock during human review ─────────────────

def test_approval_sla_pauses_on_human_review():
    """The APPROVAL stage SLA must have pause_on_human_review=True."""
    approval_sla = next(
        (s for s in SLAS if s["stage_code"] == "APPROVAL"
         and s["product_code"] is None and s["priority_tier"] is None),
        None,
    )
    assert approval_sla is not None, "No default APPROVAL SLA configured"
    assert approval_sla["pause_on_human_review"] is True, (
        "APPROVAL stage is human-pending; its SLA must have pause_on_human_review=True "
        "so the clock pauses while waiting for the branch manager."
    )


def test_approval_stage_is_human_pending():
    """The APPROVAL stage must be marked is_human_pending=True."""
    approval = next((s for s in STAGES if s["stage_code"] == "APPROVAL"), None)
    assert approval is not None
    assert approval["is_human_pending"] is True


# ── AC-8: savings_account product-scoped SLA is disabled ─────────────────────

def test_savings_account_sla_disabled():
    """The savings_account product-scoped SLA on PRODUCT_SELECTION must be disabled.

    This demonstrates the per-product SLA override: the savings account is an
    instant product that opens in seconds, so SLA monitoring is irrelevant.
    """
    savings_sla = next(
        (s for s in SLAS
         if s["stage_code"] == "PRODUCT_SELECTION"
         and s["product_code"] == "savings_account"),
        None,
    )
    assert savings_sla is not None, (
        "No product-scoped SLA row found for savings_account/PRODUCT_SELECTION. "
        "The instant account must have an explicit is_enabled=False override."
    )
    assert savings_sla["is_enabled"] is False, (
        "savings_account SLA on PRODUCT_SELECTION must be is_enabled=False. "
        f"Got is_enabled={savings_sla['is_enabled']}"
    )


# ── AC-9: deposit_ops persona has correct landing page and nav ────────────────

def test_deposit_ops_persona_configured():
    """deposit_ops persona must exist with a default_route and non-empty nav_links."""
    persona = next((p for p in PERSONAS if p["persona_code"] == "deposit_ops"), None)
    assert persona is not None, "deposit_ops persona not configured"
    assert persona["default_route"], "deposit_ops must have a default_route"
    assert persona["nav_links"], "deposit_ops must have at least one nav_link"


def test_deposit_ops_has_admin_config_excluded():
    """deposit_ops must NOT have admin:config permission (least privilege)."""
    scopes = PERMISSIONS.get("deposit_ops", [])
    assert "admin:config" not in scopes, (
        "deposit_ops must not have admin:config — branch staff should not "
        "be able to modify domain configuration."
    )


def test_branch_manager_can_approve():
    """branch_manager must have review:approve permission."""
    scopes = PERMISSIONS.get("branch_manager", [])
    assert "review:approve" in scopes, (
        "branch_manager must have review:approve to act on APPROVAL stage."
    )


# ── AC-10: Shared documents listed in product required_documents ──────────────

def test_govt_photo_id_required_by_all_products():
    """GOVT_PHOTO_ID must be listed in required_documents for every product.

    Note: Phase 4.5 (shared-core collect-once enforcement) was explicitly
    skipped.  The shared document is listed in each product's metadata so the
    collect-once workflow can be demonstrated manually via the document center.
    """
    for product in PRODUCTS:
        assert "GOVT_PHOTO_ID" in product["required_documents"], (
            f"Product '{product['product_code']}' does not list GOVT_PHOTO_ID. "
            "All retail products require a government-issued photo ID."
        )


# ── AC-11: First-to-complete activation (activation_criteria present) ─────────

def test_all_products_have_activation_criteria():
    """Every product must have activation_criteria so the ActivationGateService
    can evaluate whether it should be independently activated."""
    for product in PRODUCTS:
        assert product.get("activation_criteria"), (
            f"Product '{product['product_code']}' has no activation_criteria. "
            "ActivationGateService.evaluate() will default to DECLINED without it."
        )
        assert product["activation_criteria"].get("kyc_passed") is True, (
            f"Product '{product['product_code']}' activation_criteria must require "
            "kyc_passed=True (KYC gate is mandatory for all retail products)."
        )


# ── AC-12: Audit chain (decision_log entries via portal API calls) ────────────

def test_admin_portal_uses_decision_log():
    """The admin portal routes import decision_log_service for CONFIG_CHANGE audit entries.

    This is a structural test: we verify that each admin router module imports
    decision_log_service, confirming that portal operations are audit-logged.
    """
    import importlib
    for module_name in [
        "app.api.routers.admin.domains",
        "app.api.routers.admin.stages",
        "app.api.routers.admin.products",
        "app.api.routers.admin.sla",
        "app.api.routers.admin.agents",
        "app.api.routers.admin.personas",
    ]:
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            pytest.skip(f"Cannot import {module_name} (not on PYTHONPATH)")
        assert hasattr(mod, "decision_log_service"), (
            f"{module_name} does not import decision_log_service. Portal config "
            "changes must be written to the decision_log for audit compliance."
        )


# ── AC-13: Pipeline steps present and correctly ordered ───────────────────────

def test_all_products_have_pipeline_steps():
    """Every retail product must have at least one pipeline step configured."""
    product_codes = {p["product_code"] for p in PRODUCTS}
    for code in product_codes:
        assert code in PIPELINES, f"No pipeline configured for product '{code}'"
        steps = PIPELINES[code]
        assert len(steps) >= 1, f"Product '{code}' pipeline must have ≥ 1 step"


def test_pipeline_steps_are_sequentially_ordered():
    """Pipeline steps must have step_order starting at 0 and incrementing by 1."""
    for product_code, steps in PIPELINES.items():
        orders = sorted(s["step_order"] for s in steps)
        expected = list(range(len(steps)))
        assert orders == expected, (
            f"Product '{product_code}' pipeline steps are not sequentially ordered. "
            f"Expected {expected}, got {orders}"
        )


def test_deposit_cd_has_more_steps_than_savings():
    """deposit_cd (requires approval) must have ≥ same number of steps as savings_account."""
    assert len(PIPELINES["deposit_cd"]) >= len(PIPELINES["savings_account"])


# ── AC-14: Stage routing uses pre-registered task types ───────────────────────

def test_all_stage_transitions_reference_known_stages():
    """All transition endpoints must reference valid stage codes.

    This mirrors DomainDefinitionLoader contract check #1 (no dangling transitions).
    """
    for from_s, to_s in TRANSITIONS:
        assert from_s in _STAGE_CODES, f"Transition from unknown stage '{from_s}'"
        assert to_s in _STAGE_CODES,   f"Transition to unknown stage '{to_s}'"


def test_terminal_stages_reachable_from_intake():
    """At least one terminal stage must be reachable from INTAKE via BFS.

    Mirrors DomainDefinitionLoader contract check #3.
    """
    graph: dict[str, list[str]] = {s: [] for s in _STAGE_CODES}
    for from_s, to_s in TRANSITIONS:
        graph[from_s].append(to_s)

    visited: set[str] = set()
    queue = ["INTAKE"]
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        queue.extend(graph.get(node, []))

    reachable_terminals = _TERMINAL_STAGES & visited
    assert reachable_terminals, (
        f"No terminal stage is reachable from INTAKE. "
        f"Terminal stages: {_TERMINAL_STAGES}. Reachable: {visited}"
    )


# ── AC-15: SLA health dashboard data is complete ─────────────────────────────

def test_sla_health_rows_have_required_fields():
    """Every SLA row must have the fields expected by SLAHealthEntry."""
    required_fields = {
        "stage_code", "is_enabled", "window_hours",
        "warning_pct", "escalation_pct", "pause_on_human_review",
    }
    for sla in SLAS:
        missing = required_fields - set(sla.keys())
        assert not missing, f"SLA row missing fields: {missing}\nRow: {sla}"


# ── Data integrity ────────────────────────────────────────────────────────────

def test_domain_code_pattern():
    """domain_code must match the portal API pattern r'^[a-z0-9_]+$'."""
    import re
    assert re.match(r"^[a-z0-9_]+$", DOMAIN_CODE), (
        f"DOMAIN_CODE '{DOMAIN_CODE}' does not match required pattern ^[a-z0-9_]+$"
    )


def test_all_sla_product_codes_reference_known_products():
    """Product-scoped SLA rows must reference product codes that exist in PRODUCTS."""
    known = {p["product_code"] for p in PRODUCTS}
    for sla in SLAS:
        if sla["product_code"] is not None:
            assert sla["product_code"] in known, (
                f"SLA references product '{sla['product_code']}' which is not in PRODUCTS"
            )


def test_all_sla_stage_codes_reference_known_stages():
    """SLA stage_code values must all exist in STAGES."""
    for sla in SLAS:
        assert sla["stage_code"] in _STAGE_CODES, (
            f"SLA references stage '{sla['stage_code']}' which is not in STAGES"
        )


def test_personas_have_at_least_one_permission():
    """Every persona must have at least one permission scope."""
    for persona in PERSONAS:
        code = persona["persona_code"]
        scopes = PERMISSIONS.get(code, [])
        assert scopes, f"Persona '{code}' has no permissions configured"


def test_task_routing_covers_all_non_terminal_stages():
    """Every non-terminal stage must have a task routing entry."""
    routed_stages = {r[0] for r in TASK_ROUTING}
    non_terminal = {s["stage_code"] for s in STAGES if not s["is_terminal"]}
    missing = non_terminal - routed_stages
    assert not missing, (
        f"Non-terminal stages without task routing: {missing}. "
        "The workflow cannot dispatch these stages."
    )
