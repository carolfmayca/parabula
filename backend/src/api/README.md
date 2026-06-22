# API

API FastAPI responsável por receber medicamentos e perfil do paciente, buscar bulas no Supabase ou na ANVISA, chamar o modelo via OpenRouter e retornar interações medicamentosas e riscos clínicos.

## Execução

De dentro de `backend/`:

```bash
source .venv/bin/activate
python -m uvicorn src.api.api:app --reload --host 0.0.0.0 --port 8000
```

Da raiz do projeto:

```bash
python -m uvicorn backend.src.api.api:app --reload --host 0.0.0.0 --port 8000
```

Swagger:

```text
http://localhost:8000/docs
```

## Endpoint

### Autenticação

```http
GET /auth/?user=frontend-demo
```

Gera um token para o usuário informado e salva no banco apenas o par
`(usuário, hash do token)`. O token em texto puro aparece só nessa resposta.

Use o token nas demais rotas:

```http
Authorization: Bearer pb_seu_token
```

O frontend de demonstração já usa o token padrão `pb_frontend_demo_token`.
O banco guarda apenas o hash desse token, criado por `backend/db/schema.sql`
ou pela migração `backend/db/auth_migration.sql`.

Para criar tokens adicionais:

```bash
curl "http://localhost:8000/auth/?user=outro-cliente"
```

Em bancos já existentes, aplique antes a migração
`backend/db/auth_migration.sql`. Para bancos novos, `backend/db/schema.sql` já
inclui essas tabelas.

Em produção, defina `API_TOKEN_ISSUER_SECRET` no backend. Quando essa variável
existe, `/auth/` só emite tokens se receber o mesmo valor no header
`X-Admin-Secret`:

```bash
curl -H "X-Admin-Secret: seu_segredo" \
  "http://localhost:8000/auth/?user=frontend-demo"
```

### Guarda de autorização

```http
GET /check-interactions/
```

Valida o token enviado no header `Authorization`. Se o token estiver ausente ou
inválido, a API bloqueia a chamada e registra a tentativa em `api_access_logs`
e em `backend/logs/access_logs.jsonl`.

### Análise de interações

```http
POST /drug-interactions/check
```

Essa rota também exige `Authorization: Bearer <token>`.

### Logs do usuário

```http
GET /logs/
```

Retorna os logs de acesso e os logs de análise do usuário dono do token.

## Entrada

```json
{
  "drugs": [
    {
      "name": "ibuprofeno",
      "via": "oral",
      "dose": "400mg"
    },
    {
      "name": "losartana",
      "via": "oral",
      "dose": "50mg"
    }
  ],
  "patient": {
    "age": 42,
    "biological_sex": "female",
    "is_pregnant": false,
    "comorbidities": ["hipertensão"]
  }
}
```

| Campo | Tipo | Obrigatório | Observação |
| --- | --- | --- | --- |
| `drugs` | `array[string]` ou `array[object]` | Sim | mínimo de 2 medicamentos |
| `drugs[].name` | `string` | Sim quando `drugs` usa objetos | princípio ativo ou nome comercial |
| `drugs[].via` | `string` | Não | via de administração considerada na análise |
| `drugs[].dose` | `string` ou número | Não | dosagem considerada na análise |
| `patient.age` | `int` | Sim | use `0` quando não informado |
| `patient.biological_sex` | `"female"`, `"male"` ou `"other"` | Sim | usado para validar gravidez |
| `patient.is_pregnant` | `boolean` | Sim | só pode ser `true` quando `biological_sex` for `"female"` |
| `patient.comorbidities` | `array[string]` | Sim | use `[]` quando não informado |

## Regras

- `drugs` deve conter pelo menos 2 medicamentos.
- Medicamentos duplicados não são permitidos.
- Medicamentos podem ser enviados por princípio ativo ou nome comercial.
- Via de administração e dosagem são consideradas quando enviadas.
- Se o medicamento não estiver no banco, a API tenta buscar a bula na ANVISA e cadastrá-lo.
- Se não encontrar na ANVISA, o medicamento é desconsiderado e retornado em `ignored_drugs`.
- Se nenhum medicamento puder ser analisado, a API retorna `NO_DRUGS_AVAILABLE`.

## Saída

```json
{
  "success": true,
  "analysis_log_id": "2a2fc2a2-8f0d-4e4a-a76f-7314e28f5e2b",
  "drugs": ["ibuprofeno", "losartana"],
  "ignored_drugs": [
    {
      "drug": "medicamento inexistente",
      "reason": "nao_encontrado_anvisa"
    }
  ],
  "interactions": {
    "summary": {
      "interactions_found": false,
      "severity": "low",
      "description": "Nenhuma interação relevante encontrada."
    },
    "details": []
  },
  "clinical_risks": {
    "risks_found": false,
    "severity": "low",
    "items": []
  }
}
```

