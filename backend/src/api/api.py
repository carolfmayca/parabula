import unicodedata
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from openrouter import OpenRouter
from typing import List, Literal
import os
import json

try:
    from backend.db.supabase_client import get_client, buscar_medicamento, buscar_bula
except ModuleNotFoundError:
    from db.supabase_client import get_client, buscar_medicamento, buscar_bula
    
app = FastAPI()

supabase_client = get_client()

def remover_acentos(texto: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

class Patient(BaseModel):
    age: int
    biological_sex: Literal["female", "male", "other"]
    is_pregnant: bool
    comorbidities: List[str]

class DrugRequest(BaseModel):
    drugs: List[str]
    patient: Patient


def chamar_modelo(client: OpenRouter, prompt: str) -> dict:
    """Chama o modelo e já retorna o JSON parseado, lançando HTTPException se falhar."""
    response = client.chat.send(
        model="openai/gpt-oss-120b:free",
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INVALID_MODEL_RESPONSE",
                "message": "O modelo retornou uma resposta inválida."
            }
        )


def montar_bulas_texto(drugs: List[str]) -> str:
    """
    Para cada medicamento, busca no Supabase e monta o bloco de texto das bulas.
    Lança HTTPException se algum medicamento não for encontrado.
    """
    bulas_texto = ""

    for drug in drugs:
        drug_busca = remover_acentos(drug)

        medicamentos_encontrados = buscar_medicamento(supabase_client, drug_busca)

        if not medicamentos_encontrados:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "DRUG_NOT_FOUND",
                    "message": f"Medicamento '{drug}' não encontrado no sistema."
                }
            )

        med_registro = medicamentos_encontrados[0]
        med_id = med_registro["id"]
        nome_oficial = med_registro["principio_ativo"]

        bula_registro = buscar_bula(supabase_client, med_id)

        if not bula_registro:
            conteudo_bula = "Informações de bula indisponíveis no banco de dados."
        else:
            secoes_bula = bula_registro["conteudo_json"]
            conteudo_bula = ""
            for secao_nome, secao_conteudo in secoes_bula.items(): 
                if ( 
                    ( "interac" in secao_nome.lower() or 
                     "contraind" in secao_nome.lower() or 
                     "advert" in secao_nome.lower() ) 
                     and secao_conteudo ): 
                    conteudo_bula += f"{secao_nome}:\n{secao_conteudo}\n"
            if not conteudo_bula:
                conteudo_bula = json.dumps(secoes_bula, ensure_ascii=False, indent=2)

        bulas_texto += f"""
        Medicamento: {nome_oficial} (Buscado como: {drug})

        Informações da bula:
        {conteudo_bula}

        ------------------------
        """

    return bulas_texto


def prompt_interacoes(drugs: List[str], bulas_texto: str) -> str:
    """
    Prompt focado APENAS em interações entre os medicamentos.
    Não recebe dados do paciente — evita que o modelo misture os contextos.
    """
    return f"""
    Você é um sistema especializado em farmacologia clínica.
    Sua tarefa é identificar interações medicamentosas entre os medicamentos listados,
    com base exclusivamente nas informações das bulas fornecidas.

    Medicamentos:
    {", ".join(drugs)}

    RESPONDA APENAS EM JSON VÁLIDO, sem texto fora do JSON.

    Formato obrigatório:
    {{
      "summary": {{
        "interactions_found": true,
        "severity": "high",
        "description": "resumo curto citando explicitamente os medicamentos envolvidos e os principais riscos da interação"
      }},
      "details": [
        {{
          "drugs": ["medicamento A", "medicamento B"],
          "severity": "high",
          "description": "descrição detalhada da interação entre esses medicamentos"
        }}
      ]
    }}

    Regras:
    - Analise APENAS interações entre os medicamentos. Ignore dados do paciente.
    - Não escreva texto fora do JSON.
    - Use severity como: low, medium ou high.
    - Se não houver interação relevante, retorne interactions_found como false e details como lista vazia.
    - O summary.description deve citar explicitamente os medicamentos envolvidos.
    - Baseie-se EXCLUSIVAMENTE nas informações das bulas fornecidas. Se uma interação não estiver descrita nas bulas, não a reporte.

    Informações das bulas:
    {bulas_texto}
"""


def prompt_riscos_clinicos(drugs: List[str], patient: Patient, bulas_texto: str) -> str:
    """
    Prompt focado APENAS nos riscos clínicos do perfil do paciente com cada medicamento.
    Avalia comorbidades, faixa etária e gravidez — sem analisar interações entre medicamentos.
    """
    comorbidades_str = (
        ", ".join(patient.comorbidities) if patient.comorbidities else "Nenhuma"
    )

    return f"""
    Você é um sistema especializado em farmacologia clínica.
    Sua tarefa é avaliar se algum dos medicamentos listados apresenta riscos, contraindicações
    ou alertas específicos para o perfil clínico do paciente abaixo.

    Perfil do paciente:
    - Idade: {patient.age} anos
    - Sexo biológico: {patient.biological_sex}
    - Grávida: {patient.is_pregnant}
    - Comorbidades: {comorbidades_str}

    Medicamentos:
    {", ".join(drugs)}

    Avalie três categorias de risco clínico:
    1. Contraindicações ou cautelas por comorbidade (ex: AINE em paciente hipertenso)
    2. Riscos por faixa etária (ex: sedativos em idosos, doses em crianças)
    3. Contraindicações ou cautelas na gravidez (apenas se is_pregnant for true)

    RESPONDA APENAS EM JSON VÁLIDO, sem texto fora do JSON.

    Formato obrigatório:
    {{
      "risks_found": true,
      "severity": "high",
      "items": [
        {{
          "drug": "nome do medicamento",
          "severity": "high",
          "description": "descrição detalhada do risco para este paciente"
        }}
      ]
    }}

    Regras:
    - Analise APENAS riscos do medicamento com o perfil do paciente. Não analise interações entre medicamentos.
    - Se is_pregnant for false, não avalie riscos de gravidez.
    - Use severity como: low, medium ou high.
    - O severity raiz deve refletir o maior severity encontrado nos items.
    - Se não houver nenhum risco, retorne risks_found como false e items como lista vazia.
    - Não escreva texto fora do JSON.
    - Baseie-se EXCLUSIVAMENTE nas informações das bulas fornecidas. Se um risco não estiver descrito nas bulas, não o reporte.
    - NÃO reporte interações entre medicamentos. Isso é responsabilidade de outro sistema. Reporte APENAS riscos decorrentes do perfil do paciente (comorbidades, idade, gravidez). 
    - Se o único risco identificado for uma interação entre medicamentos, retorne risks_found como false e items como lista vazia.

    Informações das bulas:
    {bulas_texto}
"""


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
    bulas_texto = montar_bulas_texto(drugs)

    client = OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY"))

    # PROMPT 1: interações entre medicamentos
    resultado_interacoes = chamar_modelo(
        client,
        prompt_interacoes(drugs, bulas_texto)
    )

    # PROMPT 2: riscos clínicos do perfil do paciente
    resultado_riscos = chamar_modelo(
        client,
        prompt_riscos_clinicos(drugs, data.patient, bulas_texto)
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