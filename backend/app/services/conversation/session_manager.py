from __future__ import annotations

from uuid import UUID

from app.agents.customer_service.conversation_memory import ConversationMemory
from app.agents.customer_service.data_collection_orchestrator import DataCollectionOrchestrator


class ConversationSession:
    """Per-case conversation session — owns a DCO instance and conversation memory."""

    __slots__ = (
        "case_id",
        "client_id",
        "selected_products",
        "dco",
        "memory",
        "collection_complete",
        "_advance_sent",
    )

    def __init__(self, case_id: UUID, client_id: UUID, selected_products: list[str]) -> None:
        self.case_id = case_id
        self.client_id = client_id
        self.selected_products = selected_products
        self.dco = DataCollectionOrchestrator()
        self.memory = ConversationMemory(max_messages=40)
        self.dco.init_session(case_id, selected_products)
        self.collection_complete: bool = False
        self._advance_sent: bool = False


class SessionManager:
    """In-memory registry of active per-case conversation sessions."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, ConversationSession] = {}

    def get_or_create(
        self, case_id: UUID, client_id: UUID, selected_products: list[str]
    ) -> ConversationSession:
        if case_id not in self._sessions:
            self._sessions[case_id] = ConversationSession(case_id, client_id, selected_products)
        return self._sessions[case_id]

    def get(self, case_id: UUID) -> ConversationSession | None:
        return self._sessions.get(case_id)

    def evict(self, case_id: UUID) -> None:
        self._sessions.pop(case_id, None)


session_manager = SessionManager()
