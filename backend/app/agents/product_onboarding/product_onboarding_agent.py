from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from app.agents.base.a2a_types import (
    AgentID,
    TaskPacket,
    TaskResponse,
    TaskType,
)
from app.agents.base.base_agent import BaseAgent
from app.agents.product_onboarding.suitability_assessor import SuitabilityAssessor

_PRODUCT_STEPS: dict[str, list[str]] = {
    "cash_account": [
        "suitability_assessment",
        "account_funding_setup",
        "account_provisioning",
        "welcome_kit",
    ],
    "retirement_account": [
        "suitability_assessment",
        "contribution_limits_check",
        "beneficiary_designation",
        "investment_selection",
        "account_provisioning",
        "welcome_kit",
    ],
}

_DEFAULT_STEPS: list[str] = [
    "suitability_assessment",
    "account_provisioning",
    "welcome_kit",
]

_STEP_DURATIONS_MS: dict[str, tuple[int, int]] = {
    "suitability_assessment": (200, 600),
    "risk_profiling": (300, 800),
    "portfolio_construction": (500, 1200),
    "mandate_setup": (200, 500),
    "contribution_limits_check": (100, 300),
    "beneficiary_designation": (150, 400),
    "investment_selection": (400, 900),
    "account_provisioning": (300, 700),
    "welcome_kit": (100, 250),
}


