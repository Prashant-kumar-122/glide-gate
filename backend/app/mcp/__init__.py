from app.mcp.mcp_connector import MCPConnector, MCPRegistry, MCPToolDefinition, mcp_registry
from app.mcp.mcp_logger import MCPLogger, mcp_logger
from app.mcp.connectors.identity_verification.connector import identity_verification_connector
from app.mcp.connectors.document_management.connector import document_management_connector

# Register both simulated connectors at import time
mcp_registry.register(identity_verification_connector)
mcp_registry.register(document_management_connector)

__all__ = [
    "MCPConnector",
    "MCPRegistry",
    "MCPToolDefinition",
    "mcp_registry",
    "MCPLogger",
    "mcp_logger",
    "identity_verification_connector",
    "document_management_connector",
]
