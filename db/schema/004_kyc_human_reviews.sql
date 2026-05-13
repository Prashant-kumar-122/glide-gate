-- =============================================================================
-- 004_kyc_human_reviews.sql — kyc_checks, human_reviews
-- BRD: Section 15.2.1, FR-04, FR-13
-- =============================================================================

-- ---------------------------------------------------------------------------
-- kyc_checks
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kyc_checks (
    id                           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id                      UUID        NOT NULL,
    client_id                    UUID        NOT NULL,
    identity_score               NUMERIC(5,4),
    aml_score                    NUMERIC(5,4),
    profile_score                NUMERIC(5,4),
    composite_score              NUMERIC(5,4),
    risk_band                    VARCHAR(20),   -- LOW, MEDIUM, HIGH, VERY_HIGH
    identity_verification_result JSONB       NOT NULL DEFAULT '{}',
    aml_check_result             JSONB       NOT NULL DEFAULT '{}',
    sanctions_check_result       JSONB       NOT NULL DEFAULT '{}',
    checkpoint_rules_applied     JSONB       NOT NULL DEFAULT '[]',
    status                       VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    decision                     VARCHAR(30),
    decision_reason              TEXT,
    decided_at                   TIMESTAMPTZ,
    metadata                     JSONB       NOT NULL DEFAULT '{}',
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_kyc_case      FOREIGN KEY (case_id)   REFERENCES onboarding_cases (id),
    CONSTRAINT fk_kyc_client    FOREIGN KEY (client_id) REFERENCES clients (id),
    CONSTRAINT kyc_status_chk   CHECK (status   IN ('PENDING','PASSED','FAILED','ESCALATED')),
    CONSTRAINT kyc_decision_chk CHECK (decision IN ('APPROVED','REJECTED','ESCALATED') OR decision IS NULL),
    CONSTRAINT kyc_risk_band_chk CHECK (risk_band IN ('LOW','MEDIUM','HIGH','VERY_HIGH') OR risk_band IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_kyc_case_id    ON kyc_checks (case_id);
CREATE INDEX IF NOT EXISTS idx_kyc_client_id  ON kyc_checks (client_id);
CREATE INDEX IF NOT EXISTS idx_kyc_status     ON kyc_checks (status);
CREATE INDEX IF NOT EXISTS idx_kyc_risk_band  ON kyc_checks (risk_band);
CREATE INDEX IF NOT EXISTS idx_kyc_created_at ON kyc_checks (created_at DESC);

-- ---------------------------------------------------------------------------
-- human_reviews
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS human_reviews (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           UUID        NOT NULL,
    kyc_check_id      UUID        NOT NULL,
    reviewer_id       UUID,
    reviewer_role     VARCHAR(50),                    -- ComplianceOfficer
    status            VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    evidence_packet   JSONB       NOT NULL DEFAULT '{}',
    decision          VARCHAR(30),
    decision_notes    TEXT,
    escalation_reason TEXT,
    assigned_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at        TIMESTAMPTZ,
    metadata          JSONB       NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_hr_case      FOREIGN KEY (case_id)      REFERENCES onboarding_cases (id),
    CONSTRAINT fk_hr_kyc_check FOREIGN KEY (kyc_check_id) REFERENCES kyc_checks (id),
    CONSTRAINT hr_status_chk   CHECK (status   IN ('PENDING','APPROVED','REJECTED','MORE_INFO_REQUESTED')),
    CONSTRAINT hr_decision_chk CHECK (decision IN ('APPROVED','REJECTED','MORE_INFO_REQUESTED') OR decision IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_hr_case_id     ON human_reviews (case_id);
CREATE INDEX IF NOT EXISTS idx_hr_kyc_check   ON human_reviews (kyc_check_id);
CREATE INDEX IF NOT EXISTS idx_hr_status      ON human_reviews (status);
CREATE INDEX IF NOT EXISTS idx_hr_reviewer_id ON human_reviews (reviewer_id) WHERE reviewer_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_hr_created_at  ON human_reviews (created_at DESC);
