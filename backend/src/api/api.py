from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from openrouter import OpenRouter
from typing import List, Literal
import os
import json

# Importando o cliente e as funções de busca do banco de dados.
try:
    from backend.db.supabase_client import get_client, buscar_medicamento, buscar_bula
except ModuleNotFoundError:
    from db.supabase_client import get_client, buscar_medicamento, buscar_bula

app = FastAPI()

# Inicializa o cliente do Supabase uma única vez na inicialização da API
supabase_client = get_client()

class Patient(BaseModel):
    age: int
    biological_sex: Literal["female", "male", "other"]
    is_pregnant: bool
    comorbidities: List[str]

class DrugRequest(BaseModel):
    drugs: List[str]
    patient: Patient

@app.post("/drug-interactions/check")
def check_interactions(data: DrugRequest):

    # padroniza tudo para minúsculo
    drugs = [drug.lower() for drug in data.drugs]

    # VALIDAÇÃO 0: Consistência dos dados do paciente
    if (
        data.patient.is_pregnant
        and data.patient.biological_sex != "female"
    ):
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

    # BUSCA NO BANCO E MONTAGEM DO TEXTO DAS BULAS
    bulas_texto = ""

    for drug in drugs:
        # Busca o medicamento no Supabase (por princípio ativo ou alias)
        medicamentos_encontrados = buscar_medicamento(supabase_client, drug)

        # Se a lista voltar vazia, o medicamento não existe no banco (Substitui o VALID_DRUGS)
        if not medicamentos_encontrados:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "DRUG_NOT_FOUND",
                    "message": f"Medicamento '{drug}' não encontrado no sistema."
                }
            )
        
        # Pega o primeiro registro correspondente encontrado
        med_registro = medicamentos_encontrados[0]
        med_id = med_registro["id"]
        nome_oficial = med_registro["principio_ativo"]

        # Busca a bula vigente associada ao ID desse medicamento no banco
        bula_registro = buscar_bula(supabase_client, med_id)

        if not bula_registro:
            # Caso o medicamento exista, mas não tenha nenhuma bula cadastrada ainda
            interacoes_texto = "Informações de bula indisponíveis no banco de dados."
        else:
            # Pega o dicionário de seções gravado na coluna JSONB (conteudo_json)
            secoes_bula = bula_registro["conteudo_json"]
            
            # varre o JSON procurando por seções que falem de interações.
            interacoes_texto = ""
            for secao_nome, secao_conteudo in secoes_bula.items():
                if "interac" in secao_nome.lower() and secao_conteudo:
                    interacoes_texto += f"{secao_nome}:\n{secao_conteudo}\n"
            
            # Se a estrutura do JSON não tiver uma chave explícita com o termo "interac",
            # passamos o JSON inteiro e deixamos o LLM analisar tudo (garante resiliência).
            if not interacoes_texto:
                interacoes_texto = json.dumps(secoes_bula, ensure_ascii=False, indent=2)

        # Agrupa os textos das bulas recuperados do Supabase
        bulas_texto += f"""
        Medicamento: {nome_oficial} (Buscado como: {drug})

        Interações medicamentosas:
        {interacoes_texto}

        ------------------------
        """

    # PROMPT PARA O MODELO
    prompt = f"""
    Analise as informações das bulas abaixo.

    Dados do paciente:

    - Idade: {data.patient.age}
    - Sexo biológico: {data.patient.biological_sex}
    - Grávida: {data.patient.is_pregnant}
    - Comorbidades: {", ".join(data.patient.comorbidities) if data.patient.comorbidities else "Nenhuma"}

    Medicamentos:
    {", ".join(drugs)}

    Considere os medicamentos, a idade, o sexo biológico,
    a gravidez e as comorbidades ao avaliar riscos,
    contraindicações e interações medicamentosas.

    Verifique se existe interação medicamentosa entre eles.

    RESPONDA APENAS EM JSON VÁLIDO.

    Formato obrigatório:

    {{
      "summary": {{
        "interactions_found": true,
        "severity": "high",
        "description": "descrição curta"
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

    # CHAMADA DO OPENROUTER
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

    # CONVERTE JSON DO MODELO E RETORNA
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

    return {
        "success": True,
        "drugs": drugs,
        "summary": parsed_response["summary"],
        "details": parsed_response["details"]
    }