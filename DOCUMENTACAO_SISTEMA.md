# ParaBula - Documentação do Sistema

## 1. Resumo

O ParaBula é uma solução digital para apoiar a análise de segurança no uso de medicamentos. O sistema recebe uma lista de medicamentos e, quando informado, o perfil clínico do paciente, consultando informações oficiais de bulas brasileiras para retornar alertas sobre interações medicamentosas e riscos clínicos.

A aplicação considera dados como nome do medicamento, via de administração, dose, idade, peso, sexo biológico, gravidez e comorbidades. O objetivo é auxiliar profissionais e usuários na identificação de possíveis riscos, sem substituir a avaliação clínica de um profissional de saúde.

## 2. Arquitetura do Sistema

O sistema foi organizado em dois módulos principais: frontend e backend. O frontend é responsável pela interface web, enquanto o backend concentra as regras de validação, autenticação, busca de bulas, processamento dos dados, chamada ao modelo de linguagem e armazenamento dos logs.

Estrutura geral:

```text
parabula/
├── frontend/                 # Interface web em Express.js e Handlebars
├── backend/                  # API, processamento de bulas, banco e LLM
├── backend/db/               # Scripts SQL e cliente Supabase
├── backend/src/api/          # Endpoints da API
├── backend/src/classes/      # Modelos de entrada e validações
├── backend/src/modelo_llm/   # Prompts e integração com OpenRouter
├── backend/src/processador_texto/
│   └── processador_texto.py  # Montagem dos textos das bulas
└── backend/src/processamento_bulas/
    └── ...                   # Coleta, conversão e carga de bulas
```

Fluxo de comunicação:

1. O usuário acessa a interface web em `http://localhost:3000`.
2. O frontend coleta medicamentos e dados do paciente.
3. O frontend envia uma requisição HTTP para o backend em `POST /drug-interactions/check`.
4. O backend autentica a requisição usando token.
5. O backend valida os dados recebidos.
6. O backend recupera as bulas vigentes dos medicamentos.
7. O backend consulta os logs para reaproveitar resultados já calculados, quando possível.
8. Se não houver resultado válido em log, o backend monta os prompts e chama o modelo via OpenRouter.
9. A resposta é salva em logs locais e no banco.
10. O frontend renderiza a tela de resultados.

## 3. Tecnologias Utilizadas

Frontend:

- Node.js;
- Express.js;
- Express Handlebars;
- HTML, CSS e JavaScript.

Backend:

- Python;
- FastAPI;
- Uvicorn;
- Pydantic;
- Supabase;
- OpenRouter;
- PyPDF2;
- HTTPX;
- Cloudscraper.

Banco de dados e armazenamento:

- PostgreSQL via Supabase;
- tabelas para medicamentos, aliases, bulas, logs de acesso, tokens e logs de análise;
- arquivos locais JSONL para logs em `backend/logs/`.

Serviços externos:

- ANVISA, usada como fonte de bulas;
- OpenRouter, usado para acessar o modelo de linguagem responsável pela análise textual.

## 4. Funcionamento dos Componentes

### Frontend

O frontend está localizado na pasta `frontend/`. Ele fornece as telas do sistema e envia os dados para a API.

Principais partes:

- `app.js`: inicializa o servidor Express e configura Handlebars, arquivos estáticos e rotas.
- `routes/index.js`: define as rotas acessadas pelo usuário.
- `controllers/interactionController.js`: recebe os dados do formulário, normaliza medicamentos, monta o payload e chama o backend.
- `views/interaction.hbs`: tela de entrada dos medicamentos e dados do paciente.
- `views/results.hbs`: tela de exibição do resultado da análise.
- `public/js/interaction.js`: controla a interação do formulário, validação básica e lista de medicamentos no navegador.
- `public/js/results.js`: controla a exibição dos detalhes na página de resultados.
- `public/css/`: contém os estilos visuais da aplicação.

### Backend/API

O backend está localizado em `backend/` e expõe uma API FastAPI.

Principais endpoints:

- `GET /auth/`: emite token de autenticação para um usuário.
- `GET /check-interactions/`: valida se o token enviado está autorizado.
- `POST /drug-interactions/check`: executa a análise de medicamentos e perfil do paciente.
- `GET /logs/`: retorna logs de acesso e de análise do usuário autenticado.

No endpoint principal, o backend:

1. recebe medicamentos e perfil do paciente;
2. valida campos obrigatórios e regras de consistência;
3. impede medicamentos duplicados;
4. valida dose, idade, peso e gravidez;
5. busca as bulas no banco ou na ANVISA;
6. consulta os logs para verificar se a análise já existe;
7. monta o contexto textual das bulas;
8. chama o modelo de linguagem, quando necessário;
9. normaliza a saída;
10. salva os logs;
11. retorna JSON para o frontend.

