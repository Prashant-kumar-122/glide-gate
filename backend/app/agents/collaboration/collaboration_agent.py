from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskResponse, TaskType
from app.agents.base.base_agent import BaseAgent


class CollaborationRoom(object):
    """In-memory representation of a multi-party review room."""

    __slots__ = ("room_id", "case_id", "participants", "comments", "created_at")

    def __init__(self, room_id: UUID, case_id: UUID) -> None:
        self.room_id = room_id
        self.case_id = case_id
        self.participants: list[dict[str, str]] = []
        self.comments: list[dict[str, Any]] = []
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_id": str(self.room_id),
            "case_id": str(self.case_id),
            "participants": self.participants,
            "comment_count": len(self.comments),
            "comments": self.comments,
            "created_at": self.created_at,
        }


class CollaborationAgent(BaseAgent):
    """
    Collaboration Agent (BRD Section 6.1, Section 7.4).

    Manages multi-party collaboration rooms for onboarding cases, enabling
    advisors, compliance officers, and CC representatives to share comments
    and track document review status.

    Handles:
    - CREATE_COLLABORATION_ROOM — create a new room for a case
    - ADD_COMMENT               — append a comment to an existing room
    """

    agent_id = AgentID.COLLABORATION

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        # In-memory store; replaced by DB in STEP-12+
        self._rooms: dict[str, CollaborationRoom] = {}

    async def process(self, task: TaskPacket) -> TaskResponse:
        handlers = {
            TaskType.CREATE_COLLABORATION_ROOM: self._handle_create_room,
            TaskType.ADD_COMMENT: self._handle_add_comment,
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

    async def _handle_create_room(self, task: TaskPacket) -> TaskResponse:
        case_key = str(task.case_id)
        if case_key in self._rooms:
            room = self._rooms[case_key]
            self.logger.debug(f"Returning existing collaboration room for case={task.case_id}")
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="SUCCESS",
                result={"already_exists": True, **room.to_dict()},
            )

        room = CollaborationRoom(room_id=uuid4(), case_id=task.case_id)
        participants: list[dict[str, str]] = task.payload.get("participants", [])
        for p in participants:
            room.participants.append(p)

        self._rooms[case_key] = room
        self.logger.info(
            f"Created collaboration room={room.room_id} for case={task.case_id} "
            f"participants={len(participants)}"
        )

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={"already_exists": False, **room.to_dict()},
        )

    async def _handle_add_comment(self, task: TaskPacket) -> TaskResponse:
        case_key = str(task.case_id)
        room = self._rooms.get(case_key)

        if room is None:
            room = CollaborationRoom(room_id=uuid4(), case_id=task.case_id)
            self._rooms[case_key] = room
            self.logger.warning(
                f"ADD_COMMENT: auto-created room for case={task.case_id} (no prior CREATE)"
            )

        author_id: str = task.payload.get("author_id", str(task.client_id))
        author_role: str = task.payload.get("author_role", "advisor")
        text: str = task.payload.get("text", "").strip()
        document_id: str | None = task.payload.get("document_id")
        visibility: str = task.payload.get("visibility", "internal")

        if not text:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=["payload.text is required"],
            )

        comment: dict[str, Any] = {
            "comment_id": str(uuid4()),
            "author_id": author_id,
            "author_role": author_role,
            "text": text,
            "document_id": document_id,
            "visibility": visibility,
            "created_at": datetime.utcnow().isoformat(),
        }
        room.comments.append(comment)

        self.logger.debug(
            f"Added comment to room={room.room_id} case={task.case_id} "
            f"author={author_role} doc={document_id}"
        )

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={
                "room_id": str(room.room_id),
                "comment": comment,
                "total_comments": len(room.comments),
            },
        )

    # ── Public helpers ────────────────────────────────────────────────────────

    def get_room(self, case_id: UUID) -> dict[str, Any] | None:
        room = self._rooms.get(str(case_id))
        return room.to_dict() if room else None
