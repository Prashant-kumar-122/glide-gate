"""Add sales_manager_reviews table and SALES_REVIEW stage to onboarding_cases

Revision ID: 0005_sales_review
Revises: 0011_institutional_products_seed
Create Date: 2026-06-04

Changes:
- Create sales_manager_reviews table
- Drop and recreate oc_status_chk / oc_stage_chk constraints to include SALES_REVIEW
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_sales_review"
down_revision = "0011_institutional_products_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Widen onboarding_cases CHECK constraints ───────────────────────────
    # Drop only if constraint exists (DB may already have these values applied)
    bind.execute(sa.text(
        "ALTER TABLE onboarding_cases DROP CONSTRAINT IF EXISTS oc_status_chk"
    ))
    bind.execute(sa.text(
        "ALTER TABLE onboarding_cases DROP CONSTRAINT IF EXISTS oc_stage_chk"
    ))

    op.create_check_constraint(
        "oc_status_chk",
        "onboarding_cases",
        "status IN ('INTAKE','SALES_REVIEW','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED')",
    )
    op.create_check_constraint(
        "oc_stage_chk",
        "onboarding_cases",
        "current_stage IN ('INTAKE','SALES_REVIEW','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED')",
    )

    # ── 2. Create sales_manager_reviews table (idempotent) ────────────────────
    from sqlalchemy import inspect as sa_inspect
    if "sales_manager_reviews" in sa_inspect(bind).get_table_names():
        return
    op.create_table(
        "sales_manager_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("onboarding_cases.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("reviewer_role", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("decision", sa.String(30), nullable=True),
        sa.Column("decision_notes", sa.Text, nullable=True),
        sa.Column("ai_risk_summary", sa.Text, nullable=True),
        sa.Column("risk_score", sa.Float, nullable=True),
        sa.Column(
            "case_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("assigned_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED','MORE_INFO_REQUESTED')",
            name="smr_status_chk",
        ),
    )


def downgrade() -> None:
    op.drop_table("sales_manager_reviews")

    op.drop_constraint("oc_status_chk", "onboarding_cases", type_="check")
    op.drop_constraint("oc_stage_chk", "onboarding_cases", type_="check")

    op.create_check_constraint(
        "oc_status_chk",
        "onboarding_cases",
        "status IN ('INTAKE','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED')",
    )
    op.create_check_constraint(
        "oc_stage_chk",
        "onboarding_cases",
        "current_stage IN ('INTAKE','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED')",
    )
