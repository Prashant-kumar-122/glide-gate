-- =============================================================================
-- 002_onboarding_cases.sql — onboarding_cases, products, case_products,
--                             case_product_steps
-- BRD: Section 15.2.1
-- =============================================================================

-- ---------------------------------------------------------------------------
-- onboarding_cases
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_cases (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           UUID        NOT NULL,
    status              VARCHAR(30) NOT NULL DEFAULT 'INTAKE',
    current_stage       VARCHAR(30) NOT NULL DEFAULT 'INTAKE',
    selected_products   TEXT[]      NOT NULL DEFAULT '{}',
    shared_context      JSONB       NOT NULL DEFAULT '{}',   -- persisted OnboardingState
    assigned_advisor_id UUID,
    sla_deadline        TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    metadata            JSONB       NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_oc_client      FOREIGN KEY (client_id) REFERENCES clients (id),
    CONSTRAINT oc_status_chk     CHECK (status IN ('INTAKE','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED')),
    CONSTRAINT oc_stage_chk      CHECK (current_stage IN ('INTAKE','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED'))
);

CREATE INDEX IF NOT EXISTS idx_oc_client_id     ON onboarding_cases (client_id);
CREATE INDEX IF NOT EXISTS idx_oc_status        ON onboarding_cases (status);
CREATE INDEX IF NOT EXISTS idx_oc_current_stage ON onboarding_cases (current_stage);
CREATE INDEX IF NOT EXISTS idx_oc_created_at    ON onboarding_cases (created_at DESC);

-- ---------------------------------------------------------------------------
-- products
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    product_code         VARCHAR(50) NOT NULL,
    name                 VARCHAR(200) NOT NULL,
    description          TEXT,
    is_active            BOOLEAN     NOT NULL DEFAULT TRUE,
    required_documents   TEXT[]      NOT NULL DEFAULT '{}',
    suitability_criteria JSONB       NOT NULL DEFAULT '{}',
    step_sequence        JSONB       NOT NULL DEFAULT '[]',
    metadata             JSONB       NOT NULL DEFAULT '{}',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT products_code_uq UNIQUE (product_code)
);

CREATE INDEX IF NOT EXISTS idx_products_code      ON products (product_code);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON products (is_active);

-- ---------------------------------------------------------------------------
-- case_products
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_products (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id              UUID        NOT NULL,
    product_id           UUID        NOT NULL,
    product_code         VARCHAR(50) NOT NULL,
    status               VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    suitability_outcome  JSONB       NOT NULL DEFAULT '{}',
    account_number       VARCHAR(100),
    started_at           TIMESTAMPTZ,
    completed_at         TIMESTAMPTZ,
    metadata             JSONB       NOT NULL DEFAULT '{}',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_cp_case    FOREIGN KEY (case_id)    REFERENCES onboarding_cases (id),
    CONSTRAINT fk_cp_product FOREIGN KEY (product_id) REFERENCES products (id),
    CONSTRAINT cp_status_chk CHECK (status IN ('PENDING','IN_PROGRESS','COMPLETE','FAILED','SKIPPED'))
);

CREATE INDEX IF NOT EXISTS idx_case_products_case_id      ON case_products (case_id);
CREATE INDEX IF NOT EXISTS idx_case_products_product_code ON case_products (product_code);
CREATE INDEX IF NOT EXISTS idx_case_products_status       ON case_products (status);

-- ---------------------------------------------------------------------------
-- case_product_steps
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_product_steps (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_product_id  UUID        NOT NULL,
    step_name        VARCHAR(100) NOT NULL,
    step_index       INTEGER     NOT NULL,
    status           VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    result           JSONB       NOT NULL DEFAULT '{}',
    started_at       TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_cps_case_product FOREIGN KEY (case_product_id) REFERENCES case_products (id) ON DELETE CASCADE,
    CONSTRAINT cps_status_chk      CHECK (status IN ('PENDING','IN_PROGRESS','COMPLETE','FAILED','SKIPPED'))
);

CREATE INDEX IF NOT EXISTS idx_cps_case_product_id ON case_product_steps (case_product_id);
CREATE INDEX IF NOT EXISTS idx_cps_status           ON case_product_steps (status);
