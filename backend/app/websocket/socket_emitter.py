from __future__ import annotations

"""Singleton helper so agents and services can emit socket events without
importing the raw `sio` server directly.  All emission goes through
`emit_to_case` which targets the correct socket.io room.
"""

from typing import Any
from uuid import UUID

from loguru import logger

from app.websocket.socket_events import SocketEvent
from app.websocket import socket_server
from uuid import UUID


class SocketEmitter:
    """Thin façade over `socket_server.emit_to_case`.

    Usage::

        from app.websocket.socket_emitter import socket_emitter
        await socket_emitter.agent_message(case_id, payload)
    """

    # ── Generic ──────────────────────────────────────────────────────────────

    async def emit(
        self,
        case_id: str | UUID,
        event: SocketEvent | str,
        data: dict[str, Any],
    ) -> None:
        try:
            await socket_server.emit_to_case(case_id, event, data)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SocketEmitter] emit failed event={event} case={case_id}: {exc}")

    # ── Typed helpers ────────────────────────────────────────────────────────

    async def agent_message(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.AGENT_MESSAGE, payload)

    async def task_assigned(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.TASK_ASSIGNED, payload)

    async def task_complete(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.TASK_COMPLETE, payload)

    async def document_status_changed(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.DOCUMENT_STATUS_CHANGED, payload)

    async def document_uploaded(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.DOCUMENT_UPLOADED, payload)

    async def kyc_result(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.KYC_RESULT, payload)

    async def escalation_triggered(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.ESCALATION_TRIGGERED, payload)

    async def review_decided(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.REVIEW_DECIDED, payload)

    async def sales_review_triggered(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.SALES_REVIEW_TRIGGERED, payload)

    async def sales_review_decided(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.SALES_REVIEW_DECIDED, payload)

    async def product_track_update(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.PRODUCT_TRACK_UPDATE, payload)

    async def notification_sent(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.NOTIFICATION_SENT, payload)

    async def notify_user(self, user_id: str | UUID, payload: dict[str, Any]) -> None:
        """Emit notification_sent directly to the user room (bypasses case room)."""
        try:
            await socket_server.emit_to_user(user_id, SocketEvent.NOTIFICATION_SENT, payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SocketEmitter] notify_user failed user={user_id}: {exc}")

    async def case_stage_changed(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.CASE_STAGE_CHANGED, payload)

    async def progress_update(self, case_id: str | UUID, payload: dict[str, Any]) -> None:
        await self.emit(case_id, SocketEvent.PROGRESS_UPDATE, payload)


# Module-level singleton — import and use directly:
#   from app.websocket.socket_emitter import socket_emitter
socket_emitter = SocketEmitter()
