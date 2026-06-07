# Contrato de Entrada - ParaBula

Definir como o frontend enviará os medicamentos para a API de verificação de interações medicamentosas.

---

# Endpoint

```http
POST /drug-interactions/check
```

---

# Entrada esperada

```json
{
  "drugs": [
    "ibuprofeno",
    "losartana"
  ]
}
```

---

# Estrutura

| Campo | Tipo          | Obrigatório | Descrição             |
| ----- | ------------- | ----------- | --------------------- |
| drugs | array[string] | Sim         | Lista de medicamentos |

---

# Regras

- O campo `drugs` é obrigatório
- `drugs` deve ser uma lista (array)
- A lista deve conter no mínimo 2 medicamentos
- Cada medicamento deve ser uma string
- Medicamentos duplicados não são permitidos
- Os medicamentos devem ser enviados usando o princípio ativo
- Os nomes devem estar em lowercase

---

# Exemplo válido

```json
{
  "drugs": [
    "ibuprofeno",
    "losartana",
    "dipirona"
  ]
}
```

---

# Exemplos inválidos

## Lista vazia

```json
{
  "drugs": []
}
```

Motivo:
- mínimo de 2 medicamentos

---

## Tipos inválidos

```json
{
  "drugs": [
    123,
    true
  ]
}
```

Motivo:
- todos os itens devem ser strings

---

## Medicamentos duplicados

```json
{
  "drugs": [
    "ibuprofeno",
    "ibuprofeno"
  ]
}
```

Motivo:
- medicamentos duplicados não são permitidos

---

# Mock da API

Arquivo:

```text
mock_api.py
```

Código:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

class DrugRequest(BaseModel):
    drugs: List[str]

@app.post("/drug-interactions/check")
def check_interactions(data: DrugRequest):
    print(data.model_dump())

    return {
        "status": "request received"
    }
```

---

# Como executar e testar o mock

## 1. Instalar dependências

```bash
pip install fastapi uvicorn
```

---

## 2. Rodar o servidor

No terminal, execute:

```bash
uvicorn mock_api:app --reload
```

---

## 3. Acessar a documentação Swagger

Abra no navegador:

```text
http://127.0.0.1:8000/docs
```

---

## 4. Testar o endpoint

Selecione o endpoint:

```http
POST /drug-interactions/check
```

Clique em:
- “Try it out”
- insira o JSON abaixo:

```json
{
  "drugs": [
    "ibuprofeno",
    "losartana"
  ]
}
```

Depois clique em:
- “Execute”

---

## 5. Resultado esperado no Swagger

A API deve retornar:

```json
{
  "status": "request received"
}
```

Status esperado:

```text
200 OK
```

---

## 6. Resultado esperado no terminal

O terminal onde o servidor foi iniciado deve exibir:

```python
{'drugs': ['ibuprofeno', 'losartana']}
```

Além do log da requisição:

```text
POST /drug-interactions/check HTTP/1.1" 200 OK
```