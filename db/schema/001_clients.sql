-- =============================================================================
-- 001_clients.sql — clients, client_profiles, client_addresses
-- BRD: Section 15.2.1
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- clients
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clients (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                   VARCHAR(255) NOT NULL,
    phone                   VARCHAR(50),
    first_name              VARCHAR(100) NOT NULL,
    last_name               VARCHAR(100) NOT NULL,
    date_of_birth           DATE,
    nationality             VARCHAR(100),
    tax_residency           VARCHAR(100),
    employment_status       VARCHAR(50),   -- employed, self_employed, retired, student, unemployed
    annual_income           NUMERIC(15, 2),
    source_of_wealth        TEXT,
    risk_appetite           VARCHAR(20),   -- conservative, moderate, aggressive
    investment_experience   VARCHAR(20),   -- none, limited, moderate, extensive
    investment_horizon      VARCHAR(20),   -- short, medium, long
    kyc_status              VARCHAR(20)    NOT NULL DEFAULT 'PENDING',  -- PENDING, PASSED, FAILED, ESCALATED
    metadata                JSONB          NOT NULL DEFAULT '{}',
    created_at              TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ    NOT NULL DEFAULT NOW(),

    CONSTRAINT clients_email_uq           UNIQUE (email),
    CONSTRAINT clients_kyc_status_chk     CHECK (kyc_status IN ('PENDING','PASSED','FAILED','ESCALATED')),
    CONSTRAINT clients_risk_appetite_chk  CHECK (risk_appetite IN ('conservative','moderate','aggressive') OR risk_appetite IS NULL),
    CONSTRAINT clients_employment_chk     CHECK (employment_status IN ('employed','self_employed','retired','student','unemployed') OR employment_status IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_clients_email      ON clients (email);
CREATE INDEX IF NOT EXISTS idx_clients_kyc_status ON clients (kyc_status);
CREATE INDEX IF NOT EXISTS idx_clients_created_at ON clients (created_at DESC);

-- ---------------------------------------------------------------------------
-- client_profiles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS client_profiles (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id                       UUID        NOT NULL,
    profile_data                    JSONB       NOT NULL DEFAULT '{}',
    consent_marketing               BOOLEAN     NOT NULL DEFAULT FALSE,
    consent_data_processing         BOOLEAN     NOT NULL DEFAULT TRUE,
    preferred_communication_channel VARCHAR(20) NOT NULL DEFAULT 'email',  -- email, sms, in_app
    language_preference             VARCHAR(10) NOT NULL DEFAULT 'en',
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_cp_client FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE,
    CONSTRAINT client_profiles_client_uq UNIQUE (client_id),
    CONSTRAINT cp_channel_chk CHECK (preferred_communication_channel IN ('email','sms','in_app'))
);

CREATE INDEX IF NOT EXISTS idx_client_profiles_client_id ON client_profiles (client_id);

-- ---------------------------------------------------------------------------
-- client_addresses
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS client_addresses (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id    UUID         NOT NULL,
    address_type VARCHAR(20)  NOT NULL,  -- residential, mailing, business
    line1        VARCHAR(255) NOT NULL,
    line2        VARCHAR(255),
    city         VARCHAR(100),
    state        VARCHAR(100),
    postal_code  VARCHAR(20),
    country      VARCHAR(100) NOT NULL,
    is_primary   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ca_client        FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE,
    CONSTRAINT ca_address_type_chk CHECK (address_type IN ('residential','mailing','business'))
);

CREATE INDEX IF NOT EXISTS idx_client_addresses_client_id ON client_addresses (client_id);
CREATE INDEX IF NOT EXISTS idx_client_addresses_primary   ON client_addresses (client_id, is_primary);
