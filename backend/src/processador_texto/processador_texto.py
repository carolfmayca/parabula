import json
import unicodedata
from pathlib import Path
from typing import List


def get_interacoes(i: str) -> str:
    json_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "bulas_json"
        / f"bula_{i.capitalize()}.json"
    )
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        interacoes = data.get("INTERAÇÕES MEDICAMENTOSAS", "")
        if not interacoes:
            cabecalho = data.get("CABECALHO")
            interacoes = cabecalho[
                cabecalho.find("INTERAÇÕES MEDICAMENTOSAS"):cabecalho.find("7. CUIDADOS")
            ]

    return interacoes


def get_advertenciasEprecaucoes(i: str) -> str:
    json_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "bulas_json"
        / f"bula_{i.capitalize()}.json"
    )
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        cabecalho = data.get("CABECALHO")
        advertenciasEprecaucoes = cabecalho[
            cabecalho.find("4. CONTRAINDICAÇÕES"):cabecalho.find("6. INTERAÇÕES MEDICAMENTOSAS")
        ]
    return advertenciasEprecaucoes


def remover_acentos(texto: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


try:
    from backend.db.supabase_client import buscar_medicamento, buscar_bula
    from backend.src.processamento_bulas.importacao_automatica import (
        importar_medicamento_desconhecido,
    )
except ModuleNotFoundError:
    from db.supabase_client import buscar_medicamento, buscar_bula
    from src.processamento_bulas.importacao_automatica import (
        importar_medicamento_desconhecido,
    )


def buscar_ou_importar_medicamento(supabase_client, drug: str):
    medicamentos_encontrados = buscar_medicamento(supabase_client, drug)
    if medicamentos_encontrados:
        return medicamentos_encontrados, None

    drug_busca = remover_acentos(drug)
    if drug_busca != drug:
        medicamentos_encontrados = buscar_medicamento(supabase_client, drug_busca)
        if medicamentos_encontrados:
            return medicamentos_encontrados, None

    try:
        resultado_importacao = importar_medicamento_desconhecido(
            supabase_client,
            drug,
        )
    except Exception as exc:
        return [], {
            "importado": False,
            "motivo": "erro_importacao_anvisa",
            "mensagem": str(exc),
        }

    if resultado_importacao.get("importado"):
        medicamentos_encontrados = buscar_medicamento(supabase_client, drug)

    return medicamentos_encontrados, resultado_importacao


def _conteudo_dos_campos(secoes_bula: dict, campos: List[str] | None) -> str:
    conteudo_bula = ""

    if campos:
        secoes_por_nome_normalizado = {
            remover_acentos(nome).upper(): conteudo
            for nome, conteudo in secoes_bula.items()
        }

        for campo in campos:
            campo_normalizado = remover_acentos(campo).upper()
            secao_conteudo = secoes_por_nome_normalizado.get(
                campo_normalizado,
                "Conteúdo não disponível",
            )
            conteudo_bula += f"{campo}:\n{secao_conteudo}\n"

        return conteudo_bula

    for secao_nome, secao_conteudo in secoes_bula.items():
        secao_normalizada = remover_acentos(secao_nome).lower()
        if (
            (
                "interac" in secao_normalizada
                or "contraind" in secao_normalizada
                or "advert" in secao_normalizada
            )
            and secao_conteudo
        ):
            conteudo_bula += f"{secao_nome}:\n{secao_conteudo}\n"

    if not conteudo_bula:
        conteudo_bula = json.dumps(secoes_bula, ensure_ascii=False, indent=2)

    return conteudo_bula


def montar_bulas_texto(
    drugs: List[str],
    supabase_client,
    campos: List[str] | None = None,
    retornar_metadados: bool = False,
):
    """
    Para cada medicamento, busca no Supabase e monta o bloco de texto das bulas.
    Medicamentos ausentes são buscados automaticamente na ANVISA. Se ainda
    assim não forem encontrados, são ignorados no texto retornado.
    """
    bulas_texto = ""
    drugs_considerados = []
    drogas_ignoradas = []
    importacoes = []

    for drug in drugs:
        medicamentos_encontrados, resultado_importacao = buscar_ou_importar_medicamento(
            supabase_client,
            drug,
        )
        if resultado_importacao:
            importacoes.append({"drug": drug, **resultado_importacao})

        if not medicamentos_encontrados:
            drogas_ignoradas.append({
                "drug": drug,
                "reason": (
                    resultado_importacao.get("motivo")
                    if resultado_importacao
                    else "nao_encontrado_banco"
                ),
            })
            continue

        med_registro = medicamentos_encontrados[0]
        med_id = med_registro["id"]
        nome_oficial = med_registro["principio_ativo"]
        drugs_considerados.append(nome_oficial)

        bula_registro = buscar_bula(supabase_client, med_id)

        if not bula_registro:
            conteudo_bula = "Informações de bula indisponíveis no banco de dados."
        else:
            conteudo_bula = _conteudo_dos_campos(
                bula_registro["conteudo_json"],
                campos,
            )

        bulas_texto += f"""
        Medicamento: {nome_oficial} (Buscado como: {drug})

        Informações da bula:
        {conteudo_bula}

        ------------------------
        """

    if retornar_metadados:
        return {
            "bulas_texto": bulas_texto,
            "drugs_considerados": drugs_considerados,
            "ignored_drugs": drogas_ignoradas,
            "importacoes": importacoes,
        }

    return bulas_texto
