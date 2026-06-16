"""Add product_activation table (Phase 4.6)

Revision ID: 0018_product_activation
Revises: 0017_product_pipeline_seed
Create Date: 2026-06-16

Phase 4.6 — First-to-complete activation gate (FR-GL-01/02/03).

Adds:
  - product_activation: per-product activation state machine
    (PENDING → CRITERIA_MET → ACTIVATED | DECLINED)
  - Adverse-action fields for ECOA compliance (FR-AU-04)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_product_activation"
down_revision = "0017_product_pipeline_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_activation",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("product_code", sa.Text(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("criteria_met_at", sa.DateTime(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("declined_at", sa.DateTime(), nullable=True),
        sa.Column("decline_reason", sa.Text(), nullable=True),
        sa.Column("account_number", sa.String(100), nullable=True),
        sa.Column("is_adverse_action", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("adverse_action_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "state IN ('PENDING', 'CRITERIA_MET', 'ACTIVATED', 'DECLINED')",
            name="pa_state_chk",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "product_code", name="pa_case_product_uq"),
    )
    op.create_index("ix_product_activation_case_id", "product_activation", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_product_activation_case_id", table_name="product_activation")
    op.drop_table("product_activation")
