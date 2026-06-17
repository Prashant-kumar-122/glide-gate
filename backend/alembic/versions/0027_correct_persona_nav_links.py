"""Set correct nav_links for all wealth_management personas.

Final nav layout:
  advisor       → Workspace (/), Agent Trace (/agent-trace), Contact Centre (/contact-centre)
  sales_manager → Workspace (/), Agent Trace (/agent-trace), Contact Centre (/contact-centre)
  admin         → Agent Trace (/agent-trace), Admin (/admin)
  client        → [] (single portal page — tab bar should not be visible)

Revision ID: 0027_correct_persona_nav_links
Revises: 0026_add_agent_trace_nav
Create Date: 2026-06-17
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0027_correct_persona_nav_links"
down_revision = "0026_add_agent_trace_nav"
branch_labels = None
depends_on = None

_NEW_NAV: dict[str, list[dict]] = {
    "advisor": [
        {"label": "Workspace",      "href": "/"},
        {"label": "Agent Trace",    "href": "/agent-trace"},
        {"label": "Contact Centre", "href": "/contact-centre"},
    ],
    "sales_manager": [
        {"label": "Workspace",      "href": "/"},
        {"label": "Agent Trace",    "href": "/agent-trace"},
        {"label": "Contact Centre", "href": "/contact-centre"},
    ],
    "admin": [
        {"label": "Agent Trace", "href": "/agent-trace"},
        {"label": "Admin",       "href": "/admin"},
    ],
    "client": [],
}

# Previous values (from 0014 seed + 0026 patch) for downgrade
_OLD_NAV: dict[str, list[dict]] = {
    "advisor": [
        {"label": "Cases",       "href": "/advisor/cases"},
        {"label": "Clients",     "href": "/advisor/clients"},
        {"label": "Agent Trace", "href": "/agent-trace"},
    ],
    "sales_manager": [
        {"label": "Cases",        "href": "/advisor/cases"},
        {"label": "Sales Review", "href": "/advisor/cases?stage=SALES_REVIEW"},
        {"label": "Agent Trace",  "href": "/agent-trace"},
    ],
    "admin": [
        {"label": "Cases",       "href": "/advisor/cases"},
        {"label": "Admin",       "href": "/admin"},
        {"label": "Agent Trace", "href": "/agent-trace"},
    ],
    "client": [
        {"label": "My Application", "href": "/client/portal"},
    ],
}


def _apply(nav_map: dict[str, list[dict]]) -> None:
    conn = op.get_bind()
    for persona_code, links in nav_map.items():
        conn.execute(
            sa.text(
                """
                UPDATE domain_personas
                   SET nav_links = CAST(:nav AS jsonb)
                 WHERE persona_code = :code
                   AND domain_id = (
                         SELECT id FROM domains WHERE domain_code = 'wealth_management'
                       )
                """
            ),
            {"nav": json.dumps(links), "code": persona_code},
        )


def upgrade() -> None:
    _apply(_NEW_NAV)


def downgrade() -> None:
    _apply(_OLD_NAV)
