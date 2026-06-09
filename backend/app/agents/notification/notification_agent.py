from __future__ import annotations

import asyncio
import random
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskResponse, TaskType
from app.agents.base.base_agent import BaseAgent
from app.agents.notification.notification_templates import get_template, list_templates
from app.config import settings
from app.websocket.socket_emitter import socket_emitter
from app.models.communications import Notification

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

    # ── Dispatch ─────────────────────────────────────────────────────────────

    async def _dispatch(
        self,
        rendered: dict[str, str],
        task: TaskPacket,
        priority_override: str | None = None,
    ) -> dict[str, Any]:
        channel = rendered.get("channel", "in_app")
        is_simulated = True
        status = "SIMULATED_SENT"
        latency_ms = 0

        if channel == "email" and settings.EMAIL_ENABLED and settings.RESEND_API_KEY:
            self.logger.info(f"[NotificationAgent] sending real email case={task.case_id}")
            status, latency_ms, is_simulated = await self._send_email(rendered, task)
        else:
            self.logger.info(
                f"[NotificationAgent] simulating channel={channel} "
                f"email_enabled={settings.EMAIL_ENABLED} has_key={bool(settings.RESEND_API_KEY)} "
                f"case={task.case_id}"
            )
            lo, hi = _DISPATCH_LATENCY_MS
            latency = random.uniform(lo / 1000, hi / 1000)
            await asyncio.sleep(latency)
            latency_ms = round(latency * 1000)

        record: dict[str, Any] = {
            "notification_id": str(uuid4()),
            "case_id": str(task.case_id),
            "client_id": str(task.client_id),
            "template_id": rendered.get("template_id"),
            "channel": channel,
            "subject": rendered.get("subject"),
            "body": rendered.get("body") or "",
            "body_preview": rendered.get("body") or "",
            "priority": priority_override or str(task.priority),
            "status": status,
            "latency_ms": latency_ms,
            "dispatched_at": datetime.utcnow().isoformat(),
            "is_simulated": is_simulated,
        }

        self._dispatch_log.append(record)
        prefix = "[SIMULATED]" if is_simulated else "[SENT]"
        self.logger.debug(
            f"{prefix} Notification dispatched: template={record['template_id']} "
            f"channel={channel} case={task.case_id}"
        )

        _socket_payload = {
            "notification_id": record["notification_id"],
            "template_id": record["template_id"],
            "channel": record["channel"],
            "subject": record["subject"],
            "body_preview": record["body_preview"],
            "priority": record["priority"],
            "status": record["status"],
        }
        _user_type = task.payload.get("user_type", "client")
        if channel == "in_app" and _user_type != "advisor" and task.client_id:
            # Client-specific in-app → send only to that user's room
            await socket_emitter.notify_user(task.client_id, _socket_payload)

            # Push dedup (v1): if the user has no active socket session, send a push
            # notification so they're alerted while the app is closed/backgrounded.
            # Known v1 gap: a backgrounded-but-connected tab may get both; revisit
            # with a visibilitychange-driven user_active signal in a later iteration.
            from app.websocket.socket_server import has_active_socket
            if not has_active_socket(str(task.client_id)):
                try:
                    from app.services.push.push_service import push_service
                    await push_service.send_push_to_user(
                        str(task.client_id),
                        {
                            "title": record.get("subject") or "GlideGate",
                            "body_preview": record.get("body_preview", ""),
                            "notification_id": record["notification_id"],
                            "url": "/",
                        },
                    )
                except Exception as push_exc:
                    self.logger.error(f"[NotificationAgent] push dispatch failed: {push_exc}")
        else:
            # Advisor/broadcast in-app or email audit → case room
            await socket_emitter.notification_sent(task.case_id, _socket_payload)

        await self._save_to_db(record, task)

        return record

    async def _save_to_db(self, record: dict[str, Any], task: TaskPacket) -> None:
        """Persist the dispatched notification to the notifications table."""
        from app.database import AsyncSessionLocal

        user_type: str | None = None
        if task.payload.get("user_type"):
            user_type = task.payload["user_type"]
        elif task.client_id:
            user_type = "client"

        try:
            async with AsyncSessionLocal() as session:
                notif = Notification(
                    case_id=task.case_id,
                    user_id=task.client_id,
                    user_type=user_type,
                    template_name=record.get("template_id"),
                    channel=record["channel"],
                    recipient_email=task.payload.get("recipient_email") or task.payload.get("client_email"),
                    subject=record.get("subject"),
                    body=(record.get("body") or task.payload.get("body") or record.get("body_preview")),
                    status=record["status"],
                    is_simulated=record["is_simulated"],
                    sent_at=datetime.utcnow() if record["status"] in ("SENT", "SIMULATED_SENT") else None,
                )
                session.add(notif)
                await session.commit()
                record["notification_id"] = str(notif.id)
        except Exception as exc:
            self.logger.error(f"Failed to persist notification to DB: {exc}")

    async def _send_email(
        self,
        rendered: dict[str, str],
        task: TaskPacket,
    ) -> tuple[str, int, bool]:
        """Send real email via Resend. Returns (status, latency_ms, is_simulated)."""
        import time

        try:
            import resend  # type: ignore[import-untyped]

            resend.api_key = settings.RESEND_API_KEY
            recipient = (
                task.payload.get("recipient_email")
                or task.payload.get("client_email", "")
            )
            if not recipient:
                self.logger.warning(
                    f"No recipient_email in payload for case={task.case_id}, simulating"
                )
                return "SIMULATED_SENT", 0, True

            t0 = time.monotonic()
            resend.Emails.send({
                "from": f"{settings.NOTIFICATION_FROM_NAME} <{settings.NOTIFICATION_FROM_EMAIL}>",
                "to": [recipient],
                "subject": rendered.get("subject", ""),
                "text": rendered.get("body", ""),
            })
            return "SENT", round((time.monotonic() - t0) * 1000), False

        except Exception as exc:
            self.logger.error(f"Email dispatch failed for case={task.case_id}: {exc}")
            return "FAILED", 0, False

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_variables(self, task: TaskPacket) -> dict[str, Any]:
        payload = task.payload
        products = payload.get("selected_products", payload.get("products", []))
        product_names = ", ".join(_PRODUCT_NAMES.get(p, p) for p in products) if products else ""

        product_code = payload.get("product_code", "")
        product_name = _PRODUCT_NAMES.get(product_code, product_code.replace("_", " ").title())

        document_name = (
            payload.get("document_name")
            or payload.get("document_type")
            or "document"
        )

        return {
            "case_id": str(task.case_id),
            "case_name": payload.get("case_name", f"Case {str(task.case_id)[:8]}"),
            "client_id": str(task.client_id),
            "client_name": payload.get("client_name", "Valued Client"),
            "products": product_names or product_name,
            "product_name": product_name,
            "product_code": product_code,
            "track_status": payload.get("track_status", ""),
            "steps_completed": str(payload.get("steps_completed", "")),
            "total_steps": str(payload.get("total_steps", "")),
            "document_type": document_name,
            "document_name": document_name,
            "document_list": payload.get("document_list", document_name),
            "revision_reason": payload.get("revision_reason", ""),
            "decision": payload.get("decision", ""),
            "decision_notes": payload.get("decision_notes", ""),
            "risk_band": payload.get("risk_band", ""),
            "escalation_reason": payload.get("reason", ""),
            "evidence_packet_id": payload.get("evidence_packet_id", ""),
            "author_name": payload.get("author_name", ""),
            "comment_body": payload.get("comment_body", ""),
            "account_numbers": payload.get("account_numbers", "—"),
        }

    # ── Public helpers ────────────────────────────────────────────────────────

    def get_dispatch_log(self) -> list[dict[str, Any]]:
        return list(self._dispatch_log)
