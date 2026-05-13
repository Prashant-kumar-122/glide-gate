from __future__ import annotations

import abc
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class MCPConnector(abc.ABC):
    """Abstract base for all MCP connectors."""

    connector_name: str

    @abc.abstractmethod
    def list_tools(self) -> list[MCPToolDefinition]:
        """Return metadata for every tool this connector exposes."""
        ...

    @abc.abstractmethod
    async def invoke(
        self,
        tool_name: str,
        inputs: dict[str, Any],
        *,
        case_id: UUID | None = None,
        agent_id: str = "unknown",
    ) -> dict[str, Any]:
        """Invoke a named tool and return its structured output."""
        ...


class MCPRegistry:
    """Process-level registry for connector discovery and invocation."""

    def __init__(self) -> None:
        self._connectors: dict[str, MCPConnector] = {}

    def register(self, connector: MCPConnector) -> None:
        self._connectors[connector.connector_name] = connector

    def get(self, connector_name: str) -> MCPConnector:
        if connector_name not in self._connectors:
            raise KeyError(f"MCP connector not registered: {connector_name!r}")
        return self._connectors[connector_name]

    def list_connectors(self) -> list[str]:
        return list(self._connectors.keys())

    def list_all_tools(self) -> dict[str, list[MCPToolDefinition]]:
        return {name: conn.list_tools() for name, conn in self._connectors.items()}

    async def invoke(
        self,
        connector_name: str,
        tool_name: str,
        inputs: dict[str, Any],
        *,
        case_id: UUID | None = None,
        agent_id: str = "unknown",
    ) -> dict[str, Any]:
        connector = self.get(connector_name)
        return await connector.invoke(
            tool_name, inputs, case_id=case_id, agent_id=agent_id
        )


# Process-level singleton
mcp_registry = MCPRegistry()
