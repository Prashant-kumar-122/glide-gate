-- =============================================================================
-- 010_questionnaire.sql — onboarding_questionnaires, onboarding_questions,
--                          onboarding_question_rules, onboarding_answers,
--                          onboarding_question_sessions
-- BRD: Section 15.2.4, Section 15.3
-- =============================================================================

-- ---------------------------------------------------------------------------
-- onboarding_questionnaires
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_questionnaires (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    version     INTEGER     NOT NULL DEFAULT 1,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    sections    JSONB       NOT NULL DEFAULT '[]',   -- ordered list of section names
    metadata    JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oq_is_active ON onboarding_questionnaires (is_active);
CREATE INDEX IF NOT EXISTS idx_oq_version   ON onboarding_questionnaires (version);

-- ---------------------------------------------------------------------------
-- onboarding_questions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_questions (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    questionnaire_id  UUID        NOT NULL,
    section           VARCHAR(100) NOT NULL,
    question_key      VARCHAR(100) NOT NULL,   -- field key, e.g. "annual_income"
    question_text     TEXT        NOT NULL,
    question_type     VARCHAR(30) NOT NULL,    -- text, number, select, multi_select, date, boolean
    options           JSONB       NOT NULL DEFAULT '[]',    -- choices for select types
    validation_rules  JSONB       NOT NULL DEFAULT '{}',   -- min, max, required, regex
    show_if           JSONB,                               -- conditional display rule
    order_index       INTEGER     NOT NULL,
    is_required       BOOLEAN     NOT NULL DEFAULT TRUE,
    metadata          JSONB       NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_oqn_questionnaire FOREIGN KEY (questionnaire_id) REFERENCES onboarding_questionnaires (id) ON DELETE CASCADE,
    CONSTRAINT oqn_type_chk         CHECK (question_type IN ('text','number','select','multi_select','date','boolean','currency')),
    CONSTRAINT oqn_key_uq           UNIQUE (questionnaire_id, question_key)
);

CREATE INDEX IF NOT EXISTS idx_oqn_questionnaire_id ON onboarding_questions (questionnaire_id);
CREATE INDEX IF NOT EXISTS idx_oqn_section          ON onboarding_questions (section);
CREATE INDEX IF NOT EXISTS idx_oqn_order_index      ON onboarding_questions (questionnaire_id, order_index);

-- ---------------------------------------------------------------------------
-- onboarding_question_rules
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_question_rules (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID        NOT NULL,
    rule_type   VARCHAR(50) NOT NULL,   -- show_if, validate, skip
    condition   JSONB       NOT NULL,   -- e.g. {"field":"annual_income","operator":"gt","value":250000}
    action      JSONB       NOT NULL DEFAULT '{}',
    priority    INTEGER     NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_oqr_question FOREIGN KEY (question_id) REFERENCES onboarding_questions (id) ON DELETE CASCADE,
    CONSTRAINT oqr_rule_type_chk CHECK (rule_type IN ('show_if','validate','skip','require'))
);

CREATE INDEX IF NOT EXISTS idx_oqr_question_id ON onboarding_question_rules (question_id);
CREATE INDEX IF NOT EXISTS idx_oqr_rule_type   ON onboarding_question_rules (rule_type);

-- ---------------------------------------------------------------------------
-- onboarding_answers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_answers (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id          UUID        NOT NULL,
    client_id        UUID        NOT NULL,
    questionnaire_id UUID        NOT NULL,
    question_id      UUID        NOT NULL,
    question_key     VARCHAR(100) NOT NULL,
    answer_value     JSONB,                  -- flexible: string, number, list, bool
    answered_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata         JSONB       NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_oa_case            FOREIGN KEY (case_id)          REFERENCES onboarding_cases (id),
    CONSTRAINT fk_oa_client          FOREIGN KEY (client_id)        REFERENCES clients (id),
    CONSTRAINT fk_oa_questionnaire   FOREIGN KEY (questionnaire_id) REFERENCES onboarding_questionnaires (id),
    CONSTRAINT fk_oa_question        FOREIGN KEY (question_id)      REFERENCES onboarding_questions (id),
    CONSTRAINT oa_case_question_uq   UNIQUE (case_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_oa_case_id          ON onboarding_answers (case_id);
CREATE INDEX IF NOT EXISTS idx_oa_client_id        ON onboarding_answers (client_id);
CREATE INDEX IF NOT EXISTS idx_oa_questionnaire_id ON onboarding_answers (questionnaire_id);
CREATE INDEX IF NOT EXISTS idx_oa_question_key     ON onboarding_answers (question_key);

-- ---------------------------------------------------------------------------
-- onboarding_question_sessions  (enables paused journey resumption — FR-12)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_question_sessions (
    id                       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id                  UUID        NOT NULL,
    client_id                UUID        NOT NULL,
    questionnaire_id         UUID        NOT NULL,
    status                   VARCHAR(30) NOT NULL DEFAULT 'IN_PROGRESS',
    current_section          VARCHAR(100),
    current_question_index   INTEGER     NOT NULL DEFAULT 0,
    completed_sections       TEXT[]      NOT NULL DEFAULT '{}',
    session_data             JSONB       NOT NULL DEFAULT '{}',   -- partial answers + state
    paused_at                TIMESTAMPTZ,
    resumed_at               TIMESTAMPTZ,
    completed_at             TIMESTAMPTZ,
    metadata                 JSONB       NOT NULL DEFAULT '{}',
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_oqs_case            FOREIGN KEY (case_id)          REFERENCES onboarding_cases (id),
    CONSTRAINT fk_oqs_client          FOREIGN KEY (client_id)        REFERENCES clients (id),
    CONSTRAINT fk_oqs_questionnaire   FOREIGN KEY (questionnaire_id) REFERENCES onboarding_questionnaires (id),
    CONSTRAINT oqs_status_chk         CHECK (status IN ('IN_PROGRESS','PAUSED','COMPLETED','ABANDONED')),
    CONSTRAINT oqs_case_q_uq          UNIQUE (case_id, questionnaire_id)
);

CREATE INDEX IF NOT EXISTS idx_oqs_case_id          ON onboarding_question_sessions (case_id);
CREATE INDEX IF NOT EXISTS idx_oqs_client_id        ON onboarding_question_sessions (client_id);
CREATE INDEX IF NOT EXISTS idx_oqs_status           ON onboarding_question_sessions (status);
CREATE INDEX IF NOT EXISTS idx_oqs_questionnaire_id ON onboarding_question_sessions (questionnaire_id);
