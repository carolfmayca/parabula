import unicodedata
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
    num_drugs = len(drugs)

    patient = data.patient
    perfil_paciente = []

    if patient.age is not None:
        perfil_paciente.append(f"- Idade: {patient.age} anos")

    if patient.biological_sex is not None:
        perfil_paciente.append(
            f"- Sexo biológico: {patient.biological_sex}"
        )

    if patient.is_pregnant is not None:
        perfil_paciente.append(
            f"- Grávida: {patient.is_pregnant}"
        )

    if patient.comorbidities:
        perfil_paciente.append(
            f"- Comorbidades: {', '.join(patient.comorbidities)}"
        )

    perfil_paciente_str = "\n".join(perfil_paciente)
    has_patient = bool(perfil_paciente)

    # VALIDAÇÃO 1: Medicamentos duplicados
    if len(drugs) != len(set(drugs)):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "DUPLICATE_DRUGS",
                "message": "Medicamentos duplicados não são permitidos."
            }
        )
    
    #VALIDAÇÃO 2: pelo menos 1 medicamento deve ser informado
    if num_drugs == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "NO_DRUGS_PROVIDED",
                "message": "Pelo menos um medicamento deve ser informado."
            }
        )
    
    #VALIDAÇÃO 3: em caso de 1 medicamento, os dados clinicos devem ser informados
    #cenario 1: medicamento sem dados do paciente = não processa
    if num_drugs == 1 and not has_patient:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INSUFFICIENT_INFORMATION",
                "message": (
                    "Não é possível realizar a análise com apenas "
                    "um medicamento sem informações do paciente."
                )
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

    bulas_texto = montar_bulas_texto(drugs, supabase_client)

    client = OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY"))
    
    #cenario 2: 1 medicamento e dados do paciente
    if num_drugs == 1 and has_patient:
        resultado_riscos = chamar_modelo(
            client,
            prompt_riscos_clinicos(drugs,data.patient,bulas_texto, perfil_paciente_str)
        )

        return {
            "success": True,
            "drugs": drugs,
            "clinical_risks": {
                "risks_found": resultado_riscos["risks_found"],
                "severity": resultado_riscos["severity"],
                "items": resultado_riscos["items"]
            }
        }
    
    #cenario 3: 2 ou + medicamentos sem dados do paciente
    if num_drugs >= 2 and not has_patient:
        resultado_interacoes = chamar_modelo(
            client,
            prompt_interacoes(drugs, bulas_texto)
        )

        return {
            "success": True,
            "drugs": drugs,
            "interactions": {
                "summary": resultado_interacoes["summary"],
                "details": resultado_interacoes["details"]
            }
        }
    
    #cenario 4: 2 ou + medicamentos com dados do paciente
    if num_drugs >= 2 and has_patient:
        resultado_interacoes = chamar_modelo(
            client,
            prompt_interacoes(drugs, bulas_texto)
        )
        resultado_riscos = chamar_modelo(
            client,
            prompt_riscos_clinicos(drugs,data.patient,bulas_texto, perfil_paciente_str)
        )

        return {
            "success": True,
            "drugs": drugs,
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
