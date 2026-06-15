import json
import os
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

import cloudscraper


HEADERS = {
    "Authorization": "Guest",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://consultas.anvisa.gov.br/",
}

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
PASTA_PDF = DATA_DIR / "bulas_pdf"
PASTA_JSON = DATA_DIR / "bulas_json"
RETRIES = 3
RETRY_DELAY_SECONDS = 5


def criar_scraper():
    return cloudscraper.create_scraper()


def get_com_retry(scraper, url: str, *, headers: dict | None = None, descricao: str = "requisição"):
    for tentativa in range(RETRIES + 1):
        try:
            response = scraper.get(url, headers=headers)
        except Exception as erro:
            response = None
            mensagem_erro = str(erro)
        else:
            mensagem_erro = f"status {response.status_code}"
            if response.ok:
                return response

        if tentativa < RETRIES:
            print(
                f"[RETRY] {descricao} falhou ({mensagem_erro}). "
                f"Tentativa {tentativa + 1}/{RETRIES} em {RETRY_DELAY_SECONDS}s..."
            )
            time.sleep(RETRY_DELAY_SECONDS)

    print(f"[ERRO] {descricao} falhou após {RETRIES} retries ({mensagem_erro})")
    return response


def normalizar_nome(nome: str) -> str:
    nome = str(nome).strip().lower()
    nome = unicodedata.normalize("NFD", nome)
    nome = "".join(c for c in nome if unicodedata.category(c) != "Mn")
    nome = re.sub(r"\s+", " ", nome)
    return nome


def nome_arquivo_seguro(nome: str) -> str:
    nome = normalizar_nome(nome)
    return re.sub(r'[\\/:*?"<>|]+', "", nome)


def pesquisar_por_nome_produto(scraper, nome: str, count: int = 10) -> dict | None:
    nome_url = quote(str(nome))
    url = (
        "https://consultas.anvisa.gov.br/api/consulta/bulario"
        f"?count={count}&filter%5BnomeProduto%5D={nome_url}"
    )
    response = get_com_retry(scraper, url, headers=HEADERS, descricao=f"pesquisa por produto '{nome}'")
    if response and response.ok:
        return response.json()
    status = response.status_code if response else "sem resposta"
    print(f"[ERRO] pesquisa por produto '{nome}': {status}")
    return None


def pesquisar_por_principio_ativo(scraper, principio: str, count: int = 10) -> dict | None:
    principio_url = quote(str(principio))
    url = (
        "https://consultas.anvisa.gov.br/api/consulta/bulario"
        f"?count={count}&filter%5BprincipiAtivo%5D={principio_url}"
    )
    response = get_com_retry(
        scraper,
        url,
        headers=HEADERS,
        descricao=f"pesquisa por princípio '{principio}'",
    )
    if response and response.ok:
        return response.json()
    status = response.status_code if response else "sem resposta"
    print(f"[ERRO] pesquisa por princípio '{principio}': {status}")
    return None


def get_detalhes_medicamento(scraper, num_processo: str) -> dict | None:
    url = f"https://consultas.anvisa.gov.br/api/consulta/medicamento/produtos/{num_processo}"
    response = get_com_retry(
        scraper,
        url,
        headers=HEADERS,
        descricao=f"detalhes do processo '{num_processo}'",
    )
    if response and response.ok:
        return response.json()
    status = response.status_code if response else "sem resposta"
    print(f"[ERRO] detalhes do processo '{num_processo}': {status}")
    return None


def extrair_principios_ativos(detalhes: dict | None) -> list[str]:
    if not detalhes:
        return []

    principio = detalhes.get("principioAtivo") or detalhes.get("nomeGenerico")
    if not principio:
        return []

    partes = [principio]
    if "+" in principio:
        partes.extend(p.strip() for p in principio.split("+"))

    principios = []
    vistos = set()
    for parte in partes:
        parte = parte.strip()
        chave = normalizar_nome(parte)
        if parte and chave not in vistos:
            principios.append(parte)
            vistos.add(chave)
    return principios


def produto_corresponde_a_principio(nome: str, nome_produto: str | None, principios: list[str]) -> bool:
    nomes_principio = {normalizar_nome(principio) for principio in principios}
    nome_normalizado = normalizar_nome(nome)
    produto_normalizado = normalizar_nome(nome_produto or "")

    return nome_normalizado in nomes_principio or produto_normalizado in nomes_principio


