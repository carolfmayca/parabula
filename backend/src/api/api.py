import logging
import os

from fastapi import FastAPI, HTTPException
from openrouter import OpenRouter

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
logger = logging.getLogger("uvicorn.error")


def normalizar_severidade(valor: str | None) -> str:
    if not valor:
        return "medium"

    valor_normalizado = str(valor).strip().lower()
    if valor_normalizado in {"high", "alta"}:
        return "high"
    if valor_normalizado in {"medium", "media", "média"}:
        return "medium"
    if valor_normalizado in {"low", "baixa"}:
        return "low"
    return "medium"


def ajustar_interacoes_saida(resultado_interacoes: dict) -> dict:
    summary = resultado_interacoes.get("summary", {})
    details = resultado_interacoes.get("details", [])

    if not isinstance(details, list):
        details = []

    interactions_found = bool(summary.get("interactions_found")) and bool(details)
    summary["interactions_found"] = interactions_found
    summary["severity"] = (
        normalizar_severidade(summary.get("severity"))
        if interactions_found
        else "low"
    )

    resultado_interacoes["summary"] = summary
    resultado_interacoes["details"] = details
    return resultado_interacoes


def ajustar_riscos_saida(resultado_riscos: dict) -> dict:
    items = resultado_riscos.get("items", [])

    if not isinstance(items, list):
        items = []

    risks_found = bool(resultado_riscos.get("risks_found")) and bool(items)
    resultado_riscos["risks_found"] = risks_found
    resultado_riscos["severity"] = (
        normalizar_severidade(resultado_riscos.get("severity"))
        if risks_found
        else "low"
    )
    resultado_riscos["items"] = items
    return resultado_riscos


def deduplicar_nomes(nomes: list[str]) -> list[str]:
    nomes_unicos = []
    vistos = set()
    for nome in nomes:
        if nome not in vistos:
            nomes_unicos.append(nome)
            vistos.add(nome)
    return nomes_unicos


def montar_contexto_medicamentos_considerados(
    drogas_requisitadas,
    drugs_considerados: list[str],
) -> str:
    nomes_considerados = {drug.lower() for drug in drugs_considerados}
    linhas = []
    nomes_incluidos = set()

    for drug in drogas_requisitadas:
        if drug.name not in nomes_considerados and drug.name.lower() not in nomes_considerados:
            continue

        linha = f"- {drug.name}"
        if drug.via:
            linha += f" (via: {drug.via})"
        linhas.append(linha)
        nomes_incluidos.add(drug.name.lower())

    for drug in drugs_considerados:
        if drug.lower() not in nomes_incluidos:
            linhas.append(f"- {drug}")

    return "\n".join(linhas)


