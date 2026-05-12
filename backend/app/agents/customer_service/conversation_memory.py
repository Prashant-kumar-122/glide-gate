from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationMemory:
    """Per-case rolling conversation history (in-process, replaced by DB in STEP-12)."""

    def __init__(self, max_messages: int = 40) -> None:
        self._store: dict[UUID, list[Message]] = {}
        self.max_messages = max_messages

    def add(self, case_id: UUID, role: Literal["user", "assistant"], content: str) -> None:
        if case_id not in self._store:
            self._store[case_id] = []
        self._store[case_id].append(Message(role=role, content=content))
        if len(self._store[case_id]) > self.max_messages:
            self._store[case_id] = self._store[case_id][-self.max_messages :]

    def get(self, case_id: UUID) -> list[Message]:
        return list(self._store.get(case_id, []))

    def to_anthropic(self, case_id: UUID) -> list[dict[str, str]]:
        """Format messages for the Anthropic SDK `messages` parameter."""
        return [{"role": m.role, "content": m.content} for m in self.get(case_id)]

    def clear(self, case_id: UUID) -> None:
        self._store.pop(case_id, None)

    def turn_count(self, case_id: UUID) -> int:
        return len(self._store.get(case_id, []))