def baixar_primeira_bula_profissional(
    scraper,
    resultado: dict | None,
    rotulo_arquivo: str,
    origem: str,
) -> dict | None:
    if not isinstance(resultado, dict) or not resultado.get("content"):
        print(f"[ERRO] {rotulo_arquivo} ({origem}) -> nenhum resultado")
        return None

    PASTA_PDF.mkdir(exist_ok=True)

    for med in resultado["content"]:
        id_bula = med.get("idBulaProfissionalProtegido")
        if not id_bula:
            continue

        nome_produto = med.get("nomeProduto", "N/A")
        empresa = med.get("razaoSocial", "N/A")
        processo = med.get("numProcesso", "N/A")
        filename = PASTA_PDF / f"bula_profissional_{nome_arquivo_seguro(rotulo_arquivo)}.pdf"
        url_pdf = (
            "https://consultas.anvisa.gov.br/api/consulta/medicamentos/arquivo"
            f"/bula/parecer/{id_bula}/?Authorization="
        )

        resp = get_com_retry(scraper, url_pdf, descricao=f"download da bula '{rotulo_arquivo}'")
        if not resp or not resp.ok:
            status = resp.status_code if resp else "sem resposta"
            print(f"[ERRO] {rotulo_arquivo} ({origem}) -> falha ao baixar PDF ({status})")
            return None

        with open(filename, "wb") as f:
            f.write(resp.content)

        print(f"[OK] {rotulo_arquivo} ({origem})")
        print(f"     Produto: {nome_produto}")
        print(f"     Empresa: {empresa}")
        print(f"     Processo: {processo}")
        print(f"     PDF: {filename}")

        return {
            "arquivo": str(filename),
            "produto": nome_produto,
            "empresa": empresa,
            "processo": processo,
            "origem": origem,
        }

    print(f"[ERRO] {rotulo_arquivo} ({origem}) -> sem bula profissional")
    return None


def processar_medicamento_com_principios(scraper, nome: str, pausa: float = 1.0) -> list[dict]:
    resultados = []

    busca_produto = pesquisar_por_nome_produto(scraper, nome)

    primeiro = None
    principios = []
    if isinstance(busca_produto, dict) and busca_produto.get("content"):
        primeiro = busca_produto["content"][0]
        num_processo = primeiro.get("numProcesso")
        if num_processo:
            detalhes = get_detalhes_medicamento(scraper, num_processo)
            principios = extrair_principios_ativos(detalhes)
        else:
            print(f"[AVISO] {nome} -> sem número de processo para buscar princípio ativo")

    if primeiro and produto_corresponde_a_principio(nome, primeiro.get("nomeProduto"), principios):
        rotulo_produto = f"principio_{principios[0] if principios else nome}"
        origem_produto = "princípio ativo"
    else:
        rotulo_produto = f"comercial_{nome}"
        origem_produto = "nome comercial/produto"

    bula_produto = baixar_primeira_bula_profissional(
        scraper,
        busca_produto,
        rotulo_arquivo=rotulo_produto,
        origem=origem_produto,
    )
    if bula_produto:
        resultados.append(bula_produto)

    if not primeiro:
        busca_principio = pesquisar_por_principio_ativo(scraper, nome)
        bula_principio = baixar_primeira_bula_profissional(
            scraper,
            busca_principio,
            rotulo_arquivo=f"principio_{nome}",
            origem="princípio ativo",
        )
        if bula_principio:
            resultados.append(bula_principio)
        return resultados

    if not principios:
        print(f"[AVISO] {nome} -> princípio ativo não encontrado nos detalhes")
        return resultados

    vistos = {normalizar_nome(nome)}
    for principio in principios:
        chave = normalizar_nome(principio)
        if chave in vistos:
            continue
        vistos.add(chave)

        time.sleep(pausa)
        busca_principio = pesquisar_por_principio_ativo(scraper, principio)
        bula_principio = baixar_primeira_bula_profissional(
            scraper,
            busca_principio,
            rotulo_arquivo=f"principio_{principio}",
            origem=f"princípio ativo de {nome}",
        )
        if bula_principio:
            resultados.append(bula_principio)

    return resultados


def processar_lista_medicamentos(medicamentos: list[str], pausa: float = 2.0) -> list[dict]:
    scraper = criar_scraper()
    todos_resultados = []
    vistos = set()

    for nome in medicamentos:
        chave = normalizar_nome(nome)
        if not chave or chave in vistos:
            continue
        vistos.add(chave)

        print(f"\n=== {nome} ===")
        todos_resultados.extend(processar_medicamento_com_principios(scraper, nome, pausa=pausa))
        time.sleep(pausa)

    return todos_resultados


def salvar_relatorio(resultados: list[dict], caminho: str | Path | None = None):
    caminho = Path(caminho) if caminho else PASTA_PDF / "relatorio_bulas.json"
    caminho.parent.mkdir(exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nRelatório salvo em: {caminho}")
