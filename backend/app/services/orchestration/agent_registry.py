from __future__ import annotations

from app.agents.base.a2a_types import AgentID
from app.agents.base.base_agent import BaseAgent


class AgentRegistry:
    """Simple dict-backed registry of live agent instances.

    Used by the API agents router to expose health and status without
    coupling directly to the event bus internals.
    """

    def __init__(self) -> None:
        self._registry: dict[AgentID, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._registry[agent.agent_id] = agent

    def get(self, agent_id: AgentID) -> BaseAgent | None:
        return self._registry.get(agent_id)

    def all(self) -> list[BaseAgent]:
        return list(self._registry.values())

    def agent_ids(self) -> list[AgentID]:
        return list(self._registry.keys())

    def __len__(self) -> int:
        return len(self._registry)
