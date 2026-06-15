# ParaBula

ParaBula é uma solução digital para apoiar a análise de segurança no uso de medicamentos. O sistema cruza medicamentos prescritos com informações oficiais de bulas brasileiras e com o perfil clínico do paciente, retornando alertas sobre interações medicamentosas e riscos clínicos.

A versão atual considera medicamentos, idade, sexo biológico, gravidez e comorbidades. A análise por via de administração ainda será adicionada.

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
BACKEND_URL=http://localhost:8000 npm start
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
```

## Boas Práticas de Git

Branches principais:

- `main`: versão estável.
- `develop`: integração das features.

Evite desenvolver diretamente em `main` ou `develop`.

Convenção sugerida:

```text
feature/nome-feature
fix/nome-correcao
hotfix/nome-urgente
refactor/nome-refatoracao
```

Fluxo comum:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/nova-feature
```

Antes de abrir PR:

```bash
git status
git add .
git commit -m "feat: descreve a mudança"
git push -u origin feature/nova-feature
```
