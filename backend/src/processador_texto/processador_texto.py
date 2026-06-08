import json
from pathlib import Path

def get_interacoes(i: str) -> str:
    json_path = Path(__file__).parent.parent.parent / "bulas_json" / f"bula_{i.capitalize()}.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        interacoes = data.get("INTERAÇÕES MEDICAMENTOSAS", "")
        if not interacoes:
            cabecalho = data.get("CABECALHO")   
            #print(cabecalho.find("INTERAÇÕES MEDICAMENTOSAS"), cabecalho.find("7. CUIDADOS"), sep=",")         
            interacoes = cabecalho[cabecalho.find("INTERAÇÕES MEDICAMENTOSAS"):cabecalho.find("7. CUIDADOS")]

    
    return interacoes

def get_advertenciasEprecaucoes (i: str) -> str:
    json_path = Path(__file__).parent.parent.parent / "bulas_json" / f"bula_{i.capitalize()}.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        cabecalho = data.get("CABECALHO")   
        #print(cabecalho.find("INTERAÇÕES MEDICAMENTOSAS"), cabecalho.find("7. CUIDADOS"), sep=",")         
        advertenciasEprecaucoes = cabecalho[cabecalho.find("4. CONTRAINDICAÇÕES"):cabecalho.find("6. INTERAÇÕES MEDICAMENTOSAS")]
    return advertenciasEprecaucoes

import unicodedata
def remover_acentos(texto: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

from fastapi import HTTPException
from typing import List
from backend.db.supabase_client import buscar_medicamento, buscar_bula
def montar_bulas_texto(drugs: List[str], supabase_client) -> str:
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