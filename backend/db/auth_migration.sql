-- =============================================================================
-- ParaBula – Migração incremental de autenticação da API
-- Use em bancos que já possuem o schema antigo aplicado.
-- =============================================================================

CREATE TABLE IF NOT EXISTS api_users (
    id              UUID PRIMARY KEY,
    user_key        TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_tokens (
    id              UUID PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES api_users (id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL UNIQUE,
    token_preview   TEXT,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'api_users_user_key_format_check'
    ) THEN
        ALTER TABLE api_users
            ADD CONSTRAINT api_users_user_key_format_check
            CHECK (user_key ~ '^[a-z0-9][a-z0-9_.-]{1,79}$');
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'api_tokens_token_hash_length_check'
    ) THEN
        ALTER TABLE api_tokens
            ADD CONSTRAINT api_tokens_token_hash_length_check
            CHECK (length(token_hash) = 64);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_api_tokens_user_id
    ON api_tokens (user_id);

CREATE INDEX IF NOT EXISTS idx_api_tokens_active
    ON api_tokens (active);

CREATE TABLE IF NOT EXISTS api_access_logs (
    id              UUID PRIMARY KEY,
    user_id         UUID REFERENCES api_users (id) ON DELETE SET NULL,
    user_key        TEXT,
    api_token_id    UUID REFERENCES api_tokens (id) ON DELETE SET NULL,
    endpoint        TEXT NOT NULL,
    method          TEXT NOT NULL,
    status          TEXT NOT NULL
        CHECK (status IN ('allowed', 'forbidden')),
    reason          TEXT,
    ip_address      TEXT,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_access_logs_user_id
    ON api_access_logs (user_id);

CREATE INDEX IF NOT EXISTS idx_api_access_logs_created_at
    ON api_access_logs (created_at);

CREATE INDEX IF NOT EXISTS idx_api_access_logs_status
    ON api_access_logs (status);


ALTER TABLE analise_logs
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES api_users (id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS user_key TEXT,
    ADD COLUMN IF NOT EXISTS api_token_id UUID REFERENCES api_tokens (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_analise_logs_user_id
    ON analise_logs (user_id);
