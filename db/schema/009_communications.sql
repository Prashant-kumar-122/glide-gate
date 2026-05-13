-- =============================================================================
-- 009_communications.sql — notifications, case_summaries,
--                           collaboration_rooms, collaboration_participants,
--                           collaboration_comments, conversation_messages
-- BRD: Section 15.2.3, Section 7.3–7.4
-- =============================================================================

-- ---------------------------------------------------------------------------
-- notifications
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id          UUID,
    client_id        UUID,
    template_name    VARCHAR(100),
    channel          VARCHAR(30) NOT NULL,     -- email, sms, in_app
    recipient_email  VARCHAR(255),
    recipient_phone  VARCHAR(50),
    subject          TEXT,
    body             TEXT,
    status           VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    is_simulated     BOOLEAN     NOT NULL DEFAULT TRUE,
    sent_at          TIMESTAMPTZ,
    metadata         JSONB       NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_notif_case      FOREIGN KEY (case_id)   REFERENCES onboarding_cases (id),
    CONSTRAINT fk_notif_client    FOREIGN KEY (client_id) REFERENCES clients (id),
    CONSTRAINT notif_channel_chk  CHECK (channel IN ('email','sms','in_app')),
    CONSTRAINT notif_status_chk   CHECK (status  IN ('PENDING','SENT','FAILED','BOUNCED'))
);

CREATE INDEX IF NOT EXISTS idx_notif_case_id   ON notifications (case_id)   WHERE case_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notif_client_id ON notifications (client_id) WHERE client_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notif_status    ON notifications (status);
CREATE INDEX IF NOT EXISTS idx_notif_channel   ON notifications (channel);
CREATE INDEX IF NOT EXISTS idx_notif_created   ON notifications (created_at DESC);

-- ---------------------------------------------------------------------------
-- case_summaries
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_summaries (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id       UUID        NOT NULL,
    summary_type  VARCHAR(50) NOT NULL,    -- call_summary, stage_summary, ai_summary
    content       TEXT        NOT NULL,
    model_used    VARCHAR(100),
    generated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata      JSONB       NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_cs_case  FOREIGN KEY (case_id) REFERENCES onboarding_cases (id),
    CONSTRAINT cs_type_chk CHECK (summary_type IN ('call_summary','stage_summary','ai_summary'))
);

CREATE INDEX IF NOT EXISTS idx_cs_case_id ON case_summaries (case_id);
CREATE INDEX IF NOT EXISTS idx_cs_type    ON case_summaries (summary_type);
CREATE INDEX IF NOT EXISTS idx_cs_created ON case_summaries (created_at DESC);

-- ---------------------------------------------------------------------------
-- collaboration_rooms  (DB backing for CollaborationAgent — STEP-08 is in-memory)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS collaboration_rooms (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id    UUID        NOT NULL,
    room_name  VARCHAR(200),
    status     VARCHAR(30) NOT NULL DEFAULT 'OPEN',   -- OPEN, CLOSED, ARCHIVED
    metadata   JSONB       NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_cr_case    FOREIGN KEY (case_id) REFERENCES onboarding_cases (id),
    CONSTRAINT cr_status_chk CHECK (status IN ('OPEN','CLOSED','ARCHIVED'))
);

CREATE INDEX IF NOT EXISTS idx_cr_case_id ON collaboration_rooms (case_id);
CREATE INDEX IF NOT EXISTS idx_cr_status  ON collaboration_rooms (status);

-- ---------------------------------------------------------------------------
-- collaboration_participants
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS collaboration_participants (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id        UUID         NOT NULL,
    participant_id VARCHAR(100) NOT NULL,   -- user UUID or agent_id
    role           VARCHAR(50)  NOT NULL,   -- Advisor, Client, ComplianceOfficer, CCRep, system
    joined_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    left_at        TIMESTAMPTZ,
    metadata       JSONB        NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_cpart_room  FOREIGN KEY (room_id) REFERENCES collaboration_rooms (id) ON DELETE CASCADE,
    CONSTRAINT cpart_role_chk CHECK (role IN ('Advisor','Client','ComplianceOfficer','CCRep','system'))
);

CREATE INDEX IF NOT EXISTS idx_cpart_room_id        ON collaboration_participants (room_id);
CREATE INDEX IF NOT EXISTS idx_cpart_participant_id ON collaboration_participants (participant_id);

-- ---------------------------------------------------------------------------
-- collaboration_comments
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS collaboration_comments (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id     UUID         NOT NULL,
    case_id     UUID         NOT NULL,
    author_id   VARCHAR(100) NOT NULL,     -- user UUID or agent_id
    author_role VARCHAR(50),
    content     TEXT         NOT NULL,
    visibility  VARCHAR(30)  NOT NULL DEFAULT 'team',  -- team, client_visible, compliance_only
    document_id UUID,                      -- optional: anchored to a document
    parent_id   UUID,                      -- optional: threaded reply
    metadata    JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_cc_room        FOREIGN KEY (room_id)     REFERENCES collaboration_rooms (id) ON DELETE CASCADE,
    CONSTRAINT fk_cc_case        FOREIGN KEY (case_id)     REFERENCES onboarding_cases (id),
    CONSTRAINT fk_cc_document    FOREIGN KEY (document_id) REFERENCES documents (id),
    CONSTRAINT fk_cc_parent      FOREIGN KEY (parent_id)   REFERENCES collaboration_comments (id),
    CONSTRAINT cc_visibility_chk CHECK (visibility IN ('team','client_visible','compliance_only'))
);

CREATE INDEX IF NOT EXISTS idx_cc_room_id   ON collaboration_comments (room_id);
CREATE INDEX IF NOT EXISTS idx_cc_case_id   ON collaboration_comments (case_id);
CREATE INDEX IF NOT EXISTS idx_cc_author_id ON collaboration_comments (author_id);
CREATE INDEX IF NOT EXISTS idx_cc_doc_id    ON collaboration_comments (document_id) WHERE document_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cc_created   ON collaboration_comments (created_at DESC);

-- ---------------------------------------------------------------------------
-- conversation_messages  (CustomerServiceAgent chat history for resumption)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversation_messages (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID        NOT NULL,
    client_id   UUID        NOT NULL,
    role        VARCHAR(20) NOT NULL,   -- user, assistant, system
    content     TEXT        NOT NULL,
    tokens_used INTEGER,
    metadata    JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_cm_case   FOREIGN KEY (case_id)   REFERENCES onboarding_cases (id),
    CONSTRAINT fk_cm_client FOREIGN KEY (client_id) REFERENCES clients (id),
    CONSTRAINT cm_role_chk  CHECK (role IN ('user','assistant','system'))
);

CREATE INDEX IF NOT EXISTS idx_cm_case_id   ON conversation_messages (case_id);
CREATE INDEX IF NOT EXISTS idx_cm_client_id ON conversation_messages (client_id);
CREATE INDEX IF NOT EXISTS idx_cm_created   ON conversation_messages (created_at ASC);