### Cache por logs

O sistema reaproveita resultados já calculados para evitar reprocessamento desnecessário.

Existem dois reaproveitamentos:

- se a interação medicamentosa já existir no log para os mesmos medicamentos, o backend retorna a parte de `interactions` já salva;
- se os medicamentos junto com o perfil do paciente já existirem no log, o backend retorna a parte de `clinical_risks` já salva.

Esse reaproveitamento também compara as bulas usadas na análise. Assim, mesmo que os medicamentos sejam os mesmos, o sistema só usa o resultado antigo se as bulas recuperadas atualmente forem iguais às bulas registradas no log. Isso evita reutilizar uma resposta baseada em uma versão antiga ou diferente da bula.

Quando a requisição contém medicamentos e perfil do paciente, o sistema pode reaproveitar apenas uma parte do resultado e calcular somente a parte faltante. Por exemplo, se a interação já estiver no log, mas o risco clínico daquele paciente ainda não existir, somente o risco clínico é processado.

### Modelos de dados

Os modelos ficam em `backend/src/classes/data.py` e usam Pydantic para validação.

Principais modelos:

- `Drug`: representa um medicamento, com nome, via e dose.
- `Patient`: representa o perfil do paciente, com idade, peso, sexo biológico, gravidez e comorbidades.
- `DrugRequest`: representa a requisição completa enviada ao backend.

### Processamento de bulas

O processamento de bulas fica em `backend/src/processamento_bulas/`.

Fluxo:

```text
ANVISA -> PDF -> JSON -> Supabase
```

Componentes:

- `coleta/`: baixa bulas profissionais da ANVISA;
- `conversao/`: converte PDFs em JSON por seção;
- `carga/`: carrega os dados processados no Supabase;
- `verificacao.py`: compara a bula vigente no banco com a bula atual;
- `importacao_automatica.py`: importa uma bula sob demanda quando a API recebe um medicamento desconhecido.

### Banco de dados

O banco utiliza Supabase/PostgreSQL. As principais tabelas são:

- `medicamento`: guarda princípios ativos;
- `medicamento_alias`: guarda nomes comerciais, sinônimos e abreviações;
- `bula_medicamento`: guarda o conteúdo das bulas em JSON;
- `bula_atualizacao`: controla verificações e atualizações;
- `api_users`: guarda usuários da API;
- `api_tokens`: guarda hashes dos tokens;
- `api_access_logs`: registra acessos permitidos ou bloqueados;
- `analise_logs`: registra entradas, prompts, respostas e erros das análises;
- `analise_log_bula`: relaciona análises com as bulas usadas.

### Modelo de linguagem

O módulo `backend/src/modelo_llm/` contém:

- `prompts.py`: prompts usados para análise de interações e riscos clínicos;
- `open_router.py`: integração com OpenRouter para chamada ao modelo.

As respostas esperadas do modelo são JSONs estruturados, separados em:

- `interactions`: resumo e detalhes das interações medicamentosas;
- `clinical_risks`: riscos relacionados ao perfil do paciente.

## 5. Como Executar o Sistema

### Backend

Entre na pasta do backend:

```bash
cd backend
```

Crie e ative o ambiente virtual, se ainda não existir:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie o arquivo `backend/.env` com as variáveis:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_supabase
OPENROUTER_API_KEY=sua_chave_openrouter
API_TOKEN_ISSUER_SECRET=um_segredo_para_emitir_tokens
```

Execute a API:

```bash
python -m uvicorn src.api.api:app --reload --host 0.0.0.0 --port 8000
```

A documentação interativa da API fica em:

```text
http://localhost:8000/docs
```

### Frontend

Em outro terminal, entre na pasta do frontend:

```bash
cd frontend
```

Instale as dependências:

```bash
npm install
```

Opcionalmente, crie `frontend/.env`:

```env
BACKEND_URL=http://localhost:8000
API_AUTH_TOKEN=pb_frontend_demo_token
```

Execute o frontend:

```bash
npm start
```

Acesse no navegador:

```text
http://localhost:3000
```

## 6. Considerações Finais

O ParaBula foi desenvolvido com uma arquitetura modular, separando interface, API, processamento de bulas, banco de dados e integração com modelo de linguagem. Essa separação facilita manutenção, evolução e testes de cada parte do sistema.

Como melhoria futura, o sistema pode incluir testes automatizados mais amplos, interface administrativa para visualizar logs, atualização periódica das bulas e mecanismos adicionais de validação clínica das respostas geradas.
