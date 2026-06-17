"""Seed the wealth management domain from the corrected Phase-0 orchestrator config

Revision ID: 0014_wealth_domain_seed
Revises: 0013_domain_tables
Create Date: 2026-06-11

Populates domain_* tables for the 'wealth_management' domain using the FSM and
routing from configs/agents/orchestrator.config.json (corrected in Phase 0).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014_wealth_domain_seed"
down_revision = "0013_domain_tables"
branch_labels = None
depends_on = None

# ── Deterministic UUIDs for the wealth domain seed ────────────────────────────
# Using gen_random_uuid() at INSERT time; the domain is identified by domain_code.

_WEALTH_CODE = "wealth_management"

# ── Stage data (from orchestrator.config.json fsm.stages) ─────────────────────

_STAGES = [
    {"stage_code": "INTAKE",            "display_name": "Intake",            "is_terminal": False, "is_human_pending": False},
    {"stage_code": "REVIEW",            "display_name": "Compliance Review",  "is_terminal": False, "is_human_pending": True},
    {"stage_code": "SALES_REVIEW",      "display_name": "Sales Manager Review", "is_terminal": False, "is_human_pending": True},
    {"stage_code": "KYC",               "display_name": "KYC / AML Check",   "is_terminal": False, "is_human_pending": False},
    {"stage_code": "PARALLEL_PRODUCTS", "display_name": "Product Onboarding","is_terminal": False, "is_human_pending": False},
    {"stage_code": "COMPLETE",          "display_name": "Complete",           "is_terminal": True,  "is_human_pending": False},
    {"stage_code": "ESCALATED",         "display_name": "Escalated",          "is_terminal": True,  "is_human_pending": False},
]

# ── Transitions (from orchestrator.config.json fsm.transitions) ───────────────

_TRANSITIONS = [
    ("INTAKE",            "REVIEW"),
    ("REVIEW",            "SALES_REVIEW"),
    ("REVIEW",            "KYC"),
    ("REVIEW",            "COMPLETE"),
    ("REVIEW",            "ESCALATED"),
    ("SALES_REVIEW",      "KYC"),
    ("SALES_REVIEW",      "REVIEW"),
    ("KYC",               "PARALLEL_PRODUCTS"),
    ("KYC",               "ESCALATED"),
    ("PARALLEL_PRODUCTS", "REVIEW"),
    ("PARALLEL_PRODUCTS", "COMPLETE"),
    ("PARALLEL_PRODUCTS", "ESCALATED"),
    ("ESCALATED",         "REVIEW"),
    ("ESCALATED",         "KYC"),
    ("ESCALATED",         "COMPLETE"),
]

# ── Task routing (task_routing + resume_routing from orchestrator.config.json) ─
# Each entry: (stage_code, target_agent, task_type, priority)

_TASK_ROUTING = [
    ("INTAKE",            "customer_service",   "collect_client_data",  "NORMAL"),
    ("REVIEW",            "collaboration",      "create_collaboration_room", "HIGH"),
    ("SALES_REVIEW",      "sales_manager",      "sales_manager_review", "HIGH"),
    ("KYC",               "kyc_compliance",     "run_kyc_check",        "HIGH"),
    ("PARALLEL_PRODUCTS", "product_onboarding", "onboard_product",      "NORMAL"),
    ("COMPLETE",          "notification",       "send_notification",    "NORMAL"),
    ("ESCALATED",         "notification",       "send_escalation_alert","CRITICAL"),
]

# ── Agent roster (all 9 wealth-domain agents) ─────────────────────────────────

_AGENTS = [
    ("orchestrator",          "app.agents.orchestrator.orchestrator_agent.OrchestratorAgent"),
    ("customer_service",      "app.agents.customer_service.customer_service_agent.CustomerServiceAgent"),
    ("kyc_compliance",        "app.agents.kyc_compliance.kyc_compliance_agent.KYCComplianceAgent"),
    ("document_intelligence", "app.agents.document_intelligence.document_intelligence_agent.DocumentIntelligenceAgent"),
    ("product_onboarding",    "app.agents.product_onboarding.product_onboarding_agent.ProductOnboardingAgent"),
    ("collaboration",         "app.agents.collaboration.collaboration_agent.CollaborationAgent"),
    ("contact_centre",        "app.agents.contact_centre.contact_centre_agent.ContactCentreAgent"),
    ("notification",          "app.agents.notification.notification_agent.NotificationAgent"),
    ("sales_manager",         "app.agents.sales_manager.sales_manager_agent.SalesManagerAgent"),
]

# ── Agent capabilities (subscribed / emitted task types per agent) ─────────────

_CAPABILITIES = {
    "orchestrator": {
        "subscribed": ["start_onboarding", "resume_onboarding", "advance_stage", "escalate", "health_check"],
        "emitted":    ["collect_client_data", "run_kyc_check", "onboard_product", "sales_manager_review",
                       "create_collaboration_room", "send_notification", "send_escalation_alert"],
        "handoffs":   ["customer_service", "kyc_compliance", "product_onboarding", "sales_manager",
                       "collaboration", "notification"],
    },
    "customer_service": {
        "subscribed": ["collect_client_data", "continue_conversation"],
        "emitted":    ["advance_stage"],
        "handoffs":   ["orchestrator"],
    },
    "kyc_compliance": {
        "subscribed": ["run_kyc_check", "verify_identity"],
        "emitted":    ["advance_stage", "escalate", "classify_document", "validate_document"],
        "handoffs":   ["orchestrator", "document_intelligence"],
    },
    "document_intelligence": {
        "subscribed": ["classify_document", "validate_document", "extract_ocr", "compute_diff"],
        "emitted":    ["advance_stage"],
        "handoffs":   ["orchestrator", "kyc_compliance"],
    },
    "product_onboarding": {
        "subscribed": ["onboard_product", "assess_suitability", "product_track_complete"],
        "emitted":    ["advance_stage", "send_notification"],
        "handoffs":   ["orchestrator", "notification"],
    },
    "collaboration": {
        "subscribed": ["create_collaboration_room", "add_comment"],
        "emitted":    ["advance_stage"],
        "handoffs":   ["orchestrator"],
    },
    "contact_centre": {
        "subscribed": ["summarise_call", "get_client_status"],
        "emitted":    [],
        "handoffs":   [],
    },
    "notification": {
        "subscribed": ["send_notification", "send_escalation_alert"],
        "emitted":    [],
        "handoffs":   [],
    },
    "sales_manager": {
        "subscribed": ["sales_manager_review", "sales_manager_decide"],
        "emitted":    ["advance_stage"],
        "handoffs":   ["orchestrator"],
    },
}

# ── Personas (existing users.role values expressed as domain_personas rows) ────

_PERSONAS = [
    {
        "persona_code": "advisor",
        "display_label": "Financial Advisor",
        "color": "#3B82F6",
        "default_route": "/advisor/cases",
        "nav_links": [
            {"label": "Cases", "href": "/advisor/cases"},
            {"label": "Clients", "href": "/advisor/clients"},
        ],
    },
    {
        "persona_code": "admin",
        "display_label": "Administrator",
        "color": "#8B5CF6",
        "default_route": "/admin",
        "nav_links": [
            {"label": "Cases", "href": "/advisor/cases"},
            {"label": "Admin", "href": "/admin"},
        ],
    },
    {
        "persona_code": "sales_manager",
        "display_label": "Sales Manager",
        "color": "#F59E0B",
        "default_route": "/advisor/cases",
        "nav_links": [
            {"label": "Cases", "href": "/advisor/cases"},
            {"label": "Sales Review", "href": "/advisor/cases?stage=SALES_REVIEW"},
        ],
    },
    {
        "persona_code": "client",
        "display_label": "Client",
        "color": "#10B981",
        "default_route": "/client/portal",
        "nav_links": [
            {"label": "My Application", "href": "/client/portal"},
        ],
    },
]

# ── Permissions (minimal bootstrap; Phase 7 will replace require_role guards) ─

_PERMISSIONS = {
    "advisor":       ["case:read", "case:create", "case:approve", "review:read",
                      "document:upload", "document:validate"],
    "admin":         ["case:read", "case:create", "case:approve", "review:read",
                      "review:approve", "review:escalate", "compliance:read",
                      "compliance:decide", "audit:read", "audit:export",
                      "document:upload", "document:validate", "admin:config"],
    "sales_manager": ["case:read", "review:read", "sales:review", "sales:decide"],
    "client":        ["document:upload"],
}

# ── Products (from migration 0011_institutional_products_seed) ────────────────

_PRODUCTS = [
    {"product_code": "gcf", "display_name": "Global Credit Fund",         "product_type": "institutional"},
    {"product_code": "ecm", "display_name": "Equity Capital Markets",     "product_type": "institutional"},
    {"product_code": "dcm", "display_name": "Debt Capital Markets",       "product_type": "institutional"},
    {"product_code": "tfe", "display_name": "Trade Finance & Escrow",     "product_type": "institutional"},
]

# ── Display config (stage labels mirroring frontend STAGE_LABELS) ─────────────

_DISPLAY_CONFIG = [
    {"entity_type": "stage", "entity_code": "INTAKE",            "label": "Intake",              "color": "#6B7280"},
    {"entity_type": "stage", "entity_code": "REVIEW",            "label": "Review",              "color": "#F59E0B"},
    {"entity_type": "stage", "entity_code": "SALES_REVIEW",      "label": "Sales Review",        "color": "#8B5CF6"},
    {"entity_type": "stage", "entity_code": "KYC",               "label": "KYC",                 "color": "#3B82F6"},
    {"entity_type": "stage", "entity_code": "PARALLEL_PRODUCTS", "label": "Product Onboarding",  "color": "#10B981"},
    {"entity_type": "stage", "entity_code": "COMPLETE",          "label": "Complete",            "color": "#059669"},
    {"entity_type": "stage", "entity_code": "ESCALATED",         "label": "Escalated",           "color": "#EF4444"},
    {"entity_type": "persona", "entity_code": "advisor",       "label": "Advisor",       "color": "#3B82F6"},
    {"entity_type": "persona", "entity_code": "admin",         "label": "Admin",         "color": "#8B5CF6"},
    {"entity_type": "persona", "entity_code": "sales_manager", "label": "Sales Manager", "color": "#F59E0B"},
    {"entity_type": "persona", "entity_code": "client",        "label": "Client",        "color": "#10B981"},
]


def upgrade() -> None:
    conn = op.get_bind()

    # ── Insert domain row ──────────────────────────────────────────────────────
    conn.execute(sa.text(
        "INSERT INTO domains (domain_code, display_name, is_active) "
        "VALUES (:code, :name, true)"
    ), {"code": _WEALTH_CODE, "name": "Wealth Management"})

    # Retrieve the generated id for FK references
    domain_id = conn.execute(sa.text(
        "SELECT id FROM domains WHERE domain_code = :code"
    ), {"code": _WEALTH_CODE}).scalar()

    # ── Stages ────────────────────────────────────────────────────────────────
    for s in _STAGES:
        conn.execute(sa.text(
            "INSERT INTO domain_stages (domain_id, stage_code, display_name, is_terminal, is_human_pending) "
            "VALUES (:domain_id, :stage_code, :display_name, :is_terminal, :is_human_pending)"
        ), {**s, "domain_id": domain_id})

    # ── Transitions ───────────────────────────────────────────────────────────
    for from_s, to_s in _TRANSITIONS:
        conn.execute(sa.text(
            "INSERT INTO domain_transitions (domain_id, from_stage, to_stage) "
            "VALUES (:domain_id, :from_stage, :to_stage)"
        ), {"domain_id": domain_id, "from_stage": from_s, "to_stage": to_s})

    # ── Task routing ──────────────────────────────────────────────────────────
    for stage_code, target_agent, task_type, priority in _TASK_ROUTING:
        conn.execute(sa.text(
            "INSERT INTO domain_task_routing "
            "(domain_id, stage_code, target_agent, task_type, priority) "
            "VALUES (:domain_id, :stage_code, :target_agent, :task_type, :priority)"
        ), {"domain_id": domain_id, "stage_code": stage_code,
            "target_agent": target_agent, "task_type": task_type, "priority": priority})

    # ── Agent roster ──────────────────────────────────────────────────────────
    for agent_id, agent_class in _AGENTS:
        conn.execute(sa.text(
            "INSERT INTO domain_agent_roster (domain_id, agent_id, agent_class) "
            "VALUES (:domain_id, :agent_id, :agent_class)"
        ), {"domain_id": domain_id, "agent_id": agent_id, "agent_class": agent_class})

    # ── Agent capabilities ────────────────────────────────────────────────────
    import json
    for agent_id, caps in _CAPABILITIES.items():
        conn.execute(sa.text(
            "INSERT INTO domain_agent_capabilities "
            "(domain_id, agent_id, subscribed_task_types, emitted_task_types, allowed_handoff_targets) "
            "VALUES (:domain_id, :agent_id, :subscribed, :emitted, :handoffs)"
        ), {
            "domain_id": domain_id,
            "agent_id": agent_id,
            "subscribed": caps["subscribed"],
            "emitted": caps["emitted"],
            "handoffs": caps["handoffs"],
        })

    # ── Personas ──────────────────────────────────────────────────────────────
    for p in _PERSONAS:
        conn.execute(sa.text(
            "INSERT INTO domain_personas "
            "(domain_id, persona_code, display_label, color, default_route, nav_links) "
            "VALUES (:domain_id, :persona_code, :display_label, :color, :default_route, "
            "        CAST(:nav_links AS jsonb))"
        ), {
            "domain_id": domain_id,
            "persona_code": p["persona_code"],
            "display_label": p["display_label"],
            "color": p["color"],
            "default_route": p["default_route"],
            "nav_links": json.dumps(p["nav_links"]),
        })

    # ── Permissions ───────────────────────────────────────────────────────────
    for persona_code, scopes in _PERMISSIONS.items():
        for scope in scopes:
            conn.execute(sa.text(
                "INSERT INTO domain_permissions (domain_id, persona_code, permission_scope) "
                "VALUES (:domain_id, :persona_code, :scope)"
            ), {"domain_id": domain_id, "persona_code": persona_code, "scope": scope})

    # ── Products ──────────────────────────────────────────────────────────────
    for p in _PRODUCTS:
        conn.execute(sa.text(
            "INSERT INTO domain_products "
            "(domain_id, product_code, display_name, product_type, is_active) "
            "VALUES (:domain_id, :product_code, :display_name, :product_type, true)"
        ), {"domain_id": domain_id, **p})

    # ── Display config ────────────────────────────────────────────────────────
    for d in _DISPLAY_CONFIG:
        conn.execute(sa.text(
            "INSERT INTO domain_display_config "
            "(domain_id, entity_type, entity_code, label, color) "
            "VALUES (:domain_id, :entity_type, :entity_code, :label, :color)"
        ), {"domain_id": domain_id, **d})


def downgrade() -> None:
    op.execute(sa.text(
        "DELETE FROM domains WHERE domain_code = :code"
    ), {"code": _WEALTH_CODE})
    # CASCADE delete removes all domain_* child rows automatically.