@app.post("/drug-interactions/check")
def check_interactions(data: DrugRequest):
    logger.info("Rota /drug-interactions/check chamada")

    drugs = data.drugs
    drug_names = [drug.name for drug in drugs]
    num_drugs = len(drugs)
    patient = data.patient

    logger.info("Medicamentos recebidos: %s", drug_names)

    # VALIDAÇÃO 0: Consistência dos dados do paciente
    if patient.is_pregnant and patient.biological_sex == "male":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_PATIENT_DATA",
                "message": (
                    "Pacientes do sexo biológico masculino não podem ser "
                    "marcados como grávidos."
                ),
            },
        )

    perfil_paciente = []

    if patient.age is not None:
        perfil_paciente.append(f"- Idade: {patient.age} anos")

    if patient.biological_sex is not None:
        perfil_paciente.append(f"- Sexo biológico: {patient.biological_sex}")

    if patient.is_pregnant is not None:
        perfil_paciente.append(f"- Grávida: {patient.is_pregnant}")

    if patient.comorbidities:
        perfil_paciente.append(
            f"- Comorbidades: {', '.join(patient.comorbidities)}"
        )

    perfil_paciente_str = "\n".join(perfil_paciente)
    has_patient = bool(perfil_paciente)

    # VALIDAÇÃO 1: Medicamentos duplicados
    if len(drug_names) != len(set(drug_names)):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "DUPLICATE_DRUGS",
                "message": "Medicamentos duplicados não são permitidos.",
            },
        )

    # VALIDAÇÃO 2: pelo menos 1 medicamento deve ser informado
    if num_drugs == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "NO_DRUGS_PROVIDED",
                "message": "Pelo menos um medicamento deve ser informado.",
            },
        )

    # VALIDAÇÃO 3: em caso de 1 medicamento, os dados clínicos devem ser informados
    if num_drugs == 1 and not has_patient:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INSUFFICIENT_INFORMATION",
                "message": (
                    "Não é possível realizar a análise com apenas "
                    "um medicamento sem informações do paciente."
                ),
            },
        )

    try:
        supabase_client = get_client()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SUPABASE_CONNECTION_ERROR",
                "message": f"Falha ao conectar ao Supabase: {exc}",
            },
        )

    resultado_riscos_bulas = montar_bulas_texto(
        drug_names,
        supabase_client,
        ["CONTRAINDICAÇÕES", "ADVERTÊNCIAS E PRECAUÇÕES", "POSOLOGIA E MODO DE USAR"],
        retornar_metadados=True,
    )
    texto_riscos = resultado_riscos_bulas["bulas_texto"]
    ignored_drugs = resultado_riscos_bulas["ignored_drugs"]
    drugs_considerados = deduplicar_nomes(resultado_riscos_bulas["drugs_considerados"])

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

    texto_interacoes = montar_bulas_texto(
        drugs_considerados,
        supabase_client,
        ["INTERAÇÕES MEDICAMENTOSAS", "POSOLOGIA E MODO DE USAR"],
    )

    contexto_medicamentos_str = montar_contexto_medicamentos_considerados(
        drugs,
        drugs_considerados,
    )

    logger.info("Informações de bula montadas")

    client = OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY"))
    num_drugs_considerados = len(drugs_considerados)

    if num_drugs_considerados == 1 and not has_patient:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INSUFFICIENT_AVAILABLE_INFORMATION",
                "message": (
                    "A análise ficou com apenas um medicamento disponível "
                    "e nenhuma informação do paciente."
                ),
                "ignored_drugs": ignored_drugs,
            },
        )

    # Cenario 2: 1 medicamento disponível e dados do paciente
    if num_drugs_considerados == 1 and has_patient:
        resultado_riscos = chamar_modelo(
            client,
            prompt_riscos_clinicos(
                texto_riscos,
                perfil_paciente_str,
                contexto_medicamentos_str,
            ),
        )
        resultado_riscos = ajustar_riscos_saida(resultado_riscos)

        return {
            "success": True,
            "drugs": [drug.model_dump() for drug in drugs],
            "drugs_considered": drugs_considerados,
            "ignored_drugs": ignored_drugs,
            "clinical_risks": {
                "risks_found": resultado_riscos["risks_found"],
                "severity": resultado_riscos["severity"],
                "items": resultado_riscos["items"],
            },
        }

    # Cenario 3: 2 ou + medicamentos disponíveis sem dados do paciente
    if num_drugs_considerados >= 2 and not has_patient:
        resultado_interacoes = chamar_modelo(
            client,
            prompt_interacoes(texto_interacoes, contexto_medicamentos_str),
        )
        resultado_interacoes = ajustar_interacoes_saida(resultado_interacoes)

        return {
            "success": True,
            "drugs": [drug.model_dump() for drug in drugs],
            "drugs_considered": drugs_considerados,
            "ignored_drugs": ignored_drugs,
            "interactions": {
                "summary": resultado_interacoes["summary"],
                "details": resultado_interacoes["details"],
            },
        }

    # Cenario 4: 2 ou + medicamentos disponíveis com dados do paciente
    if num_drugs_considerados >= 2 and has_patient:
        resultado_interacoes = chamar_modelo(
            client,
            prompt_interacoes(texto_interacoes, contexto_medicamentos_str),
        )
        resultado_riscos = chamar_modelo(
            client,
            prompt_riscos_clinicos(
                texto_riscos,
                perfil_paciente_str,
                contexto_medicamentos_str,
            ),
        )
        resultado_interacoes = ajustar_interacoes_saida(resultado_interacoes)
        resultado_riscos = ajustar_riscos_saida(resultado_riscos)

        return {
            "success": True,
            "drugs": [drug.model_dump() for drug in drugs],
            "drugs_considered": drugs_considerados,
            "ignored_drugs": ignored_drugs,
            "interactions": {
                "summary": resultado_interacoes["summary"],
                "details": resultado_interacoes["details"],
            },
            "clinical_risks": {
                "risks_found": resultado_riscos["risks_found"],
                "severity": resultado_riscos["severity"],
                "items": resultado_riscos["items"],
            },
        }
