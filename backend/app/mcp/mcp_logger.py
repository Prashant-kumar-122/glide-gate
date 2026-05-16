from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger

from app.database import AsyncSessionLocal
from app.models.agents import MCPToolCall
from app.services.audit.audit_log_service import audit_log_service


class MCPLogger:
    """Persists every MCP tool invocation to mcp_tool_calls with is_simulated=True."""

    async def log(
        self,
        *,
        connector_name: str,
        tool_name: str,
        agent_id: str,
        inputs: dict[str, Any],
        output: dict[str, Any],
        status: str,
        latency_ms: int,
        case_id: UUID | None = None,
        error_message: str | None = None,
        is_simulated: bool = True,
    ) -> None:
        try:
            async with AsyncSessionLocal() as session:
                record = MCPToolCall(
                    case_id=case_id,
                    agent_id=agent_id,
                    connector_name=connector_name,
                    tool_name=tool_name,
                    input_payload=inputs,
                    output_payload=output,
                    status=status,
                    is_simulated=is_simulated,
                    latency_ms=latency_ms,
                    error_message=error_message,
                    completed_at=datetime.utcnow(),
                )
                session.add(record)
                await audit_log_service.log_mcp_tool_called(
                    connector=connector_name,
                    tool=tool_name,
                    agent_id=agent_id,
                    case_id=case_id,
                    status=status,
                    latency_ms=latency_ms,
                    is_simulated=is_simulated,
                    db=session,
                )
                await session.commit()
                logger.debug(
                    f"MCPLogger: {connector_name}.{tool_name} "
                    f"[{status}] {latency_ms}ms case={case_id}"
                )
        except Exception as exc:
            # Never let logging failures break the caller
            logger.warning(f"MCPLogger: failed to persist call record: {exc}")


# Module-level singleton
mcp_logger = MCPLogger()
