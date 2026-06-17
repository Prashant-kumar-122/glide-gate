"""Phase 9: Add status column to domain_agent_roster for admin enable/disable toggle.

APPROVED agents are dispatched normally.  DEPRECATED agents are excluded from
dispatch without requiring a redeploy — the portal simply flips the flag.

Revision ID: 0024_domain_agent_status
Revises: 0023_loosen_check_constraints
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0024_domain_agent_status"
down_revision = "0023_loosen_check_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "domain_agent_roster",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="APPROVED",
        ),
    )


def downgrade() -> None:
    op.drop_column("domain_agent_roster", "status")
