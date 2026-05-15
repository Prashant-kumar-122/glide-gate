"""Add percentage column to onboarding_cases

Revision ID: 0003_case_percentage
Revises: 0002_users
Create Date: 2026-05-16

Stores the overall onboarding progress (0-100) directly on the case row,
updated on each question answered, document approved, and KYC completion.
Survives server restarts so the progress bar is correct on page load/refresh.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_case_percentage"
down_revision = "0002_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "onboarding_cases",
        sa.Column(
            "percentage",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
    )


def downgrade() -> None:
    op.drop_column("onboarding_cases", "percentage")
