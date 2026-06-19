"""Add /agent-trace nav link to advisor, admin, and sales_manager personas.

The wealth-domain seed (0014) did not include /agent-trace in persona nav_links.
When the domain config loads successfully, it overrides the static fallback nav
entirely, so the Agent Trace screen became invisible to all non-client users.

Revision ID: 0026_add_agent_trace_nav
Revises: 0025_nullable_product_id
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0026_add_agent_trace_nav"
down_revision = "0025_nullable_product_id"
branch_labels = None
depends_on = None

_PERSONAS = ("advisor", "admin", "sales_manager")

_LINK = '[{"label": "Agent Trace", "href": "/agent-trace"}]'


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE domain_personas
               SET nav_links = nav_links || CAST(:link AS jsonb)
             WHERE persona_code = ANY(:personas)
               AND domain_id = (
                     SELECT id FROM domains WHERE domain_code = 'wealth_management'
                   )
               AND NOT (nav_links @> CAST(:link AS jsonb))
            """
        ),
        {"link": _LINK, "personas": list(_PERSONAS)},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE domain_personas
               SET nav_links = (
                     SELECT jsonb_agg(elem)
                       FROM jsonb_array_elements(nav_links) AS elem
                      WHERE elem->>'href' != '/agent-trace'
                   )
             WHERE persona_code = ANY(:personas)
               AND domain_id = (
                     SELECT id FROM domains WHERE domain_code = 'wealth_management'
                   )
            """
        ),
        {"personas": list(_PERSONAS)},
    )
