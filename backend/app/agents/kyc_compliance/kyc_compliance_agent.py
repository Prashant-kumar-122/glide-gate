from __future__ import annotations

import random
from datetime import datetime, timezone
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
import app.services.compliance.checkpoint_rule_repository as rule_repo
from app.services.compliance.compliance_decision_logger import compliance_decision_logger

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

        verification = await self._simulate_identity_verification(client_data, case_id=task.case_id)
        risk_score = self._scorer.compute(client_data, verification)
        # Build engine fresh each call so admin-configured rules take effect immediately
        checkpoint = CheckpointRuleEngine(rules=rule_repo.get_all()).evaluate(
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
        import asyncio
        from sqlalchemy import update as sa_update
        from app.database import AsyncSessionLocal
        from app.models.cases import OnboardingCase

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
                    # Forward client_data so ProductOnboarding has it for
                    # suitability assessment and risk profiling steps.
                    "client_data": task.payload.get("client_data", {}),
                },
            ))
        # Persist the stage transition to the DB so the frontend reflects the outcome
        if kyc_status == "PASSED":
            new_stage = OnboardingStage.PARALLEL_PRODUCTS
        elif kyc_status == "FAILED":
            new_stage = OnboardingStage.REVIEW
        else:
            new_stage = None  # ESCALATED — leave current_stage unchanged

        if new_stage is not None:
            async def _update_stage(case_id: UUID, stage: str) -> None:
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        sa_update(OnboardingCase)
                        .where(OnboardingCase.id == case_id)
                        .values(current_stage=stage)
                    )
                    await db.commit()

            asyncio.create_task(_update_stage(task.case_id, new_stage))

        # Send client notifications for PASSED and FAILED outcomes
        if kyc_status in ("PASSED", "FAILED"):
            asyncio.create_task(
                self._notify_kyc_outcome(task, kyc_status, task.payload.get("selected_products", []))
            )

        # Log compliance decision for every KYC outcome (PASSED, ESCALATED, or FAILED)
        asyncio.create_task(
            compliance_decision_logger.log_automated_kyc_decision(
                case_id=task.case_id,
                client_id=task.client_id,
                kyc_status=kyc_status,
                risk_band=risk_score.risk_band,
                composite_score=float(risk_score.composite_score),
                identity_score=float(risk_score.identity_score),
                aml_score=float(risk_score.aml_score),
                profile_score=float(risk_score.profile_score),
                escalation_reasons=checkpoint.escalation_reasons,
                required_documents=checkpoint.required_documents,
                evidence_packet_id=str(evidence.packet_id),
            )
        )

    # ── Notification helpers ──────────────────────────────────────────────────

    async def _notify_kyc_outcome(
        self, task: TaskPacket, kyc_status: str, selected_products: list
    ) -> None:
        from app.database import AsyncSessionLocal
        from app.models.users import User
        from app.models.cases import OnboardingCase

        async with AsyncSessionLocal() as _db:
            _user = await _db.get(User, task.client_id)
            _client_name = _user.full_name if _user else ""
            _client_email = _user.email if _user else ""
            _case = await _db.get(OnboardingCase, task.case_id)
            _case_name = (_case.extra_metadata or {}).get("case_name", "") if _case else ""

        if kyc_status == "PASSED":
            templates = [("kyc_passed", "NORMAL")]
        else:
            templates = [("kyc_failed", "HIGH"), ("kyc_failed_inapp", "HIGH")]

        for _tmpl, _priority in templates:
            await self.send_task(TaskPacket(
                from_agent=self.agent_id,
                to_agent=AgentID.NOTIFICATION,
                task_type=TaskType.SEND_NOTIFICATION,
                case_id=task.case_id,
                client_id=task.client_id,
                priority=_priority,
                payload={
                    "template": _tmpl,
                    "client_name": _client_name,
                    "case_name": _case_name,
                    "selected_products": selected_products,
                    "recipient_email": _client_email,
                },
            ))

    # ── Simulated MCP identity verification ───────────────────────────────────

    async def _simulate_identity_verification(
        self, client_data: dict[str, Any], case_id: UUID | None = None
    ) -> dict[str, Any]:
        """
        Simulates the MCP Identity Verification connector (STEP-16).
        Outcome is determined by nationality:
          - India                  → document_authentic=True  (PASSED)
          - High-risk nationalities → sanctions_match=True    (ESCALATED)
          - All others             → document_authentic=False (FAILED)
        When DEMO_MODE=True, returns the pre-canned fixture for the case's scenario.
        """
        import asyncio
        from app.config import settings

        # Demo mode: return pre-canned fixture
        if settings.DEMO_MODE and case_id is not None:
            try:
                from app.services.demo.demo_mode_service import demo_mode_service
                fixture = demo_mode_service.get_kyc_result(case_id)
                if fixture:
                    latency = fixture.get("latency_ms", 300) / 1000.0
                    await asyncio.sleep(latency)
                    return fixture
            except Exception:
                pass  # fall through to normal simulation

        latency = random.uniform(0.2, 0.8)
        await asyncio.sleep(latency)

        nationality = (client_data.get("country_of_citizenship") or client_data.get("nationality") or "").lower()
        sanctions_match = nationality in _HIGH_RISK_NATIONALITIES

        # High-risk nationality → ESCALATED
        if sanctions_match:
            return {
                "verification_id": str(uuid4()),
                "name_match_confidence": 0.95,
                "document_authentic": True,
                "document_valid": True,
                "sanctions_match": True,
                "pep_match": False,
                "aml_risk_factors": ["high_risk_jurisdiction_nationality"],
                "aml_risk_level": "HIGH",
                "latency_ms": round(latency * 1000),
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "provider": "simulated_identity_verification_v1",
                "is_simulated": True,
            }

        # Non-India, non-high-risk → FAILED (inauthentic document)
        # "india" in nationality matches "india", "indian", "i am from india", etc.
        if "india" not in nationality:
            return {
                "verification_id": str(uuid4()),
                "name_match_confidence": 0.72,
                "document_authentic": False,
                "document_valid": False,
                "sanctions_match": False,
                "pep_match": False,
                "aml_risk_factors": [],
                "aml_risk_level": "LOW",
                "latency_ms": round(latency * 1000),
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "provider": "simulated_identity_verification_v1",
                "is_simulated": True,
            }

        # India → PASSED
        _INCOME_RANGE_TO_FLOAT = {
            "under $25,000": 20_000.0,
            "$25,000 - $50,000": 37_500.0,
            "$50,000 - $100,000": 75_000.0,
            "$100,000 - $200,000": 150_000.0,
            "over $200,000": 250_000.0,
        }
        aml_risk_factors: list[str] = []
        raw_income = str(client_data.get("annual_income") or "").strip().lower()
        _income = _INCOME_RANGE_TO_FLOAT.get(raw_income, 0.0)
        if _income > 1_000_000:
            aml_risk_factors.append("high_income")
        source_of_funds = client_data.get("source_of_funds") or []
        if "Other" in (source_of_funds if isinstance(source_of_funds, list) else [source_of_funds]):
            aml_risk_factors.append("undisclosed_source_of_funds")

        aml_risk_level = "MEDIUM" if len(aml_risk_factors) > 1 else ("LOW" if aml_risk_factors else "LOW")

        return {
            "verification_id": str(uuid4()),
            "name_match_confidence": 0.97,
            "document_authentic": True,
            "document_valid": True,
            "sanctions_match": False,
            "pep_match": False,
            "aml_risk_factors": aml_risk_factors,
            "aml_risk_level": aml_risk_level,
            "latency_ms": round(latency * 1000),
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "provider": "simulated_identity_verification_v1",
            "is_simulated": True,
        }
