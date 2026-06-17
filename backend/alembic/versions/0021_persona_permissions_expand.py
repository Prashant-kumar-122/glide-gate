"""Phase 7: expand domain_permissions to cover all 15 scopes; add compliance_officer persona;
drop users_role_check CHECK constraint so any persona_code value is valid.

Revision ID: 0021_persona_permissions_expand
Revises: 0020_skills_mcp_seed
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021_persona_permissions_expand"
down_revision = "0020_skills_mcp_seed"
branch_labels = None
depends_on = None

_WEALTH_CODE = "wealth_management"

# ── Additional scopes for existing personas (not already seeded in 0014) ──────
# Schema: (persona_code, scope)
_NEW_SCOPES: list[tuple[str, str]] = [
    # client: can read their own case
    ("client", "case:read"),
    # advisor: approve reviews + view sales reviews + access audit log
    ("advisor", "review:approve"),
    ("advisor", "sales:review"),
    ("advisor", "audit:read"),
    # sales_manager: can advance/approve cases; view audit; decide on tasks
    ("sales_manager", "case:approve"),
    ("sales_manager", "review:approve"),
    ("sales_manager", "audit:read"),
]

# ── New persona: compliance_officer ───────────────────────────────────────────
_COMPLIANCE_OFFICER_PERSONA = {
    "persona_code": "compliance_officer",
    "display_label": "Compliance Officer",
    "color": "#EF4444",
    "default_route": "/advisor/cases",
    "nav_links": [
        {"label": "Cases", "href": "/advisor/cases"},
        {"label": "Audit", "href": "/audit"},
    ],
}

_COMPLIANCE_OFFICER_SCOPES = [
    "case:read",
    "review:read",
    "review:approve",
    "review:escalate",
    "compliance:read",
    "compliance:decide",
    "audit:read",
    "audit:export",
]

_COMPLIANCE_OFFICER_DISPLAY = {
    "entity_type": "persona",
    "entity_code": "compliance_officer",
    "label": "Compliance Officer",
    "color": "#EF4444",
}


def upgrade() -> None:
    conn = op.get_bind()
    import json

    domain_id = conn.execute(sa.text(
        "SELECT id FROM domains WHERE domain_code = :code"
    ), {"code": _WEALTH_CODE}).scalar()

    if domain_id is None:
        return  # wealth domain not yet seeded (test env)

    # ── Add missing scopes to existing personas ────────────────────────────────
    for persona_code, scope in _NEW_SCOPES:
        conn.execute(sa.text(
            "INSERT INTO domain_permissions (domain_id, persona_code, permission_scope) "
            "VALUES (:domain_id, :persona_code, :scope) "
            "ON CONFLICT ON CONSTRAINT domain_permissions_uq DO NOTHING"
        ), {"domain_id": domain_id, "persona_code": persona_code, "scope": scope})

    # ── Insert compliance_officer persona ──────────────────────────────────────
    p = _COMPLIANCE_OFFICER_PERSONA
    conn.execute(sa.text(
        "INSERT INTO domain_personas "
        "(domain_id, persona_code, display_label, color, default_route, nav_links) "
        "VALUES (:domain_id, :persona_code, :display_label, :color, :default_route, "
        "        CAST(:nav_links AS jsonb)) "
        "ON CONFLICT ON CONSTRAINT domain_personas_uq DO NOTHING"
    ), {
        "domain_id": domain_id,
        "persona_code": p["persona_code"],
        "display_label": p["display_label"],
        "color": p["color"],
        "default_route": p["default_route"],
        "nav_links": json.dumps(p["nav_links"]),
    })

    for scope in _COMPLIANCE_OFFICER_SCOPES:
        conn.execute(sa.text(
            "INSERT INTO domain_permissions (domain_id, persona_code, permission_scope) "
            "VALUES (:domain_id, :persona_code, :scope) "
            "ON CONFLICT ON CONSTRAINT domain_permissions_uq DO NOTHING"
        ), {"domain_id": domain_id, "persona_code": "compliance_officer", "scope": scope})

    d = _COMPLIANCE_OFFICER_DISPLAY
    conn.execute(sa.text(
        "INSERT INTO domain_display_config "
        "(domain_id, entity_type, entity_code, label, color) "
        "VALUES (:domain_id, :entity_type, :entity_code, :label, :color) "
        "ON CONFLICT ON CONSTRAINT domain_display_config_uq DO NOTHING"
    ), {"domain_id": domain_id, **d})

    # ── Drop users_role_check CHECK constraint ─────────────────────────────────
    # users.role now maps to domain_personas.persona_code; validated at app layer.
    op.drop_constraint("users_role_check", "users", type_="check")


def downgrade() -> None:
    conn = op.get_bind()

    domain_id = conn.execute(sa.text(
        "SELECT id FROM domains WHERE domain_code = :code"
    ), {"code": _WEALTH_CODE}).scalar()

    if domain_id is not None:
        conn.execute(sa.text(
            "DELETE FROM domain_personas "
            "WHERE domain_id = :domain_id AND persona_code = 'compliance_officer'"
        ), {"domain_id": domain_id})

        for persona_code, scope in _NEW_SCOPES:
            conn.execute(sa.text(
                "DELETE FROM domain_permissions "
                "WHERE domain_id = :domain_id AND persona_code = :persona_code "
                "AND permission_scope = :scope"
            ), {"domain_id": domain_id, "persona_code": persona_code, "scope": scope})

    op.create_check_constraint(
        "users_role_check",
        "users",
        "role IN ('client', 'advisor', 'admin', 'sales_manager')",
    )
