-- =============================================================================
-- ParaBula – Schema do banco de dados
-- PostgreSQL 14+
-- =============================================================================

-- Extensão para remover acentos na busca por nome
CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA extensions;

-- Função imutável que envolve unaccent + lower
-- (unaccent não é IMMUTABLE por padrão; o wrapper é necessário para índices)
CREATE OR REPLACE FUNCTION public.normalize_text(TEXT)
    RETURNS TEXT
    LANGUAGE SQL
    IMMUTABLE
    STRICT
AS $$
    SELECT lower(extensions.unaccent($1));
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
    ON medicamento (public.normalize_text(principio_ativo));

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
    ON medicamento_alias (public.normalize_text(alias));

CREATE INDEX idx_alias_medicamento_id
    ON medicamento_alias (medicamento_id);


-- =============================================================================
-- bula_medicamento
-- Conteúdo completo de cada versão de bula.
-- Suporta versionamento: só uma bula vigente por medicamento.
-- =============================================================================
CREATE TABLE bula_medicamento (
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
CREATE UNIQUE INDEX idx_bula_medicamento_vigente
    ON bula_medicamento (medicamento_id)
    WHERE vigente = TRUE;

CREATE INDEX idx_bula_medicamento_medicamento_id
    ON bula_medicamento (medicamento_id);

CREATE INDEX idx_bula_medicamento_hash
    ON bula_medicamento (hash_conteudo)
    WHERE hash_conteudo IS NOT NULL;


CREATE TABLE bula_atualizacao (
    id                      SERIAL PRIMARY KEY,
    medicamento_id          INTEGER NOT NULL UNIQUE REFERENCES medicamento (id) ON DELETE CASCADE,

    ultima_verificacao_em   TIMESTAMPTZ,
    ultima_atualizacao_em   TIMESTAMPTZ,

    status_verificacao      TEXT NOT NULL DEFAULT 'pendente'
        CHECK (status_verificacao IN ('pendente', 'atualizada', 'desatualizada', 'erro')),

    mensagem_erro           TEXT,
    fonte_url               TEXT,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bula_atualizacao_ultima_verificacao
    ON bula_atualizacao (ultima_verificacao_em);

CREATE INDEX idx_bula_atualizacao_status
    ON bula_atualizacao (status_verificacao);
