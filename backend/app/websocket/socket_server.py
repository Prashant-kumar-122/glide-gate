from __future__ import annotations

import http.cookies as http_cookies
from typing import Any
from uuid import UUID

import socketio
from jose import JWTError, jwt
from loguru import logger

from app.config import settings
from app.websocket.socket_events import SocketEvent

# Singleton AsyncServer
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.SOCKETIO_CORS_ORIGINS,
    logger=False,
    engineio_logger=False,
)

# case_id (str) -> set of session IDs in that room
_case_rooms: dict[str, set[str]] = {}

# user_id (str) -> set of session IDs currently connected
# Used by push dedup: if a user has any live socket, skip push and rely on in-app toast.
_connected_users: dict[str, set[str]] = {}


def has_active_socket(user_id: str) -> bool:
    """Return True if the user has at least one live socket connection."""
    return bool(_connected_users.get(user_id))


def _room_name(case_id: str | UUID) -> str:
    return f"case:{case_id}"


# Connection lifecycle

@sio.event
async def connect(sid: str, environ: dict[str, Any], auth: dict[str, Any] | None = None) -> None:
    token: str | None = None

    # Cookies flow automatically on same-origin WebSocket upgrade
    raw_cookie = environ.get("HTTP_COOKIE", "")
    if raw_cookie:
        jar = http_cookies.SimpleCookie(raw_cookie)
        morsel = jar.get(settings.AUTH_COOKIE_NAME)
        if morsel:
            token = morsel.value

    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str | None = payload.get("sub")
            if not user_id:
                raise ValueError("Missing sub claim")
            await sio.save_session(sid, {"user_id": user_id, "role": payload.get("role", "")})
            await sio.enter_room(sid, f"user:{user_id}")
            _connected_users.setdefault(user_id, set()).add(sid)
            logger.debug(f"[WS] authenticated sid={sid} user={user_id}")
            return
        except (JWTError, ValueError, Exception) as exc:
            logger.warning(f"[WS] auth failed sid={sid}: {exc}")
            raise socketio.exceptions.ConnectionRefusedError("Authentication failed")

    if settings.DEMO_MODE:
        demo_uid = "00000000-0000-0000-0000-000000000001"
        await sio.save_session(sid, {"user_id": demo_uid, "role": "advisor"})
        await sio.enter_room(sid, f"user:{demo_uid}")
        _connected_users.setdefault(demo_uid, set()).add(sid)
        logger.debug(f"[WS] demo connection sid={sid}")
        return

    raise socketio.exceptions.ConnectionRefusedError("Authentication required")


@sio.event
async def disconnect(sid: str) -> None:
    logger.debug(f"[WS] client disconnected sid={sid}")
    for room_sids in _case_rooms.values():
        room_sids.discard(sid)

    # Remove from per-user tracking
    try:
        session = await sio.get_session(sid)
        user_id = session.get("user_id") if session else None
    except Exception:
        user_id = None

    if user_id and user_id in _connected_users:
        _connected_users[user_id].discard(sid)
        if not _connected_users[user_id]:
            del _connected_users[user_id]


# Room management

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


# join_user_room / leave_user_room removed — room membership is now server-derived
# from the authenticated session (see connect handler above).


# Helpers for agents/services

async def emit_to_case(case_id: str | UUID, event: SocketEvent | str, data: dict[str, Any]) -> None:
    room = _room_name(case_id)
    await sio.emit(str(event), data, room=room)


async def emit_to_user(user_id: str | UUID, event: SocketEvent | str, data: dict[str, Any]) -> None:
    room = f"user:{user_id}"
    logger.info(f"[WS] emit_to_user room={room} event={event}")
    await sio.emit(str(event), data, room=room)


def room_size(case_id: str | UUID) -> int:
    return len(_case_rooms.get(str(case_id), set()))
