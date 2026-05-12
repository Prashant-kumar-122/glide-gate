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
    "onboarding_started": NotificationTemplate(
        template_id="onboarding_started",
        channel="email",
        subject_tmpl="Welcome to GlideGate — Your onboarding has started",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "Your GlideGate wealth management onboarding has been initiated "
            "for the following product(s): $products.\n\n"
            "Your dedicated advisor will guide you through the next steps. "
            "You can track your progress in the client portal at any time.\n\n"
            "Kind regards,\nThe GlideGate Onboarding Team"
        ),
    ),
    "kyc_passed": NotificationTemplate(
        template_id="kyc_passed",
        channel="email",
        subject_tmpl="Identity Verification Complete — GlideGate",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "We are pleased to confirm that your identity verification has been "
            "completed successfully. We are now proceeding with setting up your "
            "account(s): $products.\n\n"
            "Kind regards,\nThe GlideGate Onboarding Team"
        ),
    ),
    "kyc_failed": NotificationTemplate(
        template_id="kyc_failed",
        channel="email",
        subject_tmpl="Action Required — Identity Verification",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "Unfortunately, we were unable to complete your identity verification. "
            "Please contact your advisor or our support team for assistance.\n\n"
            "Reference: $case_id\n\n"
            "Kind regards,\nThe GlideGate Compliance Team"
        ),
    ),
    "kyc_escalated": NotificationTemplate(
        template_id="kyc_escalated",
        channel="email",
        subject_tmpl="Your Application Is Under Review — GlideGate",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "Your application requires additional compliance review. "
            "Our team will be in touch within 1–2 business days.\n\n"
            "Reference: $case_id\n\n"
            "Kind regards,\nThe GlideGate Compliance Team"
        ),
    ),
    "document_requested": NotificationTemplate(
        template_id="document_requested",
        channel="email",
        subject_tmpl="Documents Required — GlideGate Onboarding",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "To proceed with your onboarding, we require the following document(s): "
            "$document_list.\n\n"
            "Please upload them via your client portal.\n\n"
            "Kind regards,\nThe GlideGate Onboarding Team"
        ),
    ),
    "document_approved": NotificationTemplate(
        template_id="document_approved",
        channel="in_app",
        subject_tmpl="Document Approved",
        body_tmpl="Your $document_type has been reviewed and approved.",
    ),
    "document_needs_revision": NotificationTemplate(
        template_id="document_needs_revision",
        channel="in_app",
        subject_tmpl="Document Revision Required",
        body_tmpl=(
            "Your $document_type requires revision. "
            "Reason: $revision_reason. "
            "Please re-upload an updated version."
        ),
    ),
    "product_track_update": NotificationTemplate(
        template_id="product_track_update",
        channel="in_app",
        subject_tmpl="Product Account Update — $product_name",
        body_tmpl=(
            "Your $product_name account setup is $track_status. "
            "Steps completed: $steps_completed of $total_steps."
        ),
    ),
    "onboarding_complete": NotificationTemplate(
        template_id="onboarding_complete",
        channel="email",
        subject_tmpl="Your GlideGate Account Is Ready",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "Congratulations! Your GlideGate account(s) are now active: $products.\n\n"
            "You can access your portfolio and manage your account(s) through "
            "the GlideGate client portal.\n\n"
            "Welcome aboard,\nThe GlideGate Team"
        ),
    ),
    "escalation_alert": NotificationTemplate(
        template_id="escalation_alert",
        channel="email",
        subject_tmpl="[URGENT] Compliance Escalation — Case $case_id",
        body_tmpl=(
            "Compliance Officer,\n\n"
            "A KYC escalation has been triggered for case $case_id (client: $client_name).\n\n"
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
        subject_tmpl="Compliance Review Decision — Case $case_id",
        body_tmpl=(
            "Dear $client_name,\n\n"
            "A compliance review of your application has been completed. "
            "Decision: $decision.\n\n"
            "$decision_notes\n\n"
            "Kind regards,\nThe GlideGate Compliance Team"
        ),
    ),
}


def get_template(template_id: str) -> NotificationTemplate | None:
    return _REGISTRY.get(template_id)


def list_templates() -> list[str]:
    return list(_REGISTRY.keys())
