from __future__ import annotations

import abc
from typing import Any
from uuid import UUID

from loguru import logger
from pydantic import BaseModel

# ── Per-process grant cache ────────────────────────────────────────────────────
# Key: (domain_code, agent_id, connector_id, tool_name) → granted bool
# Populated lazily on first invoke; cleared on process restart.
_grant_cache: dict[tuple[str, str, str, str], bool] = {}


async def _check_tool_grant(
    domain_code: str,
    agent_id: str,
    connector_id: str,
    tool_name: str,
) -> None:
    """Raise PermissionError if agent is not granted the tool (ADR-007).

    Fails closed when the domain exists but grants are absent.
    Logs a warning and allows through when the domain row is not yet seeded
    (migration ordering safety) or when the DB is unreachable.
    """
    if agent_id == "unknown":
        return  # legacy callers not tracked through domain config

    cache_key = (domain_code, agent_id, connector_id, tool_name)
    if cache_key in _grant_cache:
        if not _grant_cache[cache_key]:
            raise PermissionError(
                f"Agent {agent_id!r} is not granted {connector_id!r}.{tool_name!r} "
                f"in domain {domain_code!r}. "
                "Add a row to domain_agent_tool_grants. (ADR-007)"
            )
        return

    try:
        from app.database import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            granted = bool(await session.scalar(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM domain_agent_tool_grants g
                    JOIN domains d ON d.id = g.domain_id
                    WHERE d.domain_code = :domain_code
                      AND g.agent_id    = :agent_id
                      AND g.connector_id = :connector_id
                      AND g.tool_name   = :tool_name
                )
                """
            ), {
                "domain_code": domain_code,
                "agent_id": agent_id,
                "connector_id": connector_id,
                "tool_name": tool_name,
            }))

        _grant_cache[cache_key] = granted

        if not granted:
            async with AsyncSessionLocal() as session:
                domain_exists = bool(await session.scalar(text(
                    "SELECT EXISTS(SELECT 1 FROM domains WHERE domain_code = :code)"
                ), {"code": domain_code}))

            if domain_exists:
                raise PermissionError(
                    f"Agent {agent_id!r} is not granted {connector_id!r}.{tool_name!r} "
                    f"in domain {domain_code!r}. "
                    "Add a row to domain_agent_tool_grants. (ADR-007)"
                )
            logger.warning(
                f"Domain {domain_code!r} not found — skipping grant check for "
                f"{agent_id!r}.{connector_id!r}.{tool_name!r}"
            )

    except PermissionError:
        raise
    except Exception as exc:
        logger.warning(f"MCPRegistry grant check failed (non-fatal): {exc}")


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
        domain_code: str = "wealth_management",
    ) -> dict[str, Any]:
        await _check_tool_grant(domain_code, agent_id, connector_name, tool_name)
        connector = self.get(connector_name)
        return await connector.invoke(
            tool_name, inputs, case_id=case_id, agent_id=agent_id
        )


# Process-level singleton
mcp_registry = MCPRegistry()
