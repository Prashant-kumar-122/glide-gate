"""Notifications: rename client_id → user_id, add user_type, fix status check

Revision ID: 0008_notifications_user_id
Revises: 0007_client_accounts_per_product
Create Date: 2026-05-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_notifications_user_id"
down_revision = "0007_client_accounts_per_product"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop old FK from client_id → clients.id
    op.drop_constraint("fk_notif_client", "notifications", type_="foreignkey")

    # 2. Rename the column
    op.alter_column("notifications", "client_id", new_column_name="user_id")

    # 3. Re-add FK pointing at users.id (nullable — system notifications have no user)
    op.create_foreign_key(
        "fk_notif_user",
        "notifications",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. Add user_type column
    op.add_column(
        "notifications",
        sa.Column("user_type", sa.String(20), nullable=True),
    )
    op.create_check_constraint(
        "notif_user_type_chk",
        "notifications",
        "user_type IN ('client', 'advisor', 'admin')",
    )

    # 5. Widen the status check to include SIMULATED_SENT
    op.drop_constraint("notif_status_chk", "notifications", type_="check")
    op.create_check_constraint(
        "notif_status_chk",
        "notifications",
        "status IN ('PENDING','SENT','FAILED','BOUNCED','SIMULATED_SENT')",
    )

    # 6. Index for quick per-user lookups
    op.create_index("idx_notif_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_notif_user_id", table_name="notifications")
    op.drop_constraint("notif_user_type_chk", "notifications", type_="check")
    op.drop_column("notifications", "user_type")
    op.drop_constraint("fk_notif_user", "notifications", type_="foreignkey")
    op.alter_column("notifications", "user_id", new_column_name="client_id")
    op.create_foreign_key(
        "fk_notif_client", "notifications", "clients", ["client_id"], ["id"]
    )
    op.drop_constraint("notif_status_chk", "notifications", type_="check")
    op.create_check_constraint(
        "notif_status_chk",
        "notifications",
        "status IN ('PENDING','SENT','FAILED','BOUNCED')",
    )
