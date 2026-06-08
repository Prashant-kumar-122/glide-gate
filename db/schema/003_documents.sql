-- =============================================================================
-- 003_documents.sql — documents (6-state lifecycle)
-- BRD: Section 15.2.1
-- Document status lifecycle:
--   NOT_REQUESTED → REQUESTED → RECEIVED → UNDER_REVIEW → NEEDS_REVISION → APPROVED
-- =============================================================================

CREATE TYPE document_status AS ENUM (
    'NOT_REQUESTED',
    'REQUESTED',
    'RECEIVED',
    'UNDER_REVIEW',
    'NEEDS_REVISION',
    'APPROVED'
);

CREATE TABLE IF NOT EXISTS documents (
    id                    UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id               UUID            NOT NULL,
    client_id             UUID            NOT NULL,
    document_type         VARCHAR(100)    NOT NULL,
    category              VARCHAR(50)     NOT NULL,     -- identity, financial, legal, insurance, compliance, entity
    status                document_status NOT NULL DEFAULT 'NOT_REQUESTED',
    original_filename     VARCHAR(500),
    storage_path          VARCHAR(1000),
    file_size_bytes       BIGINT,
    mime_type             VARCHAR(100),
    ocr_result            JSONB           NOT NULL DEFAULT '{}',
    classification_result JSONB           NOT NULL DEFAULT '{}',
    validation_result     JSONB           NOT NULL DEFAULT '{}',
    diff_result           JSONB           NOT NULL DEFAULT '{}',
    version               INTEGER         NOT NULL DEFAULT 1,
    parent_doc_id         UUID,                          -- previous version of this document
    uploaded_by           VARCHAR(50),                   -- advisor, client
    tags                  TEXT[]          NOT NULL DEFAULT '{}',
    metadata              JSONB           NOT NULL DEFAULT '{}',
    uploaded_at           TIMESTAMPTZ,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_doc_case       FOREIGN KEY (case_id)      REFERENCES onboarding_cases (id),
    CONSTRAINT fk_doc_client     FOREIGN KEY (client_id)    REFERENCES clients (id),
    CONSTRAINT fk_doc_parent     FOREIGN KEY (parent_doc_id) REFERENCES documents (id),
    CONSTRAINT doc_category_chk  CHECK (category IN ('identity','financial','legal','insurance','compliance','entity')),
    CONSTRAINT doc_uploaded_by_chk CHECK (uploaded_by IN ('advisor','client') OR uploaded_by IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_docs_case_id   ON documents (case_id);
CREATE INDEX IF NOT EXISTS idx_docs_client_id ON documents (client_id);
CREATE INDEX IF NOT EXISTS idx_docs_status    ON documents (status);
CREATE INDEX IF NOT EXISTS idx_docs_category  ON documents (category);
CREATE INDEX IF NOT EXISTS idx_docs_type      ON documents (document_type);
CREATE INDEX IF NOT EXISTS idx_docs_parent    ON documents (parent_doc_id) WHERE parent_doc_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_docs_created   ON documents (created_at DESC);
