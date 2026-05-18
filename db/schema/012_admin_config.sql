-- 012_admin_config.sql
-- Persistent storage for admin-configured settings that previously lived
-- only in process memory (lost on restart).
--
-- One row per namespace:
--   'validation_prompts'  →  { "identity": {"goal":"…","factors":[…]}, … }
--   'llm_config'          →  { "temperature": 0.3, "primary_provider": "openai", … }
--
-- Only overridden entries are stored; absent keys fall through to .env defaults.

CREATE TABLE IF NOT EXISTS admin_config (
    namespace   VARCHAR(50)                             PRIMARY KEY,
    config      JSONB       NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);