## Logs de análise

Cada análise concluída salva um registro em `analise_logs` e retorna o ID no campo
`analysis_log_id`.

O mesmo registro também é salvo localmente em `backend/logs/analise_logs.jsonl`,
com um JSON por linha.

O log guarda:

- medicamentos recebidos, incluindo `name`, `via` e o campo opcional `dose`;
- perfil do paciente;
- medicamentos considerados e ignorados;
- bulas usadas para montar o contexto da resposta;
- prompts chamados (`interacoes_medicamentosas` e/ou `riscos_clinicos`);
- JSON retornado por cada prompt;
- JSON final retornado pela API;
- timestamps de recebimento, prompts e conclusão.

As informações de dose e via ficam no próprio `medication_input`, junto com o
medicamento recebido.

No banco, as bulas usadas também ficam na tabela `analise_log_bula`, ligada por
chave estrangeira a `analise_logs.id` e `bula_medicamento.id`.

Exemplo de registro:

```json
{
  "id": "2a2fc2a2-8f0d-4e4a-a76f-7314e28f5e2b",
  "endpoint": "/drug-interactions/check",
  "status": "success",
  "request_received_at": "2026-06-19T14:20:10.123456+00:00",
  "completed_at": "2026-06-19T14:20:18.456789+00:00",
  "medication_input": [
    {
      "name": "dipirona",
      "via": "intravenosa",
      "dose": "100ml"
    },
    {
      "name": "ibuprofeno",
      "via": "oral",
      "dose": "400mg"
    }
  ],
  "patient_input": {
    "age": 42,
    "biological_sex": "female",
    "is_pregnant": false,
    "comorbidities": ["hipertensão"]
  },
  "drugs_considered": ["dipirona", "ibuprofeno"],
  "ignored_drugs": [],
  "bulas_usadas": [
    {
      "bula_medicamento_id": 123,
      "medicamento_id": 45,
      "principio_ativo": "dipirona",
      "drug_requested": "dipirona"
    },
    {
      "bula_medicamento_id": 456,
      "medicamento_id": 78,
      "principio_ativo": "ibuprofeno",
      "drug_requested": "ibuprofeno"
    }
  ],
  "prompt_calls": [
    {
      "name": "interacoes_medicamentosas",
      "prompt": "...",
      "started_at": "2026-06-19T14:20:12.456789+00:00",
      "ended_at": "2026-06-19T14:20:15.567890+00:00",
      "response_json": {
        "summary": {
          "interactions_found": false,
          "severity": "low",
          "description": "Nenhuma interação relevante encontrada."
        },
        "details": []
      },
      "error": null
    },
    {
      "name": "riscos_clinicos",
      "prompt": "...",
      "started_at": "2026-06-19T14:20:15.678901+00:00",
      "ended_at": "2026-06-19T14:20:18.345678+00:00",
      "response_json": {
        "risks_found": false,
        "severity": "low",
        "items": []
      },
      "error": null
    }
  ],
  "response_json": {
    "success": true,
    "analysis_log_id": "2a2fc2a2-8f0d-4e4a-a76f-7314e28f5e2b",
    "drugs": [
      {
        "name": "dipirona",
        "via": "intravenosa",
        "dose": "100ml"
      },
      {
        "name": "ibuprofeno",
        "via": "oral",
        "dose": "400mg"
      }
    ],
    "drugs_considered": ["dipirona", "ibuprofeno"],
    "ignored_drugs": [],
    "interactions": {
      "summary": {
        "interactions_found": false,
        "severity": "low",
        "description": "Nenhuma interação relevante encontrada."
      },
      "details": []
    },
    "clinical_risks": {
      "risks_found": false,
      "severity": "low",
      "items": []
    }
  },
  "error_json": null
}
```

## Erros Comuns

### `400 INVALID_INPUT`

Menos de dois medicamentos.

### `400 DUPLICATE_DRUGS`

Medicamentos duplicados.

### `400 INVALID_PATIENT_DATA`

`is_pregnant` veio como `true` com `biological_sex` diferente de `"female"`.

### `404 NO_DRUGS_AVAILABLE`

Nenhum medicamento foi encontrado no banco nem na ANVISA.

### `No module named 'backend'`

Se estiver dentro de `backend/`, use:

```bash
python -m uvicorn src.api.api:app --reload --host 0.0.0.0 --port 8000
```
