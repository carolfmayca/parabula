# Como Usar o ParaBula

ParaBula é um analisador de interações medicamentosas que ajuda a identificar possíveis interações entre medicamentos. O projeto é dividido em **Frontend** (interface web) e **Backend** (API).

---

## 📋 Pré-requisitos

### Backend
- **Python 3.12+**
- **pip** (gerenciador de pacotes Python)
- Variáveis de ambiente configuradas (`.env`)

### Frontend
- **Node.js 18+**
- **npm** (gerenciador de pacotes Node.js)

---

## 🚀 Instalação

### 1. Backend

```bash
# Navegar para a pasta do backend
cd backend

# Criar ambiente virtual (primeira vez)
python -m venv .venv

# Ativar o ambiente virtual
# No Linux/Mac:
source .venv/bin/activate

# No Windows:
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

**Configurar variáveis de ambiente:**

Crie um arquivo `.env` na pasta `backend/` com:
```
SUPABASE_URL=sua_url_supabase
SUPABASE_KEY=sua_chave_supabase
OPENROUTER_API_KEY=sua_chave_openrouter
```

### 2. Frontend

```bash
# Navegar para a pasta do frontend
cd frontend

# Instalar dependências (primeira vez)
npm install
```

---

## ▶️ Como Executar

### Terminal 1 - Backend (porta 8000)

```bash
cd backend
source .venv/bin/activate  # Ativar venv
python -m uvicorn src.api.api:app --reload --host 0.0.0.0 --port 8000
```

**Você verá:**
```
Uvicorn running on http://0.0.0.0:8000
```

**Para acessar a documentação da API:**
- Abra o navegador em: `http://localhost:8000/docs`

### Terminal 2 - Frontend (porta 3000)

```bash
cd frontend
BACKEND_URL=http://localhost:8000 npm start
```

**Você verá:**
```
Server is running on http://localhost:3000
```

**Para acessar a aplicação:**
- Abra o navegador em: `http://localhost:3000`

---

## 📱 Como Usar a Interface

### Adicionar Medicamentos

1. Na tela inicial, você verá um campo para adicionar medicamentos
2. Digite o nome do medicamento (ex: "Ibuprofeno")
3. Clique em **"Adicionar"** ou pressione **Enter**
4. O medicamento aparecerá na lista
5. Repita para adicionar mais medicamentos (mínimo 2)

### Dados do Paciente (Opcional)

Você pode preencher:
- **Idade**: numero inteiro
- **Sexo Biológico**: Feminino, Masculino ou Outro
- **Grávida**: Sim ou Não (relevante apenas para mulheres)
- **Comorbidades**: condições de saúde existentes

> ⚠️ **Todos os dados do paciente são opcionais**. A análise funcionará apenas com os medicamentos.

### Analisar Interações

1. Certifique-se de ter **no mínimo 2 medicamentos** adicionados
2. Clique em **"Analisar Interações"**
3. A requisição será enviada para o backend
4. Aguarde o processamento pela IA
5. Os resultados apareçerão na tela mostrando:
   - **Resumo**: se há interações
   - **Severidade**: baixa, média ou alta
   - **Detalhes**: descrição das interações encontradas

---

## 🔌 Fluxo de Funcionamento

```
[Frontend] --HTTP POST--> [Backend/API] --Query--> [Supabase] --Busca--> [LLM (OpenRouter)]
   Usuário                 FastAPI                Database        Medicamentos      Análise de
  Adiciona              Valida Dados        Busca Bulas e     e Interações      Interações
 Medicamentos           e Chama LLM        Informações
```

### Detalhes Técnicos

1. **Frontend** (Express.js + Handlebars):
   - Captura medicamentos e dados do paciente
   - Valida se há pelo menos 2 medicamentos
   - Envia JSON para o backend

2. **Backend** (FastAPI):
   - Recebe a requisição em `/drug-interactions/check`
   - Busca informações dos medicamentos no Supabase
   - Extrai as bulas em texto
   - Monta um prompt para o LLM analisar
   - Chama a API OpenRouter (modelo GPT)
   - Retorna o resultado em JSON

3. **Dados Retornados**:
   ```json
   {
     "success": true,
     "drugs": ["Ibuprofeno", "Dipirona"],
     "summary": {
       "interactions_found": true,
       "severity": "high",
       "description": "descrição curta"
     },
     "details": [
       {
         "drugs": ["Ibuprofeno", "Dipirona"],
         "severity": "high",
         "description": "descrição detalhada"
       }
     ]
   }
   ```

---

## 🐛 Solução de Problemas

### Backend não inicia
- Verifique se Python 3.12+ está instalado: `python --version`
- Verifique se o `.env` está configurado corretamente
- Verifique a conexão com Supabase e OpenRouter

### Frontend não conecta ao backend
- Verifique se o backend está rodando em `http://localhost:8000`
- Confirme que a variável `BACKEND_URL` está configurada: `BACKEND_URL=http://localhost:8000 npm start`
- Abra o console do navegador (F12) para ver erros detalhados

### Medicamento não encontrado
- Os medicamentos devem estar cadastrados no Supabase
- O nome deve corresponder exatamente ao que está no banco
- Verifique a tabela `medicamento` em seu banco de dados

### Erro 404 na requisição
- Confirme que o endpoint `/drug-interactions/check` existe no backend
- Verifique se o backend foi reiniciado após mudanças de código

---

## 📚 Estrutura do Projeto

```
parabula/
├── frontend/
│   ├── public/
│   │   └── css/
│   │       └── style.css          (Estilos do site)
│   ├── views/
│   │   ├── interaction.hbs        (Formulário principal)
│   │   └── results.hbs            (Tela de resultados)
│   ├── controllers/
│   │   └── interactionController.js  (Lógica do frontend)
│   ├── helpers/
│   │   └── handlebars-helpers.js  (Helpers de template)
│   ├── public/js/
│   │   └── interaction.js         (JavaScript client-side)
│   └── app.js                     (Servidor Express)
│
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   └── api.py            (Endpoints FastAPI)
│   │   ├── modelo_llm/
│   │   │   ├── open_router.py    (Integração com OpenRouter)
│   │   │   └── prompts.py        (Prompts para o LLM)
│   │   └── processador_texto/
│   │       └── processador_texto.py  (Processamento de texto)
│   ├── db/
│   │   ├── supabase_client.py    (Cliente Supabase)
│   │   └── schema.sql            (Schema do banco)
│   ├── requirements.txt          (Dependências Python)
│   └── .env                      (Variáveis de ambiente)
│
└── bulas_json/
    └── bulas_agrupadas.json      (Base de dados de bulas)
```

---

## 🔐 Variáveis de Ambiente Necessárias

### `.env` (Backend)

```env
# Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=seu_api_key_supabase

# OpenRouter (para análise com IA)
OPENROUTER_API_KEY=sua_chave_openrouter
```

---

## 💡 Dicas de Desenvolvimento

- Use `--reload` no uvicorn para recarregar automaticamente após mudanças
- Use `npm start` com `--watch` para monitorar mudanças no frontend
- Abra `http://localhost:8000/docs` para testar os endpoints da API interativamente
- Use o F12 no navegador para ver logs e erros do frontend

---

## 📞 Suporte

Para dúvidas sobre o projeto, consulte a documentação da API em `http://localhost:8000/docs` ou verifique os logs nos terminais onde os servidores estão rodando.

---

**Última atualização:** Junho 2026
