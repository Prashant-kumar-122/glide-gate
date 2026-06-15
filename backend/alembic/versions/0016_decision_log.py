"""Add decision_log table and is_regulatory_breach to event_logs (Phase 2.5)

Revision ID: 0016_decision_log
Revises: 0015_priority_tier
Create Date: 2026-06-15

Implements FR-AU-01 (immutable hash-chained audit trail) and FR-AU-03 (audit export).

WORM semantics:
  The decision_log table is append-only by design. No UPDATE or DELETE methods
  exist on DecisionLogService. In production, revoke these privileges from the
  app database role:
      REVOKE UPDATE, DELETE ON decision_log FROM <app_role>;
  The default 'postgres' superuser cannot be restricted this way — create a
  dedicated app role (e.g. glide_app) in production deployments.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016_decision_log"
down_revision = "0015_priority_tier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── decision_log (append-only hash-chained audit trail) ───────────────────
    op.create_table(
        "decision_log",
        sa.Column("seq", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("case_id", sa.UUID(), sa.ForeignKey("onboarding_cases.id"), nullable=True),
        sa.Column("client_id", sa.UUID(), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("chain_hash", sa.String(64), nullable=False),
        sa.Column("is_compliance_event", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_regulatory_breach", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_decision_log_case_id", "decision_log", ["case_id"])
    op.create_index("ix_decision_log_client_id", "decision_log", ["client_id"])
    op.create_index("ix_decision_log_event_type", "decision_log", ["event_type"])
    op.create_index("ix_decision_log_is_compliance", "decision_log", ["is_compliance_event"])

    # ── is_regulatory_breach on event_logs ───────────────────────────────────
    op.add_column(
        "event_logs",
        sa.Column("is_regulatory_breach", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("event_logs", "is_regulatory_breach")
    op.drop_index("ix_decision_log_is_compliance", table_name="decision_log")
    op.drop_index("ix_decision_log_event_type", table_name="decision_log")
    op.drop_index("ix_decision_log_client_id", table_name="decision_log")
    op.drop_index("ix_decision_log_case_id", table_name="decision_log")
    op.drop_table("decision_log")
