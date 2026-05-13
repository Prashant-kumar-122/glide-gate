-- =============================================================================
-- 006_agent_tasks.sql — agent_tasks  (persisted TaskPacket + response)
-- BRD: Section 15.2.2, FR-03
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_tasks (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    from_agent      VARCHAR(50) NOT NULL,
    to_agent        VARCHAR(50) NOT NULL,
    task_type       VARCHAR(100) NOT NULL,
    case_id         UUID        NOT NULL,
    client_id       UUID        NOT NULL,
    priority        VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
    payload         JSONB       NOT NULL DEFAULT '{}',
    expected_schema VARCHAR(200),
    status          VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    result          JSONB       NOT NULL DEFAULT '{}',
    errors          JSONB       NOT NULL DEFAULT '[]',
    duration_ms     INTEGER,
    ttl             INTEGER     NOT NULL DEFAULT 300,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,

    CONSTRAINT fk_at_case       FOREIGN KEY (case_id)   REFERENCES onboarding_cases (id),
    CONSTRAINT fk_at_client     FOREIGN KEY (client_id) REFERENCES clients (id),
    CONSTRAINT at_priority_chk  CHECK (priority IN ('LOW','NORMAL','HIGH','CRITICAL')),
    CONSTRAINT at_status_chk    CHECK (status   IN ('PENDING','IN_PROGRESS','SUCCESS','PARTIAL','FAILED','ESCALATED'))
);

CREATE INDEX IF NOT EXISTS idx_at_case_id    ON agent_tasks (case_id);
CREATE INDEX IF NOT EXISTS idx_at_client_id  ON agent_tasks (client_id);
CREATE INDEX IF NOT EXISTS idx_at_from_agent ON agent_tasks (from_agent);
CREATE INDEX IF NOT EXISTS idx_at_to_agent   ON agent_tasks (to_agent);
CREATE INDEX IF NOT EXISTS idx_at_status     ON agent_tasks (status);
CREATE INDEX IF NOT EXISTS idx_at_created_at ON agent_tasks (created_at DESC);
