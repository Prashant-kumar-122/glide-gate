from __future__ import annotations

from string import Template
from typing import Any


class NotificationTemplate:
    __slots__ = ("template_id", "channel", "subject_tmpl", "body_tmpl")

    def __init__(
        self,
        template_id: str,
        channel: str,
        subject_tmpl: str,
        body_tmpl: str,
    ) -> None:
        self.template_id = template_id
        self.channel = channel
        self.subject_tmpl = subject_tmpl
        self.body_tmpl = body_tmpl

    def render(self, variables: dict[str, Any]) -> dict[str, str]:
        safe_vars = {k: str(v) for k, v in variables.items()}
        return {
            "subject": Template(self.subject_tmpl).safe_substitute(safe_vars),
            "body": Template(self.body_tmpl).safe_substitute(safe_vars),
            "channel": self.channel,
            "template_id": self.template_id,
        }


_REGISTRY: dict[str, NotificationTemplate] = {
    # ── Case created ──────────────────────────────────────────────────────────
    "onboarding_started": NotificationTemplate(
        template_id="onboarding_started",
        channel="email",
        subject_tmpl="Welcome to GlideGate — $case_name",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "Your GlideGate onboarding application **$case_name** has been initiated "
            "for the following product(s): $products.\n\n"
            "Your dedicated advisor will guide you through the next steps. "
            "You can track your progress in the client portal at any time.\n\n"
            "Kind regards,\nThe GlideGate Onboarding Team"
        ),
    ),
    "case_created_inapp": NotificationTemplate(
        template_id="case_created_inapp",
        channel="in_app",
        subject_tmpl="Case created — $case_name",
        body_tmpl=(
            "Hi $client_name! Your application **$case_name** for $products has been received. "
            "We'll guide you through each step in the client portal."
        ),
    ),

    # ── Case submitted ────────────────────────────────────────────────────────
    "case_submitted": NotificationTemplate(
        template_id="case_submitted",
        channel="email",
        subject_tmpl="Application Submitted — $case_name",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "Your application **$case_name** has been submitted successfully. "
            "Our team will now review your documents and complete the necessary checks.\n\n"
            "Product(s): $products\n\n"
            "We'll be in touch within 1–2 business days.\n\n"
            "Kind regards,\nThe GlideGate Onboarding Team"
        ),
    ),
    "case_submitted_inapp": NotificationTemplate(
        template_id="case_submitted_inapp",
        channel="in_app",
        subject_tmpl="Application submitted — $case_name",
        body_tmpl=(
            "Your application **$case_name** has been submitted. "
            "We'll review your documents and be in touch shortly."
        ),
    ),
    "advisor_case_submitted_inapp": NotificationTemplate(
        template_id="advisor_case_submitted_inapp",
        channel="in_app",
        subject_tmpl="Case submitted — $case_name",
        body_tmpl=(
            "$client_name has submitted their application for **$case_name**. "
            "Products: $products. Please review the documents."
        ),
    ),

    # ── KYC ───────────────────────────────────────────────────────────────────
    "kyc_passed": NotificationTemplate(
        template_id="kyc_passed",
        channel="email",
        subject_tmpl="Identity Verification Complete — $case_name",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "We are pleased to confirm that your identity verification for **$case_name** "
            "has been completed successfully. We are now proceeding with setting up your "
            "account(s): $products.\n\n"
            "Kind regards,\nThe GlideGate Onboarding Team"
        ),
    ),
    "kyc_failed": NotificationTemplate(
        template_id="kyc_failed",
        channel="email",
        subject_tmpl="Action Required — Identity Verification ($case_name)",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "Unfortunately, we were unable to complete your identity verification "
            "for application **$case_name**. "
            "Please contact your advisor or our support team for assistance.\n\n"
            "Kind regards,\nThe GlideGate Compliance Team"
        ),
    ),
    "kyc_failed_inapp": NotificationTemplate(
        template_id="kyc_failed_inapp",
        channel="in_app",
        subject_tmpl="Identity Verification Failed — $case_name",
        body_tmpl=(
            "We were unable to verify your identity for application **$case_name**. "
            "Please contact your advisor for assistance."
        ),
    ),
    "kyc_escalated": NotificationTemplate(
        template_id="kyc_escalated",
        channel="email",
        subject_tmpl="Your Application Is Under Review — $case_name",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "Your application **$case_name** requires additional compliance review. "
            "Our team will be in touch within 1–2 business days.\n\n"
            "Kind regards,\nThe GlideGate Compliance Team"
        ),
    ),

    # ── Documents ─────────────────────────────────────────────────────────────
    "document_requested": NotificationTemplate(
        template_id="document_requested",
        channel="email",
        subject_tmpl="Documents Required — $case_name",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "To proceed with your application **$case_name**, we require the following "
            "document(s): $document_name.\n\n"
            "Please upload them via your client portal.\n\n"
            "Kind regards,\nThe GlideGate Onboarding Team"
        ),
    ),
    "document_requested_inapp": NotificationTemplate(
        template_id="document_requested_inapp",
        channel="in_app",
        subject_tmpl="Document required — $document_name",
        body_tmpl=(
            "Your advisor has requested: **$document_name**. "
            "Please upload it via your client portal."
        ),
    ),
    "document_approved": NotificationTemplate(
        template_id="document_approved",
        channel="in_app",
        subject_tmpl="Document Approved — $document_name",
        body_tmpl="Your document **$document_name** has been reviewed and approved.",
    ),
    "document_needs_revision": NotificationTemplate(
        template_id="document_needs_revision",
        channel="in_app",
        subject_tmpl="Revision Required — $document_name",
        body_tmpl=(
            "Your document **$document_name** requires revision. "
            "Reason: $revision_reason. "
            "Please re-upload an updated version."
        ),
    ),
    "document_comment": NotificationTemplate(
        template_id="document_comment",
        channel="email",
        subject_tmpl="New Comment on $case_name — GlideGate",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "$author_name has added a comment on your application **$case_name**:\n\n"
            "\"$comment_body\"\n\n"
            "Please log in to your GlideGate portal to view and respond.\n\n"
            "Kind regards,\nThe GlideGate Team"
        ),
    ),

    # ── Product track ─────────────────────────────────────────────────────────
    "product_track_update": NotificationTemplate(
        template_id="product_track_update",
        channel="in_app",
        subject_tmpl="Product Account Update — $product_name",
        body_tmpl=(
            "Your $product_name account setup is $track_status. "
            "Steps completed: $steps_completed of $total_steps."
        ),
    ),
    "product_track_failed": NotificationTemplate(
        template_id="product_track_failed",
        channel="email",
        subject_tmpl="Account Setup Issue — $product_name ($case_name)",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "Unfortunately, we encountered an issue setting up your $product_name account "
            "as part of application **$case_name**. "
            "Our team has been notified and will contact you within 1 business day.\n\n"
            "Kind regards,\nThe GlideGate Onboarding Team"
        ),
    ),
    "product_track_failed_inapp": NotificationTemplate(
        template_id="product_track_failed_inapp",
        channel="in_app",
        subject_tmpl="Account Setup Issue — $product_name",
        body_tmpl=(
            "We encountered an issue setting up your $product_name account "
            "for application **$case_name**. "
            "Our team will contact you within 1 business day."
        ),
    ),

    # ── Onboarding complete ───────────────────────────────────────────────────
    "onboarding_complete": NotificationTemplate(
        template_id="onboarding_complete",
        channel="email",
        subject_tmpl="Your GlideGate Account Is Ready — $case_name",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "Congratulations! Your GlideGate account(s) for application **$case_name** "
            "are now active.\n\n"
            "Product(s): $products\n"
            "Account Number(s): $account_numbers\n\n"
            "You can access your portfolio and manage your account(s) through "
            "the GlideGate client portal.\n\n"
            "Welcome aboard,\nThe GlideGate Team"
        ),
    ),
    "onboarding_complete_inapp": NotificationTemplate(
        template_id="onboarding_complete_inapp",
        channel="in_app",
        subject_tmpl="Your accounts are ready — $case_name",
        body_tmpl=(
            "Congratulations $client_name! Your $products account(s) for **$case_name** "
            "are now active. Account Number(s): $account_numbers. Welcome to GlideGate!"
        ),
    ),

    # ── Compliance / escalation ───────────────────────────────────────────────
    "escalation_alert": NotificationTemplate(
        template_id="escalation_alert",
        channel="email",
        subject_tmpl="[URGENT] Compliance Escalation — $case_name",
        body_tmpl=(
            "Compliance Officer,\n\n"
            "A KYC escalation has been triggered for application **$case_name** "
            "(client: $client_name).\n\n"
            "Risk band: $risk_band\n"
            "Reason: $escalation_reason\n"
            "Evidence packet: $evidence_packet_id\n\n"
            "Please review at your earliest convenience.\n\n"
            "GlideGate Automated Compliance System"
        ),
    ),
    "human_review_decided": NotificationTemplate(
        template_id="human_review_decided",
        channel="email",
        subject_tmpl="Compliance Review Decision — $case_name",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "A compliance review of your application **$case_name** has been completed. "
            "Decision: $decision.\n\n"
            "$decision_notes\n\n"
            "Kind regards,\nThe GlideGate Compliance Team"
        ),
    ),

    # ── Advisor notifications ─────────────────────────────────────────────────
    "advisor_case_assigned": NotificationTemplate(
        template_id="advisor_case_assigned",
        channel="email",
        subject_tmpl="New Onboarding Case Assigned — $case_name",
        body_tmpl=(
            "Dear Advisor,\n\n"
            "A new onboarding case has been assigned to you.\n\n"
            "Case: $case_name\n"
            "Client: $client_name\n"
            "Products: $products\n\n"
            "Please log in to the GlideGate Advisor Portal to review and process this case.\n\n"
            "GlideGate Onboarding System"
        ),
    ),
    "advisor_case_assigned_inapp": NotificationTemplate(
        template_id="advisor_case_assigned_inapp",
        channel="in_app",
        subject_tmpl="New case assigned — $case_name",
        body_tmpl=(
            "A new onboarding case **$case_name** for $client_name has been assigned to you. "
            "Products: $products."
        ),
    ),
}


def get_template(template_id: str) -> NotificationTemplate | None:
    return _REGISTRY.get(template_id)


def list_templates() -> list[str]:
    return list(_REGISTRY.keys())
