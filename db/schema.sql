-- =============================================================================
-- ParaBula – Schema do banco de dados
-- PostgreSQL 14+
-- =============================================================================

-- Extensão para remover acentos na busca por nome
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Função imutável que envolve unaccent + lower
-- (unaccent não é IMMUTABLE por padrão; o wrapper é necessário para índices)
CREATE OR REPLACE FUNCTION normalize_text(TEXT)
    RETURNS TEXT
    LANGUAGE SQL
    IMMUTABLE STRICT
AS $$
    SELECT lower(unaccent($1));
$$;


-- =============================================================================
-- medicamento
-- Entidade central. Um registro por princípio ativo.
-- =============================================================================
CREATE TABLE medicamento (
    id                  SERIAL PRIMARY KEY,
    principio_ativo     TEXT NOT NULL,
    anvisa_processo     TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Busca por nome sem se preocupar com caixa/acentos
CREATE UNIQUE INDEX idx_medicamento_principio_normalizado
    ON medicamento (normalize_text(principio_ativo));

-- Processo ANVISA é único quando presente
CREATE UNIQUE INDEX idx_medicamento_anvisa_processo
    ON medicamento (anvisa_processo)
    WHERE anvisa_processo IS NOT NULL;


-- =============================================================================
-- medicamento_alias
-- Nomes comerciais, sinônimos e abreviações.
-- Permite buscar "Glifage" e encontrar "metformina".
-- =============================================================================
CREATE TABLE medicamento_alias (
    id              SERIAL PRIMARY KEY,
    medicamento_id  INTEGER NOT NULL REFERENCES medicamento (id) ON DELETE CASCADE,
    alias           TEXT NOT NULL,
    tipo_alias      TEXT NOT NULL CHECK (tipo_alias IN ('comercial', 'sinonimo', 'abreviacao')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_alias_normalizado
    ON medicamento_alias (normalize_text(alias));

CREATE INDEX idx_alias_medicamento_id
    ON medicamento_alias (medicamento_id);


-- =============================================================================
-- bula_versao
-- Conteúdo completo de cada versão de bula.
-- Suporta versionamento: só uma bula vigente por medicamento.
-- =============================================================================
CREATE TABLE bula_versao (
    id              SERIAL PRIMARY KEY,
    medicamento_id  INTEGER NOT NULL REFERENCES medicamento (id) ON DELETE CASCADE,
    fonte_url       TEXT,
    pdf_path        TEXT,
    hash_conteudo   TEXT,                  -- SHA-256 do PDF; evita reingestão desnecessária
    conteudo_json   JSONB NOT NULL,        -- seções da bula (CABECALHO, INDICACOES, etc.)
    vigente         BOOLEAN NOT NULL DEFAULT TRUE,
    data_publicacao DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Garante no máximo uma bula vigente por medicamento
CREATE UNIQUE INDEX idx_bula_versao_vigente
    ON bula_versao (medicamento_id)
    WHERE vigente = TRUE;

CREATE INDEX idx_bula_versao_medicamento_id
    ON bula_versao (medicamento_id);

CREATE INDEX idx_bula_versao_hash
    ON bula_versao (hash_conteudo)
    WHERE hash_conteudo IS NOT NULL;


-- =============================================================================
-- bula_cache
-- Metadados de cache. Não duplica o conteúdo da bula.
-- Rastreia quais bulas estão "quentes" (top ~100).
-- Política: LRU + frequência de acesso.
-- =============================================================================
CREATE TABLE bula_cache (
    id              SERIAL PRIMARY KEY,
    bula_id         INTEGER NOT NULL UNIQUE REFERENCES bula_versao (id) ON DELETE CASCADE,
    access_count    INTEGER NOT NULL DEFAULT 1,
    last_access_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,           -- NULL = sem expiração por tempo
    rank            INTEGER                -- posição no ranking (1 = mais acessado)
);

-- Queries de LRU e de evição consultam esses campos frequentemente
CREATE INDEX idx_cache_last_access ON bula_cache (last_access_at DESC);
CREATE INDEX idx_cache_access_count ON bula_cache (access_count DESC);
CREATE INDEX idx_cache_rank ON bula_cache (rank) WHERE rank IS NOT NULL;
