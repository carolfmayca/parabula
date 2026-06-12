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

```http
POST /drug-interactions/check
```

## Entrada

```json
{
  "drugs": ["ibuprofeno", "losartana"],
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
| `drugs` | `array[string]` | Sim | mínimo de 2 medicamentos |
| `patient.age` | `int` | Sim | use `0` quando não informado |
| `patient.biological_sex` | `"female"`, `"male"` ou `"other"` | Sim | usado para validar gravidez |
| `patient.is_pregnant` | `boolean` | Sim | só pode ser `true` quando `biological_sex` for `"female"` |
| `patient.comorbidities` | `array[string]` | Sim | use `[]` quando não informado |

## Regras

- `drugs` deve conter pelo menos 2 medicamentos.
- Medicamentos duplicados não são permitidos.
- Medicamentos podem ser enviados por princípio ativo ou nome comercial.
- Se o medicamento não estiver no banco, a API tenta buscar a bula na ANVISA e cadastrá-lo.
- Se não encontrar na ANVISA, o medicamento é desconsiderado e retornado em `ignored_drugs`.
- Se nenhum medicamento puder ser analisado, a API retorna `NO_DRUGS_AVAILABLE`.
- A análise por via de administração ainda será adicionada.

## Saída

```json
{
  "success": true,
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

