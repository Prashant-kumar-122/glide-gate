"""Add description column to domain_products.

Revision ID: 0028_domain_product_desc
Revises: 0027_correct_persona_nav_links
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0028_domain_product_desc"
down_revision = "0027_correct_persona_nav_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "domain_products",
        sa.Column("description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("domain_products", "description")
