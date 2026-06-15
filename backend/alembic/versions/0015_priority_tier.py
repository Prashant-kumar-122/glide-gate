"""Add priority_tier column to onboarding_cases (Phase 2)

Revision ID: 0015_priority_tier
Revises: 0014_wealth_domain_seed
Create Date: 2026-06-15

Adds priority_tier (e.g. 'standard', 'premium', 'sme') used by Phase 5
SLA window selection to pick the correct domain_stage_slas row.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_priority_tier"
down_revision = "0014_wealth_domain_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "onboarding_cases",
        sa.Column(
            "priority_tier",
            sa.String(50),
            nullable=False,
            server_default="standard",
        ),
    )


def downgrade() -> None:
    op.drop_column("onboarding_cases", "priority_tier")
