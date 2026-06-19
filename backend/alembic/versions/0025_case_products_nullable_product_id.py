"""Make case_products.product_id nullable to support domain-managed products.

Products created via the CADF admin portal live in domain_products, not the
legacy products table.  Removing the NOT NULL constraint allows CaseProduct
rows to be created without a legacy FK when the active domain supplies the
product definition.

Revision ID: 0025_nullable_product_id
Revises: 0024_domain_agent_status
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0025_nullable_product_id"
down_revision = "0024_domain_agent_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("case_products", "product_id", nullable=True)


def downgrade() -> None:
    op.alter_column("case_products", "product_id", nullable=False)
