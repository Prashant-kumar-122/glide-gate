-- =============================================================================
-- 007_event_logs.sql — event_logs  (append-only audit trail)
-- BRD: Section 15.2.2, FR-14
-- NOTE: No updated_at column — this table is strictly append-only.
-- =============================================================================

CREATE TABLE IF NOT EXISTS event_logs (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           UUID,                   -- nullable for system-level events
    client_id         UUID,                   -- nullable
    agent_id          VARCHAR(50),            -- which agent emitted this event
    event_type        VARCHAR(100) NOT NULL,
    event_category    VARCHAR(50),            -- AGENT_ACTION, DOCUMENT, KYC, NOTIFICATION, COMPLIANCE, SYSTEM
    entity_type       VARCHAR(50),            -- document, case, client, review, task
    entity_id         UUID,
    actor_id          VARCHAR(100),           -- user UUID or agent_id string
    actor_role        VARCHAR(50),            -- Advisor, Client, ComplianceOfficer, CCRep, system
    payload           JSONB       NOT NULL DEFAULT '{}',
    is_compliance_event BOOLEAN   NOT NULL DEFAULT FALSE,
    ip_address        VARCHAR(45),
    user_agent        TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- No updated_at: append-only table
);

CREATE INDEX IF NOT EXISTS idx_el_case_id            ON event_logs (case_id)    WHERE case_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_el_client_id          ON event_logs (client_id)  WHERE client_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_el_agent_id           ON event_logs (agent_id)   WHERE agent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_el_event_type         ON event_logs (event_type);
CREATE INDEX IF NOT EXISTS idx_el_event_category     ON event_logs (event_category);
CREATE INDEX IF NOT EXISTS idx_el_entity             ON event_logs (entity_type, entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_el_is_compliance      ON event_logs (is_compliance_event) WHERE is_compliance_event = TRUE;
CREATE INDEX IF NOT EXISTS idx_el_created_at         ON event_logs (created_at DESC);
