-- =============================================================================
-- 008_mcp_tool_calls.sql — mcp_tool_calls
-- BRD: Section 15.2.2, Section 5.3, FR-04, FR-06
-- =============================================================================

CREATE TABLE IF NOT EXISTS mcp_tool_calls (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id          UUID,
    agent_id         VARCHAR(50) NOT NULL,
    connector_name   VARCHAR(100) NOT NULL,
    tool_name        VARCHAR(100) NOT NULL,
    input_payload    JSONB       NOT NULL DEFAULT '{}',
    output_payload   JSONB       NOT NULL DEFAULT '{}',
    status           VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    is_simulated     BOOLEAN     NOT NULL DEFAULT TRUE,
    latency_ms       INTEGER,
    error_message    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ,

    CONSTRAINT fk_mcp_case    FOREIGN KEY (case_id) REFERENCES onboarding_cases (id),
    CONSTRAINT mcp_status_chk CHECK (status IN ('PENDING','SUCCESS','FAILED','TIMEOUT'))
);

CREATE INDEX IF NOT EXISTS idx_mcp_case_id        ON mcp_tool_calls (case_id)       WHERE case_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mcp_agent_id       ON mcp_tool_calls (agent_id);
CREATE INDEX IF NOT EXISTS idx_mcp_connector_name ON mcp_tool_calls (connector_name);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_name      ON mcp_tool_calls (tool_name);
CREATE INDEX IF NOT EXISTS idx_mcp_is_simulated   ON mcp_tool_calls (is_simulated);
CREATE INDEX IF NOT EXISTS idx_mcp_created_at     ON mcp_tool_calls (created_at DESC);
