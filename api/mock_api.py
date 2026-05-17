from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

class DrugRequest(BaseModel):
    drugs: List[str]

# mock simples de medicamentos "existentes"
VALID_DRUGS = [
    "ibuprofeno",
    "losartana",
    "dipirona",
    "paracetamol",
    "varfarina"
]

@app.post("/drug-interactions/check")
def check_interactions(data: DrugRequest):
    print(data.model_dump())

    # erro 1 -> menos de 2 medicamentos
    if len(data.drugs) < 2:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_INPUT",
                "message": "Envie ao menos 2 medicamentos."
            }
        )

    # erro 2 -> medicamentos duplicados
    if len(data.drugs) != len(set(data.drugs)):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "DUPLICATE_DRUGS",
                "message": "Medicamentos duplicados não são permitidos."
            }
        )

    # erro 3 -> medicamento não encontrado
    for drug in data.drugs:

        if drug not in VALID_DRUGS:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "DRUG_NOT_FOUND",
                    "message": f"Medicamento '{drug}' não encontrado."
                }
            )

    interaction = True
    severity = "low"
    description = "Nenhuma interação relevante identificada."

    # resposta mockada
    return {
        "success": True,
        "interactions_found": interaction,
        "total_drugs": len(data.drugs),
        "interaction": {
            "drugs": data.drugs,
            "severity": severity,
            "description": description,
        }
    }