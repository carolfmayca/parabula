from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from openrouter import OpenRouter
from processador_texto.processador_texto import get_interacoes
import os

app = FastAPI()


class DrugRequest(BaseModel):
    drugs: List[str]


VALID_DRUGS = [ # sem bd
    "cefalexina",
    "dipirona",
    "ibuprofeno",
    "losartana potassica"
]


@app.post("/drug-interactions/check")
def check_interactions(data: DrugRequest):

    drugs = [drug.lower() for drug in data.drugs]

    # erro 1
    if len(drugs) < 2:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_INPUT",
                "message": "Envie ao menos 2 medicamentos."
            }
        )

    # erro 2
    if len(drugs) != len(set(drugs)):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "DUPLICATE_DRUGS",
                "message": "Medicamentos duplicados não são permitidos."
            }
        )

    # erro 3
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

    Responda obrigatoriamente em JSON no formato:

    {{
        "summary": "resumo curto",
        "details": "explicação detalhada"
    }}

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
    # RESPOSTA FINAL
    # =========================

    return {
        "success": True,
        "drugs": drugs,
        "model_response": model_response
    }