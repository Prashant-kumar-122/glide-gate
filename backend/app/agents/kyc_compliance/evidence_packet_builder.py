from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    label: str
    value: Any
    source: str
    risk_relevant: bool = False


class EvidencePacket(BaseModel):
    packet_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    client_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    verification_result: dict[str, Any]
    risk_score: dict[str, Any]
    profile_summary: dict[str, Any]
    checkpoint_decisions: list[dict[str, Any]]
    items: list[EvidenceItem] = Field(default_factory=list)
    review_notes: str = ""


class EvidencePacketBuilder:
    """Assembles a structured evidence packet for human review (BRD FR-13)."""

    def build(
        self,
        case_id: UUID,
        client_id: UUID,
        client_data: dict[str, Any],
        verification_result: dict[str, Any],
        risk_score: dict[str, Any],
        checkpoint_decisions: list[dict[str, Any]],
    ) -> EvidencePacket:
        return EvidencePacket(
            case_id=case_id,
            client_id=client_id,
            verification_result=verification_result,
            risk_score=risk_score,
            profile_summary=self._summarise_profile(client_data),
            checkpoint_decisions=checkpoint_decisions,
            items=self._extract_items(client_data, verification_result, risk_score),
        )

    def _summarise_profile(self, d: dict[str, Any]) -> dict[str, Any]:
        return {
            "full_name": d.get("full_name"),
            "nationality": d.get("nationality"),
            "tax_residency": d.get("tax_residency"),
            "employment_status": d.get("employment_status"),
            "annual_income_band": self._income_band(float(d.get("annual_income") or 0)),
            "net_worth_band": self._wealth_band(float(d.get("net_worth") or 0)),
            "source_of_funds": d.get("source_of_funds"),
            "investment_experience": d.get("investment_experience"),
            "risk_tolerance": d.get("risk_tolerance"),
        }

    @staticmethod
    def _income_band(income: float) -> str:
        if income < 50_000:
            return "< 50k"
        if income < 100_000:
            return "50k–100k"
        if income < 250_000:
            return "100k–250k"
        if income < 500_000:
            return "250k–500k"
        if income < 1_000_000:
            return "500k–1M"
        return "> 1M"

    @staticmethod
    def _wealth_band(nw: float) -> str:
        if nw < 100_000:
            return "< 100k"
        if nw < 500_000:
            return "100k–500k"
        if nw < 1_000_000:
            return "500k–1M"
        if nw < 5_000_000:
            return "1M–5M"
        if nw < 10_000_000:
            return "5M–10M"
        return "> 10M"

    def _extract_items(
        self,
        client_data: dict[str, Any],
        verification: dict[str, Any],
        risk_score: dict[str, Any],
    ) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []

        items.append(EvidenceItem(
            label="Identity Verification",
            value={
                "document_authentic": verification.get("document_authentic"),
                "document_valid": verification.get("document_valid"),
                "name_match_confidence": verification.get("name_match_confidence"),
                "provider": verification.get("provider"),
            },
            source="identity_verification_mcp",
            risk_relevant=not verification.get("document_authentic", True),
        ))

        sanctions = verification.get("sanctions_match", False)
        pep = verification.get("pep_match", False)
        aml_factors = verification.get("aml_risk_factors", [])
        items.append(EvidenceItem(
            label="Sanctions & AML Screening",
            value={
                "sanctions_match": sanctions,
                "pep_match": pep,
                "aml_risk_factors": aml_factors,
                "aml_risk_level": verification.get("aml_risk_level"),
            },
            source="identity_verification_mcp",
            risk_relevant=bool(sanctions or pep or aml_factors),
        ))

        items.append(EvidenceItem(
            label="Composite Risk Score",
            value=risk_score,
            source="risk_scorer",
            risk_relevant=float(risk_score.get("composite_score", 0)) > 30,
        ))

        source_of_funds = client_data.get("source_of_funds")
        if source_of_funds:
            items.append(EvidenceItem(
                label="Source of Funds",
                value={
                    "source_of_funds": source_of_funds,
                    "source_of_wealth_detail": client_data.get("source_of_wealth_detail"),
                },
                source="client_questionnaire",
                risk_relevant=source_of_funds == "Other",
            ))

        return items
