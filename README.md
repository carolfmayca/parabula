# ParaBula

ParaBula é uma solução digital para apoiar a análise de segurança no uso de medicamentos. O sistema cruza medicamentos prescritos com informações oficiais de bulas brasileiras e com o perfil clínico do paciente, retornando alertas sobre interações medicamentosas e riscos clínicos.

A versão atual considera medicamentos, via de administração, dosagem, idade, sexo biológico, gravidez e comorbidades.

## Estrutura

```text
parabula/
├── backend/                  # API, banco, LLM e processamento de bulas
├── frontend/                 # Interface web
├── data/                     # Bases auxiliares e bulas processadas
│   ├── bulas_pdf/            # PDFs de bulas baixados da ANVISA
│   └── bulas_json/           # Bulas convertidas para JSON
└── docs/                     # Contexto de produto e respostas do professor
```

## Documentação

- [Frontend](frontend/README.md): instalação, execução e uso da interface.
- [API](backend/src/api/README.md): contrato do endpoint e erros comuns.
- [Processamento de bulas](backend/src/processamento_bulas/README.md): pipeline ANVISA -> PDF -> JSON -> Supabase.
- [Contexto do produto](docs/README.md): respostas do professor, público-alvo, dor e modelo de negócio.

## Execução Rápida

Use dois terminais.

Backend:

```bash
cd backend
source .venv/bin/activate
python -m uvicorn src.api.api:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm start
```

Acesse:

```text
http://localhost:3000
```

Swagger da API:

```text
http://localhost:8000/docs
```

## Variáveis de Ambiente

Crie `backend/.env`:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_supabase
OPENROUTER_API_KEY=sua_chave_openrouter
# Opcional em desenvolvimento; recomendado em produção para proteger GET /auth/
API_TOKEN_ISSUER_SECRET=um_segredo_para_emitir_tokens
```

O frontend já usa o token padrão `pb_frontend_demo_token`. Para trocar a URL do
backend ou sobrescrever esse token, crie `frontend/.env`:

```env
BACKEND_URL=http://localhost:8000
API_AUTH_TOKEN=pb_frontend_demo_token
```

Em bancos já existentes, aplique `backend/db/auth_migration.sql` para criar o
hash do token padrão do front.
