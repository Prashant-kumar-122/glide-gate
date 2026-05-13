from __future__ import annotations

import asyncio
import random
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskResponse, TaskType
from app.agents.base.base_agent import BaseAgent
from app.agents.notification.notification_templates import get_template, list_templates

_PRODUCT_NAMES: dict[str, str] = {
    "cash_account": "Cash Account",
    "retirement_account": "Retirement Account",
}

_DISPATCH_LATENCY_MS: tuple[int, int] = (50, 300)


class NotificationAgent(BaseAgent):
    """
    Notification Agent (BRD Section 6.1, Section 7.4).

    Handles simulated dispatch of all outbound notifications: email, SMS,
    and in-app messages. All dispatches are logged; actual delivery is
    simulated with randomised latency.

    Handles:
    - SEND_NOTIFICATION      — render template and simulate dispatch
    - SEND_ESCALATION_ALERT  — high-priority notification to compliance officers
    """

    agent_id = AgentID.NOTIFICATION

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._dispatch_log: list[dict[str, Any]] = []

    async def process(self, task: TaskPacket) -> TaskResponse:
        handlers = {
            TaskType.SEND_NOTIFICATION: self._handle_send,
            TaskType.SEND_ESCALATION_ALERT: self._handle_escalation_alert,
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

    async def _handle_send(self, task: TaskPacket) -> TaskResponse:
        template_id: str = task.payload.get("template", "")
        variables: dict[str, Any] = self._build_variables(task)

        tmpl = get_template(template_id)
        if tmpl is None:
            self.logger.warning(
                f"Unknown notification template '{template_id}' for case={task.case_id}. "
                f"Available: {list_templates()}"
            )
            rendered = {
                "subject": f"GlideGate Notification — {template_id}",
                "body": str(variables),
                "channel": "in_app",
                "template_id": template_id,
            }
        else:
            rendered = tmpl.render(variables)

        record = await self._dispatch(rendered, task)

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result=record,
        )

    async def _handle_escalation_alert(self, task: TaskPacket) -> TaskResponse:
        variables = self._build_variables(task)
        variables.setdefault("risk_band", task.payload.get("risk_band", "UNKNOWN"))
        variables.setdefault("escalation_reason", task.payload.get("reason", ""))
        variables.setdefault("evidence_packet_id", task.payload.get("evidence_packet_id", ""))

        tmpl = get_template("escalation_alert")
        rendered = tmpl.render(variables) if tmpl else {
            "subject": f"[URGENT] Escalation — {task.case_id}",
            "body": str(variables),
            "channel": "email",
            "template_id": "escalation_alert",
        }

        record = await self._dispatch(rendered, task, priority_override="CRITICAL")

        self.logger.warning(
            f"Escalation alert dispatched for case={task.case_id} "
            f"risk_band={variables.get('risk_band')}"
        )

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result=record,
        )

    # ── Dispatch simulation ───────────────────────────────────────────────────

    async def _dispatch(
        self,
        rendered: dict[str, str],
        task: TaskPacket,
        priority_override: str | None = None,
    ) -> dict[str, Any]:
        lo, hi = _DISPATCH_LATENCY_MS
        latency = random.uniform(lo / 1000, hi / 1000)
        await asyncio.sleep(latency)

        record: dict[str, Any] = {
            "notification_id": str(uuid4()),
            "case_id": str(task.case_id),
            "client_id": str(task.client_id),
            "template_id": rendered.get("template_id"),
            "channel": rendered.get("channel", "in_app"),
            "subject": rendered.get("subject"),
            "body_preview": (rendered.get("body") or "")[:120],
            "priority": priority_override or str(task.priority),
            "status": "SIMULATED_SENT",
            "latency_ms": round(latency * 1000),
            "dispatched_at": datetime.utcnow().isoformat(),
            "is_simulated": True,
        }

        self._dispatch_log.append(record)
        self.logger.debug(
            f"[SIMULATED] Notification dispatched: template={record['template_id']} "
            f"channel={record['channel']} case={task.case_id}"
        )
        return record

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_variables(self, task: TaskPacket) -> dict[str, Any]:
        payload = task.payload
        products = payload.get("selected_products", payload.get("products", []))
        product_names = ", ".join(_PRODUCT_NAMES.get(p, p) for p in products) if products else ""

        product_code = payload.get("product_code", "")
        product_name = _PRODUCT_NAMES.get(product_code, product_code.replace("_", " ").title())

        return {
            "case_id": str(task.case_id),
            "client_id": str(task.client_id),
            "client_name": payload.get("client_name", "Valued Client"),
            "products": product_names or product_name,
            "product_name": product_name,
            "product_code": product_code,
            "track_status": payload.get("track_status", ""),
            "steps_completed": str(payload.get("steps_completed", "")),
            "total_steps": str(payload.get("total_steps", "")),
            "document_type": payload.get("document_type", "document"),
            "document_list": payload.get("document_list", ""),
            "revision_reason": payload.get("revision_reason", ""),
            "decision": payload.get("decision", ""),
            "decision_notes": payload.get("decision_notes", ""),
            "risk_band": payload.get("risk_band", ""),
            "escalation_reason": payload.get("reason", ""),
            "evidence_packet_id": payload.get("evidence_packet_id", ""),
        }

    # ── Public helpers ────────────────────────────────────────────────────────

    def get_dispatch_log(self) -> list[dict[str, Any]]:
        return list(self._dispatch_log)
