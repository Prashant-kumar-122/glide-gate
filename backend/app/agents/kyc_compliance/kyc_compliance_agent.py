from __future__ import annotations

import random
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.agents.base.a2a_types import (
    AgentID,
    OnboardingStage,
    TaskPacket,
    TaskResponse,
    TaskType,
)
from app.agents.base.base_agent import BaseAgent
from app.agents.kyc_compliance.checkpoint_rule_engine import CheckpointRuleEngine
from app.agents.kyc_compliance.evidence_packet_builder import EvidencePacketBuilder
from app.agents.kyc_compliance.risk_scorer import RiskScorer

_HIGH_RISK_NATIONALITIES = {
    "iran", "north korea", "syria", "cuba", "venezuela",
    "myanmar", "belarus", "russia",
}


class KYCComplianceAgent(BaseAgent):
    """
    KYC & Compliance Agent (BRD Section 6.1, FR-04, FR-13, FR-14, FR-15).

    Handles:
    - RUN_KYC_CHECK   — full pipeline: verify → score → checkpoint → route
    - VERIFY_IDENTITY — standalone identity verification (returns raw result)

    On completion signals ADVANCE_STAGE (PARALLEL_PRODUCTS) or ESCALATE.
    MCP identity verification is simulated here; replaced by real MCP in STEP-16.
    """

    agent_id = AgentID.KYC_COMPLIANCE

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._scorer = RiskScorer()
        self._evidence_builder = EvidencePacketBuilder()
        self._rule_engine = CheckpointRuleEngine()

    async def process(self, task: TaskPacket) -> TaskResponse:
        handlers = {
            TaskType.RUN_KYC_CHECK: self._handle_run_kyc,
            TaskType.VERIFY_IDENTITY: self._handle_verify_identity,
        }
        handler = handlers.get(task.task_type)
        if handler is None:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=[f"Unsupported task_type: {task.task_type}"],
            )
        return await handler(task)

    # ── Task handlers ─────────────────────────────────────────────────────────

    async def _handle_run_kyc(self, task: TaskPacket) -> TaskResponse:
        client_data: dict[str, Any] = task.payload.get("client_data", {})
        selected_products: list[str] = task.payload.get("selected_products", [])

        self.logger.info(
            f"Running KYC check for case={task.case_id} products={selected_products}"
        )

        verification = await self._simulate_identity_verification(client_data)
        risk_score = self._scorer.compute(client_data, verification)
        checkpoint = self._rule_engine.evaluate(
            risk_score=risk_score.model_dump(),
            client_data=client_data,
            verification_result=verification,
            selected_products=selected_products,
        )
        evidence = self._evidence_builder.build(
            case_id=task.case_id,
            client_id=task.client_id,
            client_data=client_data,
            verification_result=verification,
            risk_score=risk_score.model_dump(),
            checkpoint_decisions=[d.model_dump() for d in checkpoint.decisions],
        )

        authentic = verification.get("document_authentic", True)
        if checkpoint.should_escalate:
            kyc_status = "ESCALATED"
        elif not authentic:
            kyc_status = "FAILED"
        else:
            kyc_status = "PASSED"

        self.logger.info(
            f"KYC result for case={task.case_id}: status={kyc_status} "
            f"risk_band={risk_score.risk_band} composite={risk_score.composite_score:.1f}"
        )

        await self._signal_outcome(task, kyc_status, risk_score, checkpoint, evidence)

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS" if kyc_status != "FAILED" else "FAILED",
            result={
                "kyc_status": kyc_status,
                "risk_band": risk_score.risk_band,
                "composite_score": risk_score.composite_score,
                "identity_score": risk_score.identity_score,
                "aml_score": risk_score.aml_score,
                "profile_score": risk_score.profile_score,
                "should_escalate": checkpoint.should_escalate,
                "escalation_reasons": checkpoint.escalation_reasons,
                "required_documents": checkpoint.required_documents,
                "evidence_packet_id": str(evidence.packet_id),
                "verification_id": verification.get("verification_id"),
                "checked_at": verification.get("checked_at"),
            },
        )

    async def _handle_verify_identity(self, task: TaskPacket) -> TaskResponse:
        client_data: dict[str, Any] = task.payload.get("client_data", {})
        verification = await self._simulate_identity_verification(client_data)
        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result=verification,
        )

    # ── Orchestrator signalling ───────────────────────────────────────────────

    async def _signal_outcome(
        self,
        task: TaskPacket,
        kyc_status: str,
        risk_score: Any,
        checkpoint: Any,
        evidence: Any,
    ) -> None:
        if self._bus is None:
            self.logger.warning(
                f"No event bus; cannot signal KYC outcome for case={task.case_id}"
            )
            return

        if checkpoint.should_escalate:
            await self.send_task(TaskPacket(
                from_agent=self.agent_id,
                to_agent=AgentID.ORCHESTRATOR,
                task_type=TaskType.ESCALATE,
                case_id=task.case_id,
                client_id=task.client_id,
                priority="HIGH",
                payload={
                    "reason": "; ".join(checkpoint.escalation_reasons),
                    "kyc_status": kyc_status,
                    "risk_band": risk_score.risk_band,
                    "composite_score": risk_score.composite_score,
                    "evidence_packet_id": str(evidence.packet_id),
                    "required_documents": checkpoint.required_documents,
                },
            ))
        elif kyc_status == "PASSED":
            await self.send_task(TaskPacket(
                from_agent=self.agent_id,
                to_agent=AgentID.ORCHESTRATOR,
                task_type=TaskType.ADVANCE_STAGE,
                case_id=task.case_id,
                client_id=task.client_id,
                priority="HIGH",
                payload={
                    "to_stage": OnboardingStage.PARALLEL_PRODUCTS,
                    "kyc_status": kyc_status,
                    "risk_band": risk_score.risk_band,
                    "required_documents": checkpoint.required_documents,
                    "selected_products": task.payload.get("selected_products", []),
                },
            ))

    # ── Simulated MCP identity verification ───────────────────────────────────

    async def _simulate_identity_verification(
        self, client_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Simulates the MCP Identity Verification connector (STEP-16).
        Deterministic seed from id_number for reproducible demo results.
        """
        import asyncio

        latency = random.uniform(0.2, 0.8)
        await asyncio.sleep(latency)

        id_number = str(client_data.get("id_number") or "DEFAULT")
        rng = random.Random(sum(ord(c) for c in id_number))

        name_confidence = round(rng.uniform(0.87, 0.99), 4)
        document_authentic = rng.random() > 0.04  # 96% authentic

        nationality = (client_data.get("nationality") or "").lower()
        sanctions_match = nationality in _HIGH_RISK_NATIONALITIES
        pep_match = rng.random() < 0.03  # 3% PEP rate

        aml_risk_factors: list[str] = []
        if float(client_data.get("annual_income") or 0) > 1_000_000:
            aml_risk_factors.append("high_income")
        if client_data.get("source_of_funds") == "Other":
            aml_risk_factors.append("undisclosed_source_of_funds")
        if sanctions_match:
            aml_risk_factors.append("high_risk_jurisdiction_nationality")
        if pep_match:
            aml_risk_factors.append("politically_exposed_person")

        if sanctions_match or pep_match:
            aml_risk_level = "HIGH"
        elif len(aml_risk_factors) > 1:
            aml_risk_level = "MEDIUM"
        elif aml_risk_factors:
            aml_risk_level = "LOW"
        else:
            aml_risk_level = "LOW"

        return {
            "verification_id": str(uuid4()),
            "name_match_confidence": name_confidence,
            "document_authentic": document_authentic,
            "document_valid": True,
            "sanctions_match": sanctions_match,
            "pep_match": pep_match,
            "aml_risk_factors": aml_risk_factors,
            "aml_risk_level": aml_risk_level,
            "latency_ms": round(latency * 1000),
            "checked_at": datetime.utcnow().isoformat(),
            "provider": "simulated_identity_verification_v1",
            "is_simulated": True,
        }
