from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cases import OnboardingCase
from app.models.clients import Client, ClientProfile
from app.models.documents import Document
from app.models.kyc_reviews import KYCCheck


class EvidencePacketAssembler:
    """
    Assembles a structured evidence packet from DB records for human review.

    Pulls together KYC scores, client profile, required documents, and
    checkpoint decisions into a single serialisable dict stored in
    human_reviews.evidence_packet.
    """

    async def assemble(
        self,
        case_id: UUID,
        client_id: UUID,
        kyc_result: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        client_summary = await self._load_client_summary(client_id, db)
        document_summary = await self._load_document_summary(case_id, db)
        case_summary = await self._load_case_summary(case_id, db)

        return {
            "case_id": str(case_id),
            "client_id": str(client_id),
            "assembled_at": _utcnow(),
            "kyc_result": {
                "kyc_status": kyc_result.get("kyc_status"),
                "risk_band": kyc_result.get("risk_band"),
                "composite_score": kyc_result.get("composite_score"),
                "identity_score": kyc_result.get("identity_score"),
                "aml_score": kyc_result.get("aml_score"),
                "profile_score": kyc_result.get("profile_score"),
                "should_escalate": kyc_result.get("should_escalate"),
                "escalation_reasons": kyc_result.get("escalation_reasons", []),
                "required_documents": kyc_result.get("required_documents", []),
                "verification_id": kyc_result.get("verification_id"),
                "checked_at": kyc_result.get("checked_at"),
                "evidence_packet_id": kyc_result.get("evidence_packet_id"),
            },
            "client_summary": client_summary,
            "document_summary": document_summary,
            "case_summary": case_summary,
        }

    async def assemble_from_agent_payload(
        self,
        case_id: UUID,
        client_id: UUID,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Convenience wrapper when called from the orchestrator with a raw escalation payload."""
        return await self.assemble(
            case_id=case_id,
            client_id=client_id,
            kyc_result=payload,
            db=db,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _load_client_summary(
        self, client_id: UUID, db: AsyncSession
    ) -> dict[str, Any]:
        result = await db.execute(
            select(Client, ClientProfile)
            .outerjoin(ClientProfile, ClientProfile.client_id == Client.id)
            .where(Client.id == client_id)
        )
        row = result.first()
        if row is None:
            return {"client_id": str(client_id)}

        client, profile = row
        summary: dict[str, Any] = {
            "full_name": getattr(client, "full_name", None),
            "email": getattr(client, "email", None),
            "phone": getattr(client, "phone", None),
        }
        if profile:
            summary.update({
                "nationality": profile.nationality,
                "date_of_birth": str(profile.date_of_birth) if profile.date_of_birth else None,
                "occupation": profile.occupation,
                "annual_income": float(profile.annual_income) if profile.annual_income else None,
                "source_of_funds": profile.source_of_funds,
                "risk_tolerance": profile.risk_tolerance,
                "investment_experience": profile.investment_experience,
            })
        return summary

    async def _load_document_summary(
        self, case_id: UUID, db: AsyncSession
    ) -> dict[str, Any]:
        result = await db.execute(
            select(Document).where(Document.case_id == case_id)
        )
        docs = result.scalars().all()

        by_status: dict[str, int] = {}
        categories_missing: list[str] = []
        seen_categories: set[str] = set()

        for doc in docs:
            by_status[doc.status] = by_status.get(doc.status, 0) + 1
            seen_categories.add(doc.category)

        all_required = {"identity", "financial", "compliance"}
        categories_missing = list(all_required - seen_categories)

        return {
            "total": len(docs),
            "by_status": by_status,
            "categories_present": list(seen_categories),
            "categories_missing": categories_missing,
        }

    async def _load_case_summary(
        self, case_id: UUID, db: AsyncSession
    ) -> dict[str, Any]:
        result = await db.execute(
            select(OnboardingCase).where(OnboardingCase.id == case_id)
        )
        case = result.scalar_one_or_none()
        if case is None:
            return {"case_id": str(case_id)}

        return {
            "current_stage": case.current_stage,
            "status": case.status,
            "selected_products": case.selected_products or [],
            "created_at": case.created_at.isoformat() if case.created_at else None,
        }


def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# Module-level singleton
evidence_packet_assembler = EvidencePacketAssembler()