class ProductOnboardingAgent(BaseAgent):
    """
    Product Onboarding Agent (BRD Section 6.1, FR-05, Section 8.1 stages 5–8).

    Parameterised by product_code so the Orchestrator can spawn one instance
    per selected product and run them in parallel via asyncio.gather.

    Handles:
    - ONBOARD_PRODUCT      — execute the full step sequence for the product
    - ASSESS_SUITABILITY   — standalone suitability check (returns result only)
    """

    agent_id = AgentID.PRODUCT_ONBOARDING

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._assessor = SuitabilityAssessor()

    async def process(self, task: TaskPacket) -> TaskResponse:
        handlers = {
            TaskType.ONBOARD_PRODUCT: self._handle_onboard,
            TaskType.ASSESS_SUITABILITY: self._handle_assess,
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

    async def _handle_onboard(self, task: TaskPacket) -> TaskResponse:
        product_code: str = task.payload.get("product_code", "")
        client_data: dict[str, Any] = task.payload.get("client_data", {})
        resume_from_step: int = int(task.payload.get("resume_from_step", 0))

        if not product_code:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=["payload.product_code is required"],
            )

        steps = _PRODUCT_STEPS.get(product_code, _DEFAULT_STEPS)
        total = len(steps)
        completed: list[dict[str, Any]] = []

        self.logger.info(
            f"Starting product onboarding: case={task.case_id} "
            f"product={product_code} steps={total} resume_from={resume_from_step}"
        )

        suitability = self._assessor.assess(product_code, client_data)
        if not suitability.is_suitable:
            self.logger.warning(
                f"Suitability FAILED for {product_code}: score={suitability.suitability_score}"
            )
            await self._signal_complete(task, product_code, "UNSUITABLE", completed, total)
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="PARTIAL",
                result={
                    "product_code": product_code,
                    "status": "UNSUITABLE",
                    "suitability": suitability.model_dump(),
                    "steps_completed": [],
                    "total_steps": total,
                },
            )

        for idx, step_name in enumerate(steps):
            if idx < resume_from_step:
                completed.append({"step": step_name, "status": "SKIPPED_RESUME", "step_index": idx})
                continue

            step_result = await self._execute_step(
                step_name, idx, product_code, client_data, suitability.model_dump()
            )
            completed.append(step_result)

            if step_result.get("status") == "FAILED":
                self.logger.error(
                    f"Step '{step_name}' failed for {product_code}, halting track."
                )
                await self._signal_complete(task, product_code, "FAILED", completed, total)
                return TaskResponse(
                    task_id=task.id,
                    from_agent=self.agent_id,
                    status="FAILED",
                    result={
                        "product_code": product_code,
                        "status": "FAILED",
                        "failed_step": step_name,
                        "steps_completed": completed,
                        "total_steps": total,
                    },
                )

            self.logger.debug(
                f"[{product_code}] step {idx + 1}/{total} '{step_name}' OK"
            )

        self.logger.info(f"Product onboarding COMPLETE: case={task.case_id} product={product_code}")
        await self._signal_complete(task, product_code, "COMPLETE", completed, total)

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={
                "product_code": product_code,
                "status": "COMPLETE",
                "suitability": suitability.model_dump(),
                "steps_completed": completed,
                "total_steps": total,
                "completed_at": datetime.utcnow().isoformat(),
            },
        )

    async def _handle_assess(self, task: TaskPacket) -> TaskResponse:
        product_code: str = task.payload.get("product_code", "")
        client_data: dict[str, Any] = task.payload.get("client_data", {})

        if not product_code:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=["payload.product_code is required"],
            )

        outcome = self._assessor.assess(product_code, client_data)
        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result=outcome.model_dump(),
        )

    # ── Step execution ────────────────────────────────────────────────────────

    async def _execute_step(
        self,
        step_name: str,
        step_index: int,
        product_code: str,
        client_data: dict[str, Any],
        suitability: dict[str, Any],
    ) -> dict[str, Any]:
        import random

        lo, hi = _STEP_DURATIONS_MS.get(step_name, (200, 600))
        latency = random.uniform(lo / 1000, hi / 1000)
        await asyncio.sleep(latency)

        step_data: dict[str, Any] = {
            "step": step_name,
            "step_index": step_index,
            "status": "COMPLETED",
            "duration_ms": round(latency * 1000),
            "completed_at": datetime.utcnow().isoformat(),
        }

        if step_name == "suitability_assessment":
            step_data["suitability_score"] = suitability.get("suitability_score")
            step_data["is_suitable"] = suitability.get("is_suitable")

        elif step_name == "risk_profiling":
            objective = (client_data.get("investment_objective") or "growth").lower()
            risk_tolerance = _OBJECTIVE_TO_RISK_STR.get(objective, "balanced")
            step_data["risk_profile"] = risk_tolerance
            step_data["volatility_tolerance"] = _RISK_CAPACITY_MAP_STR.get(risk_tolerance, "medium")

        elif step_name == "account_provisioning":
            import uuid
            step_data["account_number"] = f"GG-{product_code[:3].upper()}-{str(uuid.uuid4())[:8].upper()}"
            step_data["account_status"] = "PROVISIONED"

        elif step_name == "contribution_limits_check":
            raw_income = str(client_data.get("annual_income") or "").strip().lower()
            annual_income = _INCOME_RANGE_TO_FLOAT.get(raw_income, 0.0)
            step_data["annual_contribution_limit"] = min(annual_income * 0.18, 30_000.0)
            step_data["carry_forward_available"] = True

        return step_data

    # ── Orchestrator signalling ───────────────────────────────────────────────

    async def _signal_complete(
        self,
        task: TaskPacket,
        product_code: str,
        track_status: str,
        completed_steps: list[dict[str, Any]],
        total_steps: int,
    ) -> None:
        if self._bus is None:
            return

        steps_done = len([s for s in completed_steps if s.get("status") == "COMPLETED"])

        await self.send_task(TaskPacket(
            from_agent=self.agent_id,
            to_agent=AgentID.NOTIFICATION,
            task_type=TaskType.SEND_NOTIFICATION,
            case_id=task.case_id,
            client_id=task.client_id,
            priority="LOW",
            payload={
                "template": "product_track_update",
                "product_code": product_code,
                "track_status": track_status,
                "steps_completed": steps_done,
                "total_steps": total_steps,
            },
        ))

        # Notify the orchestrator so it can advance PARALLEL_PRODUCTS → REVIEW
        # once all product tracks have settled.
        await self.send_task(TaskPacket(
            from_agent=self.agent_id,
            to_agent=AgentID.ORCHESTRATOR,
            task_type=TaskType.PRODUCT_TRACK_COMPLETE,
            case_id=task.case_id,
            client_id=task.client_id,
            priority="NORMAL",
            payload={
                "product_code": product_code,
                "track_status": track_status,
                "steps_completed": steps_done,
                "total_steps": total_steps,
            },
        ))


_RISK_CAPACITY_MAP_STR: dict[str, str] = {
    "conservative": "low",
    "moderately_conservative": "low_medium",
    "balanced": "medium",
    "moderately_aggressive": "medium_high",
    "aggressive": "high",
}

_OBJECTIVE_TO_RISK_STR: dict[str, str] = {
    "capital preservation": "conservative",
    "income": "moderately_conservative",
    "growth and income": "balanced",
    "growth": "moderately_aggressive",
    "speculation": "aggressive",
    "aggressive growth": "aggressive",
}

_INCOME_RANGE_TO_FLOAT: dict[str, float] = {
    "under $25,000": 20_000.0,
    "$25,000 - $50,000": 37_500.0,
    "$50,000 - $100,000": 75_000.0,
    "$100,000 - $200,000": 150_000.0,
    "over $200,000": 250_000.0,
}
