from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from openrouter import OpenRouter
from processador_texto.processador_texto import get_interacoes
import os
import json

app = FastAPI()


class DrugRequest(BaseModel):
    drugs: List[str]


VALID_DRUGS = [
    "cefalexina",
    "ceftriaxona",
    "cefuroxima",
    "ciprofloxacino",
    "claritromicina",
    "cloreto de sódio",
    "dipirona",
    "glifage",
    "ibuprofeno",
    "losartana potassica",
    "nimesulida",
    "puran",
    "sinvastatina",
    "sulfametoxazol"
]


@app.post("/drug-interactions/check")
def check_interactions(data: DrugRequest):

    # padroniza tudo
    drugs = [drug.lower() for drug in data.drugs]

    # =========================
    # ERRO 1
    # =========================

    if len(drugs) < 2:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_INPUT",
                "message": "Envie ao menos 2 medicamentos."
            }
        )

    # =========================
    # ERRO 2
    # =========================

    if len(drugs) != len(set(drugs)):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "DUPLICATE_DRUGS",
                "message": "Medicamentos duplicados não são permitidos."
            }
        )

    # =========================
    # ERRO 3
    # =========================

    for drug in drugs:
        if drug not in VALID_DRUGS:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "DRUG_NOT_FOUND",
                    "message": f"Medicamento '{drug}' não encontrado."
                }
            )

    # =========================
    # PEGANDO BULAS
    # =========================

    bulas_texto = ""

    for drug in drugs:

        interacoes = get_interacoes(drug)

        bulas_texto += f"""
        Medicamento: {drug}

        Interações medicamentosas:
        {interacoes}

        ------------------------
        """

    # =========================
    # PROMPT
    # =========================

    prompt = f"""
    Analise as informações das bulas abaixo.

    Medicamentos:
    {", ".join(drugs)}

    Verifique se existe interação medicamentosa entre eles.

    RESPONDA APENAS EM JSON VÁLIDO.

    Formato obrigatório:

    {{
      "summary": {{
        "interactions_found": true,
        "severity": "high",
        "description": "descrição curta",
      }},
      "details": [
        {{
          "drugs": ["medicamento A", "medicamento B"],
          "severity": "high",
          "description": "descrição detalhada"
        }}
      ]
    }}

    Regras:
    - Não escreva texto fora do JSON
    - Use severity como: low, medium ou high
    - Se não houver interação relevante, ainda retorne o JSON
    - details pode conter múltiplas interações

    Informações:
    {bulas_texto}
    """

    # =========================
    # OPENROUTER
    # =========================

    client = OpenRouter(
        api_key=os.getenv("OPENROUTER_API_KEY")
    )

    response = client.chat.send(
        model="openai/gpt-oss-120b:free",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    model_response = response.choices[0].message.content

    # =========================
    # CONVERTE JSON DO MODELO
    # =========================

    try:
        parsed_response = json.loads(model_response)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INVALID_MODEL_RESPONSE",
                "message": "O modelo retornou uma resposta inválida."
            }
        )

    # =========================
    # RESPOSTA FINAL
    # =========================

    return {
        "success": True,
        "drugs": drugs,
        "summary": parsed_response["summary"],
        "details": parsed_response["details"]
    }