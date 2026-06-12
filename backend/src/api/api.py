from fastapi import FastAPI, HTTPException
from openrouter import OpenRouter
import os


try:
    from backend.db.supabase_client import get_client
    from backend.src.classes.data import DrugRequest
    from backend.src.modelo_llm.open_router import chamar_modelo
    from backend.src.processador_texto.processador_texto import montar_bulas_texto
    from backend.src.modelo_llm.prompts import prompt_interacoes, prompt_riscos_clinicos
except ModuleNotFoundError:
    from db.supabase_client import get_client
    from src.classes.data import DrugRequest
    from src.modelo_llm.open_router import chamar_modelo
    from src.processador_texto.processador_texto import montar_bulas_texto
    from src.modelo_llm.prompts import prompt_interacoes, prompt_riscos_clinicos

app = FastAPI()

@app.post("/drug-interactions/check")
def check_interactions(data: DrugRequest):

    drugs = [drug.lower() for drug in data.drugs]

    # VALIDAÇÃO 0: Consistência dos dados do paciente
    if data.patient.is_pregnant and data.patient.biological_sex != "female":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_PATIENT_DATA",
                "message": (
                    "Apenas pacientes do sexo biológico feminino "
                    "podem ser marcados como grávidos."
                )
            }
        )

    # VALIDAÇÃO 1: Mínimo de 2 medicamentos
    if len(drugs) < 2:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_INPUT",
                "message": "Envie ao menos 2 medicamentos."
            }
        )

    # VALIDAÇÃO 2: Medicamentos duplicados
    if len(drugs) != len(set(drugs)):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "DUPLICATE_DRUGS",
                "message": "Medicamentos duplicados não são permitidos."
            }
        )

    # BUSCA DAS BULAS (única vez, reutilizado nos dois prompts)
    try:
        supabase_client = get_client()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SUPABASE_CONNECTION_ERROR",
                "message": f"Falha ao conectar ao Supabase: {exc}"
            }
        )

    resultado_bulas = montar_bulas_texto(
        drugs,
        supabase_client,
        retornar_metadados=True,
    )
    bulas_texto = resultado_bulas["bulas_texto"]
    ignored_drugs = resultado_bulas["ignored_drugs"]
    drugs_considerados = []
    vistos = set()
    for drug in resultado_bulas["drugs_considerados"]:
        if drug not in vistos:
            drugs_considerados.append(drug)
            vistos.add(drug)

    if not drugs_considerados:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NO_DRUGS_AVAILABLE",
                "message": (
                    "Nenhum dos medicamentos informados foi encontrado no banco "
                    "ou na ANVISA."
                ),
                "ignored_drugs": ignored_drugs,
            },
        )

    client = OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY"))

    # PROMPT 1: interações entre medicamentos
    resultado_interacoes = chamar_modelo(
        client,
        prompt_interacoes(drugs_considerados, bulas_texto)
    )

    # PROMPT 2: riscos clínicos do perfil do paciente
    resultado_riscos = chamar_modelo(
        client,
        prompt_riscos_clinicos(drugs_considerados, data.patient, bulas_texto)
    )

    return {
        "success": True,
        "drugs": drugs_considerados,
        "ignored_drugs": ignored_drugs,
        "interactions": {
            "summary": resultado_interacoes["summary"],
            "details": resultado_interacoes["details"]
        },
        "clinical_risks": {
            "risks_found": resultado_riscos["risks_found"],
            "severity": resultado_riscos["severity"],
            "items": resultado_riscos["items"]
        }
    }   
