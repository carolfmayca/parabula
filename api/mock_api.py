from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy import Column, Integer, String

app = FastAPI()

class DrugRequest(BaseModel):
    drugs: List[str]

# mock simples de medicamentos "existentes"
# VALID_DRUGS = [
#     "ibuprofeno",
#     "losartana potássica",
#     "dipirona",
#     "paracetamol",
#     "varfarina"
# ]

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
    found_drugs = db.query(Drug).filter(
        Drug.name.in_(data.drugs)
    ).all()

    found_names = [drug.name for drug in found_drugs]

    for drug in data.drugs:
        if drug not in found_names:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "DRUG_NOT_FOUND",
                    "message": f"Medicamento '{drug}' não encontrado."
                }
            )

    #pegando as bulas
    bulas = []
    for drug in found_drugs:
        bulas.append({
            "name": drug.name,
            "bula": drug.bula
        })

    summary = []
    details = []

    #passa as bulas para o modelo
    #modelo retorna e a gente so adiciona em summary e details

    # resposta mockada
    return {
        "success": True,
        "summary": summary,
        "details": details
    }
