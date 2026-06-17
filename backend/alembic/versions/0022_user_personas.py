"""Phase 7 addendum: multi-role support — create user_personas join table, migrate
users.role data into it, drop users.role column; add case:create scope to
sales_manager so permission-based institutional case creation works.

Revision ID: 0022_user_personas
Revises: 0021_persona_permissions_expand
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0022_user_personas"
down_revision = "0021_persona_permissions_expand"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_personas",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("persona_code", sa.Text(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", "persona_code"),
    )
    op.create_index("ix_user_personas_user_id", "user_personas", ["user_id"])

    # Migrate existing single-role users into the join table
    op.execute(
        sa.text(
            "INSERT INTO user_personas (user_id, persona_code, assigned_at) "
            "SELECT id, role, created_at FROM users "
            "ON CONFLICT DO NOTHING"
        )
    )

    op.drop_column("users", "role")

    # sales_manager can now create institutional cases (explicit scope replaces
    # the implicit "not a client" logic in list_products / initiate_case).
    # domain_permissions requires domain_id — fetch from the seeded wealth domain.
    conn = op.get_bind()
    domain_id = conn.execute(
        sa.text("SELECT id FROM domains WHERE domain_code = 'wealth_management'")
    ).scalar()

    if domain_id is not None:
        conn.execute(
            sa.text(
                "INSERT INTO domain_permissions (domain_id, persona_code, permission_scope) "
                "VALUES (:domain_id, 'sales_manager', 'case:create') "
                "ON CONFLICT ON CONSTRAINT domain_permissions_uq DO NOTHING"
            ),
            {"domain_id": domain_id},
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove case:create from sales_manager (added in this migration)
    conn.execute(
        sa.text(
            "DELETE FROM domain_permissions "
            "WHERE persona_code = 'sales_manager' AND permission_scope = 'case:create'"
        )
    )

    # Restore role column from first persona_code found per user
    op.add_column("users", sa.Column("role", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE users u "
            "SET role = up.persona_code "
            "FROM (SELECT DISTINCT ON (user_id) user_id, persona_code "
            "      FROM user_personas ORDER BY user_id, assigned_at) up "
            "WHERE u.id = up.user_id"
        )
    )
    op.alter_column("users", "role", nullable=False)

    op.drop_index("ix_user_personas_user_id", table_name="user_personas")
    op.drop_table("user_personas")
