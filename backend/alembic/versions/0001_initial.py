"""Initial schema — 25 tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-13

BRD: Section 15.2.1–15.2.4
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── document_status ENUM ──────────────────────────────────────────────────
    document_status = postgresql.ENUM(
        "NOT_REQUESTED", "REQUESTED", "RECEIVED", "UNDER_REVIEW", "NEEDS_REVISION", "APPROVED",
        name="document_status",
    )
    document_status.create(op.get_bind(), checkfirst=True)

    # ── clients ───────────────────────────────────────────────────────────────
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date),
        sa.Column("nationality", sa.String(100)),
        sa.Column("tax_residency", sa.String(100)),
        sa.Column("employment_status", sa.String(50)),
        sa.Column("annual_income", sa.Numeric(15, 2)),
        sa.Column("source_of_wealth", sa.Text),
        sa.Column("risk_appetite", sa.String(20)),
        sa.Column("investment_experience", sa.String(20)),
        sa.Column("investment_horizon", sa.String(20)),
        sa.Column("kyc_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("email", name="clients_email_uq"),
        sa.CheckConstraint("kyc_status IN ('PENDING','PASSED','FAILED','ESCALATED')", name="clients_kyc_status_chk"),
    )
    op.create_index("idx_clients_email", "clients", ["email"])
    op.create_index("idx_clients_kyc_status", "clients", ["kyc_status"])
    op.create_index("idx_clients_created_at", "clients", [sa.text("created_at DESC")])

    # ── client_profiles ───────────────────────────────────────────────────────
    op.create_table(
        "client_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("consent_marketing", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.Column("consent_data_processing", sa.Boolean, nullable=False, server_default="TRUE"),
        sa.Column("preferred_communication_channel", sa.String(20), nullable=False, server_default="email"),
        sa.Column("language_preference", sa.String(10), nullable=False, server_default="en"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE", name="fk_cp_client"),
        sa.UniqueConstraint("client_id", name="client_profiles_client_uq"),
    )
    op.create_index("idx_client_profiles_client_id", "client_profiles", ["client_id"])

    # ── client_addresses ──────────────────────────────────────────────────────
    op.create_table(
        "client_addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("address_type", sa.String(20), nullable=False),
        sa.Column("line1", sa.String(255), nullable=False),
        sa.Column("line2", sa.String(255)),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(100)),
        sa.Column("postal_code", sa.String(20)),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE", name="fk_ca_client"),
        sa.CheckConstraint("address_type IN ('residential','mailing','business')", name="ca_address_type_chk"),
    )
    op.create_index("idx_client_addresses_client_id", "client_addresses", ["client_id"])

    # ── onboarding_cases ──────────────────────────────────────────────────────
    op.create_table(
        "onboarding_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="INTAKE"),
        sa.Column("current_stage", sa.String(30), nullable=False, server_default="INTAKE"),
        sa.Column("selected_products", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("shared_context", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("assigned_advisor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("sla_deadline", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_oc_client"),
        sa.CheckConstraint("status IN ('INTAKE','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED')", name="oc_status_chk"),
        sa.CheckConstraint("current_stage IN ('INTAKE','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED')", name="oc_stage_chk"),
    )
    op.create_index("idx_oc_client_id", "onboarding_cases", ["client_id"])
    op.create_index("idx_oc_status", "onboarding_cases", ["status"])
    op.create_index("idx_oc_current_stage", "onboarding_cases", ["current_stage"])

    # ── products ──────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="TRUE"),
        sa.Column("required_documents", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("suitability_criteria", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("step_sequence", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("product_code", name="products_code_uq"),
    )
    op.create_index("idx_products_code", "products", ["product_code"])

    # ── case_products ─────────────────────────────────────────────────────────
    op.create_table(
        "case_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_code", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("suitability_outcome", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("account_number", sa.String(100)),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_cp_case"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_cp_product"),
        sa.CheckConstraint("status IN ('PENDING','IN_PROGRESS','COMPLETE','FAILED','SKIPPED')", name="cp_status_chk"),
    )
    op.create_index("idx_case_products_case_id", "case_products", ["case_id"])
    op.create_index("idx_case_products_status", "case_products", ["status"])

    # ── case_product_steps ────────────────────────────────────────────────────
    op.create_table(
        "case_product_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_name", sa.String(100), nullable=False),
        sa.Column("step_index", sa.Integer, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_product_id"], ["case_products.id"], ondelete="CASCADE", name="fk_cps_case_product"),
        sa.CheckConstraint("status IN ('PENDING','IN_PROGRESS','COMPLETE','FAILED','SKIPPED')", name="cps_status_chk"),
    )
    op.create_index("idx_cps_case_product_id", "case_product_steps", ["case_product_id"])

    # ── documents ─────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="NOT_REQUESTED"),
        sa.Column("original_filename", sa.String(500)),
        sa.Column("storage_path", sa.String(1000)),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("ocr_result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("classification_result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("validation_result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("diff_result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("parent_doc_id", postgresql.UUID(as_uuid=True)),
        sa.Column("uploaded_by", sa.String(50)),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("uploaded_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_doc_case"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_doc_client"),
        sa.ForeignKeyConstraint(["parent_doc_id"], ["documents.id"], name="fk_doc_parent"),
        sa.CheckConstraint("category IN ('identity','financial','legal','insurance','compliance','entity')", name="doc_category_chk"),
    )
    op.create_index("idx_docs_case_id", "documents", ["case_id"])
    op.create_index("idx_docs_client_id", "documents", ["client_id"])
    op.create_index("idx_docs_status", "documents", ["status"])
    op.create_index("idx_docs_category", "documents", ["category"])

    # ── kyc_checks ────────────────────────────────────────────────────────────
    op.create_table(
        "kyc_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identity_score", sa.Numeric(5, 4)),
        sa.Column("aml_score", sa.Numeric(5, 4)),
        sa.Column("profile_score", sa.Numeric(5, 4)),
        sa.Column("composite_score", sa.Numeric(5, 4)),
        sa.Column("risk_band", sa.String(20)),
        sa.Column("identity_verification_result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("aml_check_result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("sanctions_check_result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("checkpoint_rules_applied", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("decision", sa.String(30)),
        sa.Column("decision_reason", sa.Text),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_kyc_case"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_kyc_client"),
        sa.CheckConstraint("status IN ('PENDING','PASSED','FAILED','ESCALATED')", name="kyc_status_chk"),
    )
    op.create_index("idx_kyc_case_id", "kyc_checks", ["case_id"])
    op.create_index("idx_kyc_status", "kyc_checks", ["status"])

    # ── human_reviews ─────────────────────────────────────────────────────────
    op.create_table(
        "human_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kyc_check_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True)),
        sa.Column("reviewer_role", sa.String(50)),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("evidence_packet", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("decision", sa.String(30)),
        sa.Column("decision_notes", sa.Text),
        sa.Column("escalation_reason", sa.Text),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_hr_case"),
        sa.ForeignKeyConstraint(["kyc_check_id"], ["kyc_checks.id"], name="fk_hr_kyc_check"),
        sa.CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','MORE_INFO_REQUESTED')", name="hr_status_chk"),
    )
    op.create_index("idx_hr_case_id", "human_reviews", ["case_id"])
    op.create_index("idx_hr_status", "human_reviews", ["status"])

    # ── agents ────────────────────────────────────────────────────────────────
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="TRUE"),
        sa.Column("capabilities", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("llm_provider", sa.String(30)),
        sa.Column("llm_model", sa.String(100)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("agent_id", name="agents_agent_id_uq"),
    )
    op.create_index("idx_agents_agent_id", "agents", ["agent_id"])

    # ── agent_tasks ───────────────────────────────────────────────────────────
    op.create_table(
        "agent_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("from_agent", sa.String(50), nullable=False),
        sa.Column("to_agent", sa.String(50), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("expected_schema", sa.String(200)),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("errors", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("ttl", sa.Integer, nullable=False, server_default="300"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_at_case"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_at_client"),
        sa.CheckConstraint("priority IN ('LOW','NORMAL','HIGH','CRITICAL')", name="at_priority_chk"),
        sa.CheckConstraint("status IN ('PENDING','IN_PROGRESS','SUCCESS','PARTIAL','FAILED','ESCALATED')", name="at_status_chk"),
    )
    op.create_index("idx_at_case_id", "agent_tasks", ["case_id"])
    op.create_index("idx_at_status", "agent_tasks", ["status"])

    # ── event_logs  (append-only) ─────────────────────────────────────────────
    op.create_table(
        "event_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True)),
        sa.Column("client_id", postgresql.UUID(as_uuid=True)),
        sa.Column("agent_id", sa.String(50)),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_category", sa.String(50)),
        sa.Column("entity_type", sa.String(50)),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_id", sa.String(100)),
        sa.Column("actor_role", sa.String(50)),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_compliance_event", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_el_event_type", "event_logs", ["event_type"])
    op.create_index("idx_el_created_at", "event_logs", [sa.text("created_at DESC")])

    # ── mcp_tool_calls ────────────────────────────────────────────────────────
    op.create_table(
        "mcp_tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True)),
        sa.Column("agent_id", sa.String(50), nullable=False),
        sa.Column("connector_name", sa.String(100), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("input_payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("output_payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("is_simulated", sa.Boolean, nullable=False, server_default="TRUE"),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_mcp_case"),
        sa.CheckConstraint("status IN ('PENDING','SUCCESS','FAILED','TIMEOUT')", name="mcp_status_chk"),
    )
    op.create_index("idx_mcp_agent_id", "mcp_tool_calls", ["agent_id"])
    op.create_index("idx_mcp_tool_name", "mcp_tool_calls", ["tool_name"])

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True)),
        sa.Column("client_id", postgresql.UUID(as_uuid=True)),
        sa.Column("template_name", sa.String(100)),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("recipient_email", sa.String(255)),
        sa.Column("recipient_phone", sa.String(50)),
        sa.Column("subject", sa.Text),
        sa.Column("body", sa.Text),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("is_simulated", sa.Boolean, nullable=False, server_default="TRUE"),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_notif_case"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_notif_client"),
        sa.CheckConstraint("channel IN ('email','sms','in_app')", name="notif_channel_chk"),
        sa.CheckConstraint("status IN ('PENDING','SENT','FAILED','BOUNCED')", name="notif_status_chk"),
    )
    op.create_index("idx_notif_status", "notifications", ["status"])

    # ── case_summaries ────────────────────────────────────────────────────────
    op.create_table(
        "case_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("model_used", sa.String(100)),
        sa.Column("generated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_cs_case"),
        sa.CheckConstraint("summary_type IN ('call_summary','stage_summary','ai_summary')", name="cs_type_chk"),
    )
    op.create_index("idx_cs_case_id", "case_summaries", ["case_id"])

    # ── collaboration_rooms ───────────────────────────────────────────────────
    op.create_table(
        "collaboration_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_name", sa.String(200)),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_cr_case"),
        sa.CheckConstraint("status IN ('OPEN','CLOSED','ARCHIVED')", name="cr_status_chk"),
    )
    op.create_index("idx_cr_case_id", "collaboration_rooms", ["case_id"])

    # ── collaboration_participants ────────────────────────────────────────────
    op.create_table(
        "collaboration_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", sa.String(100), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("joined_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("left_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["room_id"], ["collaboration_rooms.id"], ondelete="CASCADE", name="fk_cpart_room"),
        sa.CheckConstraint("role IN ('Advisor','Client','ComplianceOfficer','CCRep','system')", name="cpart_role_chk"),
    )
    op.create_index("idx_cpart_room_id", "collaboration_participants", ["room_id"])

    # ── collaboration_comments ────────────────────────────────────────────────
    op.create_table(
        "collaboration_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", sa.String(100), nullable=False),
        sa.Column("author_role", sa.String(50)),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("visibility", sa.String(30), nullable=False, server_default="team"),
        sa.Column("document_id", postgresql.UUID(as_uuid=True)),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["room_id"], ["collaboration_rooms.id"], ondelete="CASCADE", name="fk_cc_room"),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_cc_case"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_cc_document"),
        sa.ForeignKeyConstraint(["parent_id"], ["collaboration_comments.id"], name="fk_cc_parent"),
        sa.CheckConstraint("visibility IN ('team','client_visible','compliance_only')", name="cc_visibility_chk"),
    )
    op.create_index("idx_cc_room_id", "collaboration_comments", ["room_id"])
    op.create_index("idx_cc_case_id", "collaboration_comments", ["case_id"])

    # ── conversation_messages ─────────────────────────────────────────────────
    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tokens_used", sa.Integer),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_cm_case"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_cm_client"),
        sa.CheckConstraint("role IN ('user','assistant','system')", name="cm_role_chk"),
    )
    op.create_index("idx_cm_case_id", "conversation_messages", ["case_id"])

    # ── onboarding_questionnaires ─────────────────────────────────────────────
    op.create_table(
        "onboarding_questionnaires",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="TRUE"),
        sa.Column("sections", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── onboarding_questions ──────────────────────────────────────────────────
    op.create_table(
        "onboarding_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("questionnaire_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section", sa.String(100), nullable=False),
        sa.Column("question_key", sa.String(100), nullable=False),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("question_type", sa.String(30), nullable=False),
        sa.Column("options", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("validation_rules", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("show_if", postgresql.JSONB),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="TRUE"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["questionnaire_id"], ["onboarding_questionnaires.id"], ondelete="CASCADE", name="fk_oqn_questionnaire"),
        sa.UniqueConstraint("questionnaire_id", "question_key", name="oqn_key_uq"),
        sa.CheckConstraint("question_type IN ('text','number','select','multi_select','date','boolean','currency')", name="oqn_type_chk"),
    )
    op.create_index("idx_oqn_questionnaire_id", "onboarding_questions", ["questionnaire_id"])
    op.create_index("idx_oqn_section", "onboarding_questions", ["section"])

    # ── onboarding_question_rules ─────────────────────────────────────────────
    op.create_table(
        "onboarding_question_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("condition", postgresql.JSONB, nullable=False),
        sa.Column("action", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["question_id"], ["onboarding_questions.id"], ondelete="CASCADE", name="fk_oqr_question"),
        sa.CheckConstraint("rule_type IN ('show_if','validate','skip','require')", name="oqr_rule_type_chk"),
    )
    op.create_index("idx_oqr_question_id", "onboarding_question_rules", ["question_id"])

    # ── onboarding_answers ────────────────────────────────────────────────────
    op.create_table(
        "onboarding_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("questionnaire_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_key", sa.String(100), nullable=False),
        sa.Column("answer_value", postgresql.JSONB),
        sa.Column("answered_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_oa_case"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_oa_client"),
        sa.ForeignKeyConstraint(["questionnaire_id"], ["onboarding_questionnaires.id"], name="fk_oa_questionnaire"),
        sa.ForeignKeyConstraint(["question_id"], ["onboarding_questions.id"], name="fk_oa_question"),
        sa.UniqueConstraint("case_id", "question_id", name="oa_case_question_uq"),
    )
    op.create_index("idx_oa_case_id", "onboarding_answers", ["case_id"])
    op.create_index("idx_oa_client_id", "onboarding_answers", ["client_id"])

    # ── onboarding_question_sessions ──────────────────────────────────────────
    op.create_table(
        "onboarding_question_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("questionnaire_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("current_section", sa.String(100)),
        sa.Column("current_question_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_sections", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("session_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("paused_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("resumed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["case_id"], ["onboarding_cases.id"], name="fk_oqs_case"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_oqs_client"),
        sa.ForeignKeyConstraint(["questionnaire_id"], ["onboarding_questionnaires.id"], name="fk_oqs_questionnaire"),
        sa.UniqueConstraint("case_id", "questionnaire_id", name="oqs_case_q_uq"),
        sa.CheckConstraint("status IN ('IN_PROGRESS','PAUSED','COMPLETED','ABANDONED')", name="oqs_status_chk"),
    )
    op.create_index("idx_oqs_case_id", "onboarding_question_sessions", ["case_id"])
    op.create_index("idx_oqs_status", "onboarding_question_sessions", ["status"])


def downgrade() -> None:
    op.drop_table("onboarding_question_sessions")
    op.drop_table("onboarding_answers")
    op.drop_table("onboarding_question_rules")
    op.drop_table("onboarding_questions")
    op.drop_table("onboarding_questionnaires")
    op.drop_table("conversation_messages")
    op.drop_table("collaboration_comments")
    op.drop_table("collaboration_participants")
    op.drop_table("collaboration_rooms")
    op.drop_table("case_summaries")
    op.drop_table("notifications")
    op.drop_table("mcp_tool_calls")
    op.drop_table("event_logs")
    op.drop_table("agent_tasks")
    op.drop_table("agents")
    op.drop_table("human_reviews")
    op.drop_table("kyc_checks")
    op.drop_table("documents")
    op.drop_table("case_product_steps")
    op.drop_table("case_products")
    op.drop_table("products")
    op.drop_table("onboarding_cases")
    op.drop_table("client_addresses")
    op.drop_table("client_profiles")
    op.drop_table("clients")
    op.execute("DROP TYPE IF EXISTS document_status")
