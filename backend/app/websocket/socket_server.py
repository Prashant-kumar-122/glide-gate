from __future__ import annotations

from typing import Any
from uuid import UUID

import socketio
from loguru import logger

from app.config import settings
from app.websocket.socket_events import SocketEvent

# ── Singleton AsyncServer ────────────────────────────────────────────────────
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.SOCKETIO_CORS_ORIGINS,
    logger=False,
    engineio_logger=False,
)

# Maps case_id (str) → set of session IDs in that room
_case_rooms: dict[str, set[str]] = {}


def _room_name(case_id: str | UUID) -> str:
    return f"case:{case_id}"


# ── Connection lifecycle ─────────────────────────────────────────────────────

@sio.event
async def connect(sid: str, environ: dict[str, Any], auth: dict[str, Any] | None = None) -> None:
    logger.debug(f"[WS] client connected sid={sid}")


@sio.event
async def disconnect(sid: str) -> None:
    logger.debug(f"[WS] client disconnected sid={sid}")
    # Remove sid from all rooms it was in
    for room_sids in _case_rooms.values():
        room_sids.discard(sid)


# ── Room management ──────────────────────────────────────────────────────────

@sio.on(SocketEvent.JOIN_CASE_ROOM)
async def on_join_case_room(sid: str, data: dict[str, Any]) -> None:
    case_id: str | None = data.get("case_id")
    if not case_id:
        await sio.emit(SocketEvent.ERROR, {"message": "case_id required"}, to=sid)
        return
    room = _room_name(case_id)
    await sio.enter_room(sid, room)
    _case_rooms.setdefault(case_id, set()).add(sid)
    logger.info(f"[WS] sid={sid} joined room={room}")
    await sio.emit("joined", {"case_id": case_id, "room": room}, to=sid)


@sio.on(SocketEvent.LEAVE_CASE_ROOM)
async def on_leave_case_room(sid: str, data: dict[str, Any]) -> None:
    case_id: str | None = data.get("case_id")
    if not case_id:
        return
    room = _room_name(case_id)
    await sio.leave_room(sid, room)
    if case_id in _case_rooms:
        _case_rooms[case_id].discard(sid)
    logger.info(f"[WS] sid={sid} left room={room}")


@sio.on("join_user_room")
async def on_join_user_room(sid: str, data: dict[str, Any]) -> None:
    user_id: str | None = data.get("user_id")
    if not user_id:
        return
    room = f"user:{user_id}"
    await sio.enter_room(sid, room)
    logger.info(f"[WS] sid={sid} joined user room={room}")


@sio.on("leave_user_room")
async def on_leave_user_room(sid: str, data: dict[str, Any]) -> None:
    user_id: str | None = data.get("user_id")
    if not user_id:
        return
    await sio.leave_room(sid, f"user:{user_id}")


# ── Helpers for agents/services ──────────────────────────────────────────────

async def emit_to_case(case_id: str | UUID, event: SocketEvent | str, data: dict[str, Any]) -> None:
    """Emit an event to all sockets in a case room."""
    room = _room_name(case_id)
    await sio.emit(str(event), data, room=room)


async def emit_to_user(user_id: str | UUID, event: SocketEvent | str, data: dict[str, Any]) -> None:
    """Emit an event to the user-level room (always connected, regardless of case)."""
    room = f"user:{user_id}"
    logger.info(f"[WS] emit_to_user room={room} event={event}")
    await sio.emit(str(event), data, room=room)


def room_size(case_id: str | UUID) -> int:
    return len(_case_rooms.get(str(case_id), set()))
