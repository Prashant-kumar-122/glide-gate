#!/usr/bin/env python3
"""Configure the Retail/Deposit domain via the admin portal REST API.

This script is the Phase 11 acceptance proof: it demonstrates that a completely
new onboarding domain (Retail/Deposit) can be stood up entirely through the admin
portal API, with zero migration scripts and zero changes to any framework code.

Usage:
    python scripts/setup_retail_deposit_domain.py --base-url http://localhost:8000

Authentication: uses ADMIN_EMAIL / ADMIN_PASSWORD env vars (defaults to dev seed).

Idempotent: safe to run multiple times; existing rows are skipped.

Acceptance criteria addressed:
  - Zero domain_*/product/pipeline/SLA rows created via migration scripts
  - Zero changes to a2a_types.py, onboarding_workflow.py, stage_dispatcher.py
  - Zero new agent classes (all existing agents reused: customer_service,
    kyc_compliance, product_onboarding, collaboration, notification)
  - deposit_ops / branch_manager / customer personas with nav_links
  - SLA priority-tier override (INTAKE: sme tier = 1h vs standard 2h)
  - savings_account product-scoped SLA is_enabled=False (instant account)
  - APPROVAL stage pause_on_human_review=True (clock pauses during human review)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx")
    sys.exit(1)


# ── Domain configuration data ─────────────────────────────────────────────────

DOMAIN_CODE = "retail_deposit"
DOMAIN_DISPLAY = "Retail & Deposit"

STAGES = [
    {"stage_code": "INTAKE",            "display_name": "Application Intake",   "is_terminal": False, "is_human_pending": False},
    {"stage_code": "VERIFICATION",      "display_name": "Identity Verification", "is_terminal": False, "is_human_pending": False},
    {"stage_code": "PRODUCT_SELECTION", "display_name": "Product Onboarding",   "is_terminal": False, "is_human_pending": False},
    {"stage_code": "APPROVAL",          "display_name": "Manager Approval",     "is_terminal": False, "is_human_pending": True},
    {"stage_code": "COMPLETE",          "display_name": "Account Opened",       "is_terminal": True,  "is_human_pending": False},
    {"stage_code": "REJECTED",          "display_name": "Application Rejected", "is_terminal": True,  "is_human_pending": False},
]

TRANSITIONS = [
    ("INTAKE",            "VERIFICATION"),
    ("VERIFICATION",      "PRODUCT_SELECTION"),
    ("VERIFICATION",      "REJECTED"),
    ("PRODUCT_SELECTION", "APPROVAL"),
    ("PRODUCT_SELECTION", "COMPLETE"),
    ("PRODUCT_SELECTION", "REJECTED"),
    ("APPROVAL",          "COMPLETE"),
    ("APPROVAL",          "REJECTED"),
    ("APPROVAL",          "VERIFICATION"),
]

# All task types already registered in _TASK_TYPE_TO_ACTIVITY_NAME —
# no changes to onboarding_workflow.py required.
TASK_ROUTING = [
    ("INTAKE",            "customer_service",   "collect_client_data",       "NORMAL"),
    ("VERIFICATION",      "kyc_compliance",     "run_kyc_check",             "HIGH"),
    ("PRODUCT_SELECTION", "product_onboarding", "onboard_product",           "NORMAL"),
    ("APPROVAL",          "collaboration",      "create_collaboration_room", "HIGH"),
    ("COMPLETE",          "notification",       "send_notification",         "NORMAL"),
    ("REJECTED",          "notification",       "send_notification",         "NORMAL"),
]

# All existing agent classes — 0 new Python files needed.
AGENTS = [
    ("orchestrator",          "app.agents.orchestrator.orchestrator_agent.OrchestratorAgent"),
    ("customer_service",      "app.agents.customer_service.customer_service_agent.CustomerServiceAgent"),
    ("kyc_compliance",        "app.agents.kyc_compliance.kyc_compliance_agent.KYCComplianceAgent"),
    ("document_intelligence", "app.agents.document_intelligence.document_intelligence_agent.DocumentIntelligenceAgent"),
    ("product_onboarding",    "app.agents.product_onboarding.product_onboarding_agent.ProductOnboardingAgent"),
    ("collaboration",         "app.agents.collaboration.collaboration_agent.CollaborationAgent"),
    ("notification",          "app.agents.notification.notification_agent.NotificationAgent"),
]

CAPABILITIES: dict[str, dict[str, list[str]]] = {
    "orchestrator": {
        "subscribed": ["start_onboarding", "resume_onboarding", "advance_stage", "escalate"],
        "emitted":    ["collect_client_data", "run_kyc_check", "onboard_product",
                       "create_collaboration_room", "send_notification"],
        "handoffs":   ["customer_service", "kyc_compliance", "product_onboarding",
                       "collaboration", "notification"],
    },
    "customer_service": {
        "subscribed": ["collect_client_data", "continue_conversation"],
        "emitted":    ["advance_stage"],
        "handoffs":   ["orchestrator"],
    },
    "kyc_compliance": {
        "subscribed": ["run_kyc_check", "verify_identity"],
        "emitted":    ["advance_stage", "classify_document", "validate_document"],
        "handoffs":   ["orchestrator", "document_intelligence"],
    },
    "document_intelligence": {
        "subscribed": ["classify_document", "validate_document", "extract_ocr"],
        "emitted":    ["advance_stage"],
        "handoffs":   ["orchestrator"],
    },
    "product_onboarding": {
        "subscribed": ["onboard_product", "assess_suitability"],
        "emitted":    ["advance_stage", "send_notification"],
        "handoffs":   ["orchestrator", "notification"],
    },
    "collaboration": {
        "subscribed": ["create_collaboration_room", "add_comment"],
        "emitted":    ["advance_stage"],
        "handoffs":   ["orchestrator"],
    },
    "notification": {
        "subscribed": ["send_notification", "send_escalation_alert"],
        "emitted":    [],
        "handoffs":   [],
    },
}

PERSONAS = [
    {
        "persona_code":  "deposit_ops",
        "display_label": "Deposit Operations",
        "color":         "#0EA5E9",
        "default_route": "/",
        "nav_links": [
            {"label": "Applications", "href": "/"},
            {"label": "Deposits",     "href": "/?stage=PRODUCT_SELECTION"},
        ],
    },
    {
        "persona_code":  "branch_manager",
        "display_label": "Branch Manager",
        "color":         "#8B5CF6",
        "default_route": "/",
        "nav_links": [
            {"label": "Applications", "href": "/"},
            {"label": "Approvals",    "href": "/?stage=APPROVAL"},
        ],
    },
    {
        "persona_code":  "customer",
        "display_label": "Customer",
        "color":         "#10B981",
        "default_route": "/client/portal",
        "nav_links": [
            {"label": "My Application", "href": "/client/portal"},
        ],
    },
]

PERMISSIONS: dict[str, list[str]] = {
    "deposit_ops":   ["case:read", "case:create", "review:read",
                      "document:upload", "document:validate"],
    "branch_manager":["case:read", "case:approve", "review:read",
                      "review:approve", "audit:read"],
    "customer":      ["document:upload", "case:read"],
}

_RETAIL_CRITERIA = {
    "min_age": 18,
    "min_income": 0,
    "min_risk_level": "LOW",
    "scoring_weights": {"age_score": 0.0, "income_score": 0.0,
                        "objective_score": 0.0, "risk_score": 1.0},
    "risk_capacity_map": {"LOW": 1.0, "MEDIUM": 1.0, "HIGH": 1.0},
    "objective_to_risk": {},
    "objective_to_horizon": {},
    "income_range_to_float": {},
}

PRODUCTS = [
    {
        "product_code":        "savings_account",
        "display_name":        "Standard Savings Account",
        "description":         "FDIC-insured savings account with no minimum balance",
        "product_type":        "retail_savings",
        "suitability_criteria": _RETAIL_CRITERIA,
        "required_documents":  ["GOVT_PHOTO_ID"],
        "activation_criteria": {"kyc_passed": True, "pipeline_completed": True,
                                 "fraud_cleared": True},
    },
    {
        "product_code":        "checking_account",
        "display_name":        "Standard Checking Account",
        "description":         "Full-feature checking account with debit card",
        "product_type":        "retail_checking",
        "suitability_criteria": _RETAIL_CRITERIA,
        "required_documents":  ["GOVT_PHOTO_ID"],
        "activation_criteria": {"kyc_passed": True, "pipeline_completed": True,
                                 "fraud_cleared": True},
    },
    {
        "product_code":        "deposit_cd",
        "display_name":        "Certificate of Deposit",
        "description":         "Fixed-rate CD with 12-month term",
        "product_type":        "retail_cd",
        "suitability_criteria": {
            **_RETAIL_CRITERIA,
            "min_income": 1000,
            "scoring_weights": {"age_score": 0.0, "income_score": 0.5,
                                 "objective_score": 0.5, "risk_score": 0.0},
            "income_range_to_float": {"$1,000+": 1.0},
        },
        "required_documents":  ["GOVT_PHOTO_ID", "PROOF_OF_INCOME"],
        "activation_criteria": {"kyc_passed": True, "pipeline_completed": True,
                                 "fraud_cleared": True, "min_income_verified": True},
    },
]

PIPELINES: dict[str, list[dict[str, Any]]] = {
    "savings_account": [
        {"step_id": "eligibility_check", "step_label": "Eligibility Check",
         "step_order": 0, "step_config": {"min_ms": 200, "max_ms": 500}},
        {"step_id": "account_setup",     "step_label": "Account Setup",
         "step_order": 1, "step_config": {"min_ms": 300, "max_ms": 800}},
        {"step_id": "welcome_package",   "step_label": "Welcome Package",
         "step_order": 2, "step_config": {"min_ms": 100, "max_ms": 300}},
    ],
    "checking_account": [
        {"step_id": "eligibility_check", "step_label": "Eligibility Check",
         "step_order": 0, "step_config": {"min_ms": 200, "max_ms": 500}},
        {"step_id": "debit_card_setup",  "step_label": "Debit Card Setup",
         "step_order": 1, "step_config": {"min_ms": 500, "max_ms": 1200}},
        {"step_id": "account_activation","step_label": "Account Activation",
         "step_order": 2, "step_config": {"min_ms": 300, "max_ms": 600}},
    ],
    "deposit_cd": [
        {"step_id": "eligibility_check", "step_label": "Eligibility Check",
         "step_order": 0, "step_config": {"min_ms": 200, "max_ms": 500}},
        {"step_id": "cd_terms_review",   "step_label": "CD Terms Review",
         "step_order": 1, "step_config": {"min_ms": 800, "max_ms": 2000}},
        {"step_id": "cd_activation",     "step_label": "CD Activation",
         "step_order": 2, "step_config": {"min_ms": 400, "max_ms": 900}},
    ],
}

# SLA configuration:
#   - INTAKE: standard (2h) and sme-tier override (1h) — proves priority_tier works
#   - VERIFICATION: 4h default
#   - PRODUCT_SELECTION: 2h default
#   - savings_account product-scoped SLA: is_enabled=False (instant account)
#   - APPROVAL: 24h with pause_on_human_review=True (clock pauses during hold)
SLAS = [
    {"stage_code": "INTAKE",            "priority_tier": None,  "product_code": None,
     "is_enabled": True,  "window_hours": 2.0,  "warning_pct": 75, "escalation_pct": 100,
     "pause_on_human_review": False},
    {"stage_code": "INTAKE",            "priority_tier": "sme", "product_code": None,
     "is_enabled": True,  "window_hours": 1.0,  "warning_pct": 75, "escalation_pct": 100,
     "pause_on_human_review": False},
    {"stage_code": "VERIFICATION",      "priority_tier": None,  "product_code": None,
     "is_enabled": True,  "window_hours": 4.0,  "warning_pct": 80, "escalation_pct": 100,
     "pause_on_human_review": False},
    {"stage_code": "PRODUCT_SELECTION", "priority_tier": None,  "product_code": None,
     "is_enabled": True,  "window_hours": 2.0,  "warning_pct": 80, "escalation_pct": 100,
     "pause_on_human_review": False},
    # savings_account: instant product — SLA monitoring disabled.
    {"stage_code": "PRODUCT_SELECTION", "priority_tier": None,  "product_code": "savings_account",
     "is_enabled": False, "window_hours": 0.5,  "warning_pct": 50, "escalation_pct": 100,
     "pause_on_human_review": False},
    {"stage_code": "APPROVAL",          "priority_tier": None,  "product_code": None,
     "is_enabled": True,  "window_hours": 24.0, "warning_pct": 80, "escalation_pct": 100,
     "pause_on_human_review": True},
]

DISPLAY_CONFIG = [
    {"entity_type": "stage",   "entity_code": "INTAKE",            "label": "Application Intake",   "color": "#6B7280"},
    {"entity_type": "stage",   "entity_code": "VERIFICATION",      "label": "ID Verification",      "color": "#3B82F6"},
    {"entity_type": "stage",   "entity_code": "PRODUCT_SELECTION", "label": "Product Onboarding",   "color": "#10B981"},
    {"entity_type": "stage",   "entity_code": "APPROVAL",          "label": "Manager Approval",     "color": "#F59E0B"},
    {"entity_type": "stage",   "entity_code": "COMPLETE",          "label": "Account Opened",       "color": "#059669"},
    {"entity_type": "stage",   "entity_code": "REJECTED",          "label": "Application Rejected", "color": "#EF4444"},
    {"entity_type": "persona", "entity_code": "deposit_ops",       "label": "Deposit Ops",          "color": "#0EA5E9"},
    {"entity_type": "persona", "entity_code": "branch_manager",    "label": "Branch Manager",       "color": "#8B5CF6"},
    {"entity_type": "persona", "entity_code": "customer",          "label": "Customer",             "color": "#10B981"},
]


# ── HTTP helpers ──────────────────────────────────────────────────────────────


_CSRF_COOKIE = "gg_csrf"


def _login(client: httpx.Client, base: str, email: str, password: str) -> str:
    r = client.post(f"{base}/api/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    # The server sets both an auth cookie and a CSRF cookie. httpx stores the auth
    # cookie and sends it on subsequent requests, which triggers the CSRF middleware.
    # Echo the CSRF cookie value back as X-CSRF-Token on every future request.
    csrf = r.cookies.get(_CSRF_COOKIE) or client.cookies.get(_CSRF_COOKIE)
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return r.json()["access_token"]


def _post(client: httpx.Client, url: str, body: dict[str, Any]) -> dict[str, Any]:
    r = client.post(url, json=body)
    if r.status_code == 409:
        return r.json()  # already exists — idempotent
    r.raise_for_status()
    return r.json()


def _put(client: httpx.Client, url: str, body: dict[str, Any]) -> dict[str, Any]:
    r = client.put(url, json=body)
    r.raise_for_status()
    return r.json()


# ── Setup steps ───────────────────────────────────────────────────────────────


def setup(base_url: str, email: str, password: str, activate: bool = False) -> None:
    base = base_url.rstrip("/")

    with httpx.Client(timeout=30) as client:
        print(f"[1/14] Authenticating as {email} …")
        token = _login(client, base, email, password)
        client.headers["Authorization"] = f"Bearer {token}"
        admin = f"{base}/api/admin/domains"

        # ── Domain ──────────────────────────────────────────────────────────
        print(f"[2/14] Creating domain '{DOMAIN_CODE}' …")
        r = client.post(f"{base}/api/admin/domains",
                        json={"domain_code": DOMAIN_CODE, "display_name": DOMAIN_DISPLAY})
        if r.status_code == 409:
            # Already exists from a previous run — fetch it by listing all domains.
            print("       (already exists — fetching existing domain)")
            all_domains = client.get(f"{base}/api/admin/domains")
            all_domains.raise_for_status()
            match = next((d for d in all_domains.json() if d["domain_code"] == DOMAIN_CODE), None)
            if not match:
                raise RuntimeError(f"Domain '{DOMAIN_CODE}' reported as conflict but not found in list")
            domain = match
        else:
            r.raise_for_status()
            domain = r.json()
        domain_id = domain["id"]
        print(f"       domain_id={domain_id}")

        base_d = f"{admin}/{domain_id}"

        # ── Stages ──────────────────────────────────────────────────────────
        print("[3/14] Creating stages …")
        for s in STAGES:
            _post(client, f"{base_d}/stages", s)
            print(f"       + {s['stage_code']}")

        # ── Transitions ─────────────────────────────────────────────────────
        print("[4/14] Creating transitions …")
        for from_s, to_s in TRANSITIONS:
            _post(client, f"{base_d}/transitions",
                  {"from_stage": from_s, "to_stage": to_s})
            print(f"       + {from_s} → {to_s}")

        # ── Task routing ────────────────────────────────────────────────────
        print("[5/14] Creating task routing …")
        for stage_code, target_agent, task_type, priority in TASK_ROUTING:
            _post(client, f"{base_d}/task-routing",
                  {"stage_code": stage_code, "target_agent": target_agent,
                   "task_type": task_type, "priority": priority})
            print(f"       + {stage_code} → {target_agent}/{task_type}")

        # ── Agent roster ────────────────────────────────────────────────────
        print("[6/14] Adding agents to roster …")
        for agent_id, agent_class in AGENTS:
            _post(client, f"{base_d}/agents",
                  {"agent_id": agent_id, "agent_class": agent_class})
            print(f"       + {agent_id}")

        # ── Agent capabilities ──────────────────────────────────────────────
        print("[7/14] Setting agent capabilities …")
        for agent_id, caps in CAPABILITIES.items():
            _put(client, f"{base_d}/agents/{agent_id}/capabilities", {
                "subscribed_task_types":    caps["subscribed"],
                "emitted_task_types":       caps["emitted"],
                "allowed_handoff_targets":  caps["handoffs"],
            })
            print(f"       + {agent_id}")

        # ── Personas ────────────────────────────────────────────────────────
        print("[8/14] Creating personas …")
        for p in PERSONAS:
            _post(client, f"{base_d}/personas", p)
            print(f"       + {p['persona_code']}")

        # ── Permissions ─────────────────────────────────────────────────────
        print("[9/14] Setting permissions …")
        for persona_code, scopes in PERMISSIONS.items():
            for scope in scopes:
                _post(client, f"{base_d}/personas/{persona_code}/permissions",
                      {"permission_scope": scope})
            print(f"       + {persona_code}: {scopes}")

        # ── Products ────────────────────────────────────────────────────────
        print("[10/14] Creating products …")
        for p in PRODUCTS:
            _post(client, f"{base_d}/products", p)
            print(f"       + {p['product_code']}")

        # ── Pipeline steps ──────────────────────────────────────────────────
        print("[11/14] Adding pipeline steps …")
        for product_code, steps in PIPELINES.items():
            for step in steps:
                _post(client, f"{base_d}/products/{product_code}/pipeline", step)
            print(f"       + {product_code}: {[s['step_id'] for s in steps]}")

        # ── SLAs ────────────────────────────────────────────────────────────
        print("[12/14] Creating SLAs …")
        for sla in SLAS:
            _post(client, f"{base_d}/slas", sla)
            tier = sla.get("priority_tier") or "default"
            prod = sla.get("product_code") or "all"
            enabled = "enabled" if sla["is_enabled"] else "DISABLED"
            print(f"       + {sla['stage_code']} [{tier}][{prod}] "
                  f"{sla['window_hours']}h {enabled}")

        # ── Display config ───────────────────────────────────────────────────
        # Admin endpoint for display_config not yet built; the domain_config API
        # falls back to stage display_name + persona color automatically.
        print("[13/14] Skipping display config (no admin endpoint yet — "
              "stage display_name and persona color are used as fallback)")

        # ── Validate ────────────────────────────────────────────────────────
        print("[14/14] Validating domain …")
        r = client.post(f"{base_d}/validate")
        r.raise_for_status()
        result = r.json()
        if result.get("valid"):
            print("       ✓ Domain is valid")
        else:
            print(f"       ✗ Domain validation FAILED: {result.get('errors')}")
            sys.exit(1)

        if activate:
            print("Activating domain (deactivates wealth_management) …")
            r = client.post(f"{base_d}/activate")
            r.raise_for_status()
            print("       ✓ retail_deposit is now the active domain")

        print()
        print(f"✓ Retail/Deposit domain configured via admin portal.")
        print(f"  domain_id : {domain_id}")
        print(f"  domain_code: {DOMAIN_CODE}")
        print(f"  stages    : {[s['stage_code'] for s in STAGES]}")
        print(f"  products  : {[p['product_code'] for p in PRODUCTS]}")
        print(f"  personas  : {[p['persona_code'] for p in PERSONAS]}")
        print()
        print("To activate (switches frontend to Retail/Deposit vocab):")
        print(f"  POST {base}/api/admin/domains/{domain_id}/activate")


# ── Entry point ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Configure the Retail/Deposit domain through the admin portal API"
    )
    parser.add_argument("--base-url", default="http://localhost:8000",
                        help="Backend base URL (default: http://localhost:8000)")
    parser.add_argument("--email",    default=os.environ.get("ADMIN_EMAIL", "admin@glide-gate.local"))
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", "Admin123!"))
    parser.add_argument("--activate", action="store_true",
                        help="Activate the domain after configuration (replaces active domain)")
    args = parser.parse_args()

    setup(args.base_url, args.email, args.password, activate=args.activate)
