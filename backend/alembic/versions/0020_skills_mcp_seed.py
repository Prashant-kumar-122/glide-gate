"""Seed domain_agent_skills, domain_agent_tool_grants, and domain_agent_prompts for Phase 6.

Revision ID: 0020_skills_mcp_seed
Revises: 0019_sla_tracking
Create Date: 2026-06-16

Activates the Skills + MCP gateway wiring for the wealth management domain:
  - domain_agent_tool_grants: kyc_compliance → identity_verification.* tools
  - domain_agent_tool_grants: document_intelligence → document_management.* tools
  - domain_agent_skills: kyc_compliance → escalation skill binding
  - domain_agent_prompts: kyc_compliance system prompt (matches hardcoded constant in escalation_skill.py)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020_skills_mcp_seed"
down_revision = "0019_sla_tracking"
branch_labels = None
depends_on = None

_WEALTH_CODE = "wealth_management"

# ── Tool grants ────────────────────────────────────────────────────────────────
# Each tuple: (agent_id, connector_id, tool_name)

_TOOL_GRANTS = [
    # KYC agent may call all three identity-verification tools
    ("kyc_compliance", "identity_verification", "verify_identity"),
    ("kyc_compliance", "identity_verification", "check_sanctions"),
    ("kyc_compliance", "identity_verification", "score_aml_risk"),
    # Document intelligence agent may call all document management tools
    ("document_intelligence", "document_management", "upload_document"),
    ("document_intelligence", "document_management", "retrieve_document"),
    ("document_intelligence", "document_management", "get_document_status"),
    ("document_intelligence", "document_management", "extract_ocr"),
]

# ── Skill bindings ─────────────────────────────────────────────────────────────
# Each tuple: (agent_id, skill_id, bound_parameters_json)

_SKILL_BINDINGS = [
    ("kyc_compliance", "escalation", {"escalation_threshold": 0.7}),
]

# ── Agent system prompts ───────────────────────────────────────────────────────
# Prompts stored here mirror the hardcoded _SYSTEM constants in skill files.
# Admin portal (Phase 9) will allow overriding these rows without a redeploy.

_KYC_SYSTEM_PROMPT = (
    "You are a compliance risk officer for a wealth management firm. "
    "Assess whether the current onboarding case warrants escalation to a human reviewer. "
    'Return a JSON object: {"should_escalate": <true|false>, '
    '"severity": "LOW"|"MEDIUM"|"HIGH"|"CRITICAL", "reason": "<concise reason>", '
    '"risk_factors": ["<factor>", ...], '
    '"recommended_action": "APPROVE"|"ESCALATE"|"REQUEST_MORE_INFO"|"REJECT"} '
    "Return only valid JSON. Err on the side of caution for high-risk indicators."
)

# Each tuple: (agent_id, prompt_role, prompt_text)
_AGENT_PROMPTS = [
    ("kyc_compliance", "escalation_assessment", _KYC_SYSTEM_PROMPT),
]


def upgrade() -> None:
    conn = op.get_bind()

    domain_id = conn.execute(sa.text(
        "SELECT id FROM domains WHERE domain_code = :code"
    ), {"code": _WEALTH_CODE}).scalar()

    if domain_id is None:
        raise RuntimeError(
            f"Domain {_WEALTH_CODE!r} not found. "
            "Run migration 0014_wealth_domain_seed first."
        )

    import json

    # ── Tool grants ───────────────────────────────────────────────────────────
    for agent_id, connector_id, tool_name in _TOOL_GRANTS:
        conn.execute(sa.text(
            "INSERT INTO domain_agent_tool_grants "
            "(domain_id, agent_id, connector_id, tool_name) "
            "VALUES (:domain_id, :agent_id, :connector_id, :tool_name) "
            "ON CONFLICT ON CONSTRAINT domain_agent_tool_grants_uq DO NOTHING"
        ), {
            "domain_id": domain_id,
            "agent_id": agent_id,
            "connector_id": connector_id,
            "tool_name": tool_name,
        })

    # ── Skill bindings ────────────────────────────────────────────────────────
    for agent_id, skill_id, bound_params in _SKILL_BINDINGS:
        conn.execute(sa.text(
            "INSERT INTO domain_agent_skills "
            "(domain_id, agent_id, skill_id, bound_parameters) "
            "VALUES (:domain_id, :agent_id, :skill_id, CAST(:bound_params AS jsonb)) "
            "ON CONFLICT ON CONSTRAINT domain_agent_skills_uq DO NOTHING"
        ), {
            "domain_id": domain_id,
            "agent_id": agent_id,
            "skill_id": skill_id,
            "bound_params": json.dumps(bound_params),
        })

    # ── Agent prompts ─────────────────────────────────────────────────────────
    for agent_id, prompt_role, prompt_text in _AGENT_PROMPTS:
        conn.execute(sa.text(
            "INSERT INTO domain_agent_prompts "
            "(domain_id, agent_id, prompt_role, prompt_text) "
            "VALUES (:domain_id, :agent_id, :prompt_role, :prompt_text) "
            "ON CONFLICT ON CONSTRAINT domain_agent_prompts_uq DO NOTHING"
        ), {
            "domain_id": domain_id,
            "agent_id": agent_id,
            "prompt_role": prompt_role,
            "prompt_text": prompt_text,
        })


def downgrade() -> None:
    conn = op.get_bind()

    domain_id = conn.execute(sa.text(
        "SELECT id FROM domains WHERE domain_code = :code"
    ), {"code": _WEALTH_CODE}).scalar()

    if domain_id is None:
        return

    for agent_id, connector_id, tool_name in _TOOL_GRANTS:
        conn.execute(sa.text(
            "DELETE FROM domain_agent_tool_grants "
            "WHERE domain_id = :domain_id AND agent_id = :agent_id "
            "  AND connector_id = :connector_id AND tool_name = :tool_name"
        ), {"domain_id": domain_id, "agent_id": agent_id,
            "connector_id": connector_id, "tool_name": tool_name})

    for agent_id, skill_id, _ in _SKILL_BINDINGS:
        conn.execute(sa.text(
            "DELETE FROM domain_agent_skills "
            "WHERE domain_id = :domain_id AND agent_id = :agent_id AND skill_id = :skill_id"
        ), {"domain_id": domain_id, "agent_id": agent_id, "skill_id": skill_id})

    for agent_id, prompt_role, _ in _AGENT_PROMPTS:
        conn.execute(sa.text(
            "DELETE FROM domain_agent_prompts "
            "WHERE domain_id = :domain_id AND agent_id = :agent_id AND prompt_role = :prompt_role"
        ), {"domain_id": domain_id, "agent_id": agent_id, "prompt_role": prompt_role})
