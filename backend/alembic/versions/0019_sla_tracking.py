"""Create case_sla_tracking table and seed wealth domain SLA rows (Phase 5)

Revision ID: 0019_sla_tracking
Revises: 0018_product_activation
Create Date: 2026-06-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_sla_tracking"
down_revision = "0018_product_activation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── case_sla_tracking ─────────────────────────────────────────────────────
    op.create_table(
        "case_sla_tracking",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("stage_code", sa.String(50), nullable=False),
        sa.Column("window_hours", sa.Numeric(10, 4), nullable=False),
        sa.Column("warning_pct", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("escalation_pct", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("warning_task_type", sa.String(100), nullable=False),
        sa.Column("escalation_task_type", sa.String(100), nullable=False),
        sa.Column("escalation_target_agent", sa.String(100), nullable=False),
        sa.Column("pause_on_human_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("priority_tier", sa.String(50), nullable=True),
        sa.Column("product_code", sa.String(50), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("warning_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("breach_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "stage_code", name="case_sla_tracking_uq"),
    )
    op.create_index("ix_case_sla_tracking_case_id", "case_sla_tracking", ["case_id"])
    op.create_index("ix_case_sla_tracking_stage", "case_sla_tracking", ["stage_code"])

    # ── Wealth domain SLA seed rows ───────────────────────────────────────────
    # Default SLA windows for the wealth_management domain.
    # Priority chain: (stage + priority_tier) is more specific than (stage only).
    # The application resolves the most-specific matching row at runtime.
    op.execute(sa.text("""
        INSERT INTO domain_stage_slas (
            domain_id, stage_code, priority_tier, product_code,
            is_enabled, window_hours, warning_pct, escalation_pct,
            warning_task_type, escalation_task_type, escalation_target_agent,
            pause_on_human_review
        )
        SELECT
            d.id,
            v.stage_code,
            v.priority_tier,
            NULL::text,
            TRUE,
            v.window_hours,
            v.warning_pct,
            v.escalation_pct,
            'sla_warning',
            'sla_breach',
            'orchestrator',
            v.pause_on_human_review
        FROM domains d
        CROSS JOIN (VALUES
            ('INTAKE',            NULL::text, 120.0::numeric, 70::int, 90::int, FALSE::boolean),
            ('INTAKE',            'sme',       48.0::numeric, 70::int, 90::int, FALSE::boolean),
            ('KYC',               NULL::text,   2.0::numeric, 70::int, 90::int, FALSE::boolean),
            ('KYC',               'sme',        1.0::numeric, 70::int, 90::int, FALSE::boolean),
            ('PARALLEL_PRODUCTS', NULL::text,   4.0::numeric, 70::int, 90::int, FALSE::boolean),
            ('REVIEW',            NULL::text,  48.0::numeric, 70::int, 90::int, TRUE::boolean),
            ('SALES_REVIEW',      NULL::text,  24.0::numeric, 70::int, 90::int, TRUE::boolean),
            ('ESCALATED',         NULL::text,  72.0::numeric, 70::int, 90::int, FALSE::boolean)
        ) AS v(stage_code, priority_tier, window_hours, warning_pct, escalation_pct, pause_on_human_review)
        WHERE d.domain_code = 'wealth_management'
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    op.execute(sa.text(
        "DELETE FROM domain_stage_slas "
        "WHERE warning_task_type = 'sla_warning' AND escalation_task_type = 'sla_breach'"
    ))
    op.drop_index("ix_case_sla_tracking_stage")
    op.drop_index("ix_case_sla_tracking_case_id")
    op.drop_table("case_sla_tracking")
