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
    import logging
    logger = logging.getLogger('uvicorn.error')

    logger.info("rota corretamente chamada")
    drugs = data.drugs
    drug_names = [drug.name for drug in drugs]
    contexto_medicamentos_str = data.montar_contexto_medicamentos()
    num_drugs = len(drugs)

    logger.info(f"Medicamentos recebidos: {drug_names}")
    
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
    logger.info("Informações do paciente coletadas")

    # VALIDAÇÃO 1: Medicamentos duplicados
    if len(drug_names) != len(set(drug_names)):
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
    
    logger.info("passou das validações")
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

    texto_riscos = montar_bulas_texto(drug_names, supabase_client, ["CONTRAINDICAÇÕES", "ADVERTÊNCIAS E PRECAUÇÕES", "POSOLOGIA E MODO DE USAR"])
    texto_interacoes = montar_bulas_texto(drug_names, supabase_client, ["INTERAÇÕES MEDICAMENTOSAS","POSOLOGIA E MODO DE USAR"])

    logger.info("pegou as informações de bula")

    client = OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY"))
    
    #cenario 2: 1 medicamento e dados do paciente
    if num_drugs == 1 and has_patient:
        resultado_riscos = chamar_modelo(
            client,
            prompt_riscos_clinicos(
                drug_names,
                texto_riscos,
                perfil_paciente_str,
                contexto_medicamentos_str,
            )
        )

        return {
            "success": True,
            "drugs": [drug.model_dump() for drug in drugs],
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
            prompt_interacoes(texto_interacoes, contexto_medicamentos_str)
        )

        return {
            "success": True,
            "drugs": [drug.model_dump() for drug in drugs],
            "interactions": {
                "summary": resultado_interacoes["summary"],
                "details": resultado_interacoes["details"]
            }
        }
    
    #cenario 4: 2 ou + medicamentos com dados do paciente
    if num_drugs >= 2 and has_patient:
        resultado_interacoes = chamar_modelo(
            client,
            prompt_interacoes(texto_interacoes, contexto_medicamentos_str)
        )
        resultado_riscos = chamar_modelo(
            client,
            prompt_riscos_clinicos(
                drug_names,
                texto_riscos,
                perfil_paciente_str,
                contexto_medicamentos_str,
            )
        )

        return {
            "success": True,
            "drugs": [drug.model_dump() for drug in drugs],
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
