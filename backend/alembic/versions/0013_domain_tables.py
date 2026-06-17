"""Create all domain_* tables for CADF Phase 1 DomainDefinition model

Revision ID: 0013_domain_tables
Revises: 0012_push_subscriptions
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_domain_tables"
down_revision = "0012_push_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── domains ───────────────────────────────────────────────────────────────
    op.create_table(
        "domains",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_code", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_code", name="domains_code_uq"),
    )
    op.create_index("ix_domains_code", "domains", ["domain_code"])
    op.create_index("ix_domains_is_active", "domains", ["is_active"])

    # ── domain_stages ─────────────────────────────────────────────────────────
    op.create_table(
        "domain_stages",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("stage_code", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("is_terminal", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_human_pending", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "stage_code", name="domain_stages_uq"),
    )
    op.create_index("ix_domain_stages_domain_id", "domain_stages", ["domain_id"])

    # ── domain_transitions ────────────────────────────────────────────────────
    op.create_table(
        "domain_transitions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("from_stage", sa.String(50), nullable=False),
        sa.Column("to_stage", sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "from_stage", "to_stage", name="domain_transitions_uq"),
    )
    op.create_index("ix_domain_transitions_domain_id", "domain_transitions", ["domain_id"])

    # ── domain_task_routing ───────────────────────────────────────────────────
    op.create_table(
        "domain_task_routing",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("stage_code", sa.String(50), nullable=False),
        sa.Column("target_agent", sa.String(100), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("priority", sa.String(20), server_default="NORMAL", nullable=False),
        sa.Column("payload_template", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("notification_templates", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "stage_code", name="domain_task_routing_uq"),
    )
    op.create_index("ix_domain_task_routing_domain_id", "domain_task_routing", ["domain_id"])

    # ── domain_agent_roster ───────────────────────────────────────────────────
    op.create_table(
        "domain_agent_roster",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("agent_class", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "agent_id", name="domain_agent_roster_uq"),
    )
    op.create_index("ix_domain_agent_roster_domain_id", "domain_agent_roster", ["domain_id"])

    # ── domain_agent_capabilities ─────────────────────────────────────────────
    op.create_table(
        "domain_agent_capabilities",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("subscribed_task_types", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("emitted_task_types", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("allowed_handoff_targets", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "agent_id", name="domain_agent_capabilities_uq"),
    )
    op.create_index("ix_domain_agent_capabilities_domain_id", "domain_agent_capabilities", ["domain_id"])

    # ── domain_product_pipelines ──────────────────────────────────────────────
    op.create_table(
        "domain_product_pipelines",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("product_code", sa.String(50), nullable=False),
        sa.Column("step_id", sa.String(100), nullable=False),
        sa.Column("step_label", sa.String(200), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("is_parallel", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("step_config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "product_code", "step_id", name="domain_product_pipelines_uq"),
    )
    op.create_index("ix_domain_product_pipelines_domain_id", "domain_product_pipelines", ["domain_id"])
    op.create_index("ix_domain_product_pipelines_product", "domain_product_pipelines", ["domain_id", "product_code"])

    # ── domain_agent_prompts ──────────────────────────────────────────────────
    op.create_table(
        "domain_agent_prompts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("prompt_role", sa.String(100), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "agent_id", "prompt_role", name="domain_agent_prompts_uq"),
    )
    op.create_index("ix_domain_agent_prompts_domain_id", "domain_agent_prompts", ["domain_id"])

    # ── domain_agent_skills ───────────────────────────────────────────────────
    op.create_table(
        "domain_agent_skills",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("skill_id", sa.String(100), nullable=False),
        sa.Column("bound_parameters", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "agent_id", "skill_id", name="domain_agent_skills_uq"),
    )
    op.create_index("ix_domain_agent_skills_domain_id", "domain_agent_skills", ["domain_id"])

    # ── domain_agent_tool_grants ──────────────────────────────────────────────
    op.create_table(
        "domain_agent_tool_grants",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("connector_id", sa.String(100), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "agent_id", "connector_id", "tool_name", name="domain_agent_tool_grants_uq"),
    )
    op.create_index("ix_domain_agent_tool_grants_domain_id", "domain_agent_tool_grants", ["domain_id"])

    # ── domain_stage_slas ─────────────────────────────────────────────────────
    # NULL priority_tier/product_code = "default" SLA for that stage.
    # The COALESCE-based unique index ensures at most one default row per stage.
    op.create_table(
        "domain_stage_slas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("stage_code", sa.String(50), nullable=False),
        sa.Column("priority_tier", sa.String(50), nullable=True),
        sa.Column("product_code", sa.String(50), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("window_hours", sa.Numeric(10, 4), nullable=False),
        sa.Column("warning_pct", sa.Integer(), server_default="80", nullable=False),
        sa.Column("escalation_pct", sa.Integer(), server_default="100", nullable=False),
        sa.Column("warning_task_type", sa.String(100), nullable=False),
        sa.Column("escalation_task_type", sa.String(100), nullable=False),
        sa.Column("escalation_target_agent", sa.String(100), nullable=False),
        sa.Column("pause_on_human_review", sa.Boolean(), server_default="false", nullable=False),
        sa.CheckConstraint("warning_pct < escalation_pct", name="domain_stage_slas_pct_chk"),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_domain_stage_slas_domain_id", "domain_stage_slas", ["domain_id"])
    # COALESCE-based unique index: enforces at most one default (NULL) row per domain+stage
    op.execute(
        """
        CREATE UNIQUE INDEX domain_stage_slas_uq
        ON domain_stage_slas (
            domain_id,
            stage_code,
            COALESCE(priority_tier, ''),
            COALESCE(product_code, '')
        )
        """
    )

    # ── domain_personas ───────────────────────────────────────────────────────
    op.create_table(
        "domain_personas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("persona_code", sa.String(50), nullable=False),
        sa.Column("display_label", sa.String(200), nullable=False),
        sa.Column("color", sa.String(50), server_default="'#000000'", nullable=False),
        sa.Column("default_route", sa.String(255), server_default="'/'", nullable=False),
        sa.Column("nav_links", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "persona_code", name="domain_personas_uq"),
    )
    op.create_index("ix_domain_personas_domain_id", "domain_personas", ["domain_id"])

    # ── domain_permissions ────────────────────────────────────────────────────
    op.create_table(
        "domain_permissions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("persona_code", sa.String(50), nullable=False),
        sa.Column("permission_scope", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "persona_code", "permission_scope", name="domain_permissions_uq"),
    )
    op.create_index("ix_domain_permissions_domain_id", "domain_permissions", ["domain_id"])

    # ── domain_products ───────────────────────────────────────────────────────
    op.create_table(
        "domain_products",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("product_code", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("product_type", sa.String(50), server_default="'retail'", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("suitability_criteria", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("required_documents", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("activation_criteria", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "product_code", name="domain_products_uq"),
    )
    op.create_index("ix_domain_products_domain_id", "domain_products", ["domain_id"])

    # ── domain_display_config ─────────────────────────────────────────────────
    op.create_table(
        "domain_display_config",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_code", sa.String(100), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("color", sa.String(50), server_default="'#000000'", nullable=False),
        sa.Column("style", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "entity_type", "entity_code", name="domain_display_config_uq"),
    )
    op.create_index("ix_domain_display_config_domain_id", "domain_display_config", ["domain_id"])


def downgrade() -> None:
    op.drop_index("ix_domain_display_config_domain_id", table_name="domain_display_config")
    op.drop_table("domain_display_config")

    op.drop_index("ix_domain_products_domain_id", table_name="domain_products")
    op.drop_table("domain_products")

    op.drop_index("ix_domain_permissions_domain_id", table_name="domain_permissions")
    op.drop_table("domain_permissions")

    op.drop_index("ix_domain_personas_domain_id", table_name="domain_personas")
    op.drop_table("domain_personas")

    op.execute("DROP INDEX IF EXISTS domain_stage_slas_uq")
    op.drop_index("ix_domain_stage_slas_domain_id", table_name="domain_stage_slas")
    op.drop_table("domain_stage_slas")

    op.drop_index("ix_domain_agent_tool_grants_domain_id", table_name="domain_agent_tool_grants")
    op.drop_table("domain_agent_tool_grants")

    op.drop_index("ix_domain_agent_skills_domain_id", table_name="domain_agent_skills")
    op.drop_table("domain_agent_skills")

    op.drop_index("ix_domain_agent_prompts_domain_id", table_name="domain_agent_prompts")
    op.drop_table("domain_agent_prompts")

    op.drop_index("ix_domain_product_pipelines_product", table_name="domain_product_pipelines")
    op.drop_index("ix_domain_product_pipelines_domain_id", table_name="domain_product_pipelines")
    op.drop_table("domain_product_pipelines")

    op.drop_index("ix_domain_agent_capabilities_domain_id", table_name="domain_agent_capabilities")
    op.drop_table("domain_agent_capabilities")

    op.drop_index("ix_domain_agent_roster_domain_id", table_name="domain_agent_roster")
    op.drop_table("domain_agent_roster")

    op.drop_index("ix_domain_task_routing_domain_id", table_name="domain_task_routing")
    op.drop_table("domain_task_routing")

    op.drop_index("ix_domain_transitions_domain_id", table_name="domain_transitions")
    op.drop_table("domain_transitions")

    op.drop_index("ix_domain_stages_domain_id", table_name="domain_stages")
    op.drop_table("domain_stages")

    op.drop_index("ix_domains_is_active", table_name="domains")
    op.drop_index("ix_domains_code", table_name="domains")
    op.drop_table("domains")
