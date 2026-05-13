-- =============================================================================
-- 005_agents.sql — agents
-- BRD: Section 15.2.2
-- =============================================================================

CREATE TABLE IF NOT EXISTS agents (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id     VARCHAR(50) NOT NULL,   -- matches AgentID enum
    name         VARCHAR(100) NOT NULL,
    description  TEXT,
    agent_type   VARCHAR(50) NOT NULL,
    config       JSONB       NOT NULL DEFAULT '{}',
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    capabilities TEXT[]      NOT NULL DEFAULT '{}',
    llm_provider VARCHAR(30),
    llm_model    VARCHAR(100),
    metadata     JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT agents_agent_id_uq UNIQUE (agent_id)
);

CREATE INDEX IF NOT EXISTS idx_agents_agent_id   ON agents (agent_id);
CREATE INDEX IF NOT EXISTS idx_agents_is_active  ON agents (is_active);
CREATE INDEX IF NOT EXISTS idx_agents_agent_type ON agents (agent_type);
