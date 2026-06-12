"""
Processador de bulas em PDF para JSON padronizado.

Extrai as seções das bulas em PDF e gera arquivos JSON individuais
e um arquivo agrupado (bulas_agrupadas.json) sem duplicatas.

Uso:
    python processar_bulas.py                    # Processa todos os PDFs
    python processar_bulas.py bula1.pdf bula2.pdf  # Processa PDFs específicos
"""

from io import BytesIO
import re
import json
import sys
import unicodedata
from pathlib import Path
from PyPDF2 import PdfReader

try:
    from backend.src.processamento_bulas.paths import (
        BULAS_AGRUPADAS_PATH,
        BULAS_JSON_DIR,
        BULAS_PDF_DIR,
    )
except ModuleNotFoundError:
    from src.processamento_bulas.paths import (
        BULAS_AGRUPADAS_PATH,
        BULAS_JSON_DIR,
        BULAS_PDF_DIR,
    )


# Seções padrão esperadas em bulas ANVISA (profissional de saúde)
SECOES_PADRAO = sorted([
    "INDICAÇÕES",
    "RESULTADOS DE EFICÁCIA",
    "CARACTERÍSTICAS FARMACOLÓGICAS",
    "CONTRAINDICAÇÕES",
    "ADVERTÊNCIAS E PRECAUÇÕES",
    "INTERAÇÕES MEDICAMENTOSAS",
    "CUIDADOS DE ARMAZENAMENTO DO MEDICAMENTO",
    "POSOLOGIA E MODO DE USAR",
    "REAÇÕES ADVERSAS",
    "SUPERDOSE",
])

ARQUIVO_AGRUPADO = BULAS_AGRUPADAS_PATH


def extrair_conteudo_secoes(caminho_pdf: Path | str | BytesIO) -> dict:
    """Extrai o conteúdo de cada seção numerada do PDF."""
    reader = PdfReader(caminho_pdf if isinstance(caminho_pdf, BytesIO) else str(caminho_pdf))

    # Extrair texto completo
    texto_completo = ""
    for pagina in reader.pages:
        texto = pagina.extract_text()
        if texto:
            texto_completo += texto + "\n"

    # Normalizar espaços mas manter quebras de linha
    texto_normalizado = re.sub(r'[ \t]+', ' ', texto_completo)
    texto_normalizado = re.sub(r' \n', '\n', texto_normalizado)
    texto_normalizado = re.sub(r'\n{3,}', '\n\n', texto_normalizado)

    # Encontrar posições de cada seção no texto
    posicoes = []
    for secao in SECOES_PADRAO:
        padrao = re.compile(r'(\d+)\.\s*' + re.escape(secao), re.IGNORECASE)
        match = padrao.search(texto_normalizado)
        if match:
            posicoes.append((secao, match.start(), match.end()))

    # Marcadores de fim do conteúdo relevante
    fim_marcadores = [
        re.compile(r'DIZERES\s+LEGAIS', re.IGNORECASE),
        re.compile(r'III\s*[-–—]\s*DIZERES', re.IGNORECASE),
        re.compile(r'Em caso de intoxicação ligue para 0800', re.IGNORECASE),
    ]

    fim_documento = len(texto_normalizado)
    for padrao_fim in fim_marcadores:
        match_fim = padrao_fim.search(texto_normalizado)
        if match_fim and match_fim.start() > 0:
            if match_fim.start() < fim_documento:
                fim_documento = match_fim.start()

    # Ordenar por posição no texto
    posicoes.sort(key=lambda x: x[1])

    # Extrair conteúdo entre seções
    resultado = {}
    for i, (secao, inicio, fim_titulo) in enumerate(posicoes):
        if i + 1 < len(posicoes):
            fim_conteudo = posicoes[i + 1][1]
        else:
            fim_conteudo = fim_documento

        conteudo = texto_normalizado[fim_titulo:fim_conteudo].strip()
        resultado[secao] = conteudo if conteudo else None

    # Preencher seções ausentes com None
    for secao in SECOES_PADRAO:
        if secao not in resultado:
            resultado[secao] = None

    return resultado


def extrair_conteudo_secoes_de_bytes(pdf_bytes: bytes) -> dict:
    """Extrai as seções de uma bula recebida em bytes, sem salvar o PDF em disco."""
    return extrair_conteudo_secoes(BytesIO(pdf_bytes))


def normalizar_nome_medicamento(nome: str) -> str:
    """Padroniza nomes de medicamentos em minúsculo e sem acento."""
    nome_sem_prefixo = re.sub(r"^bula_profissional_", "", nome, flags=re.IGNORECASE)
    nome_minusculo = nome_sem_prefixo.strip().lower()
    nome_decomposto = unicodedata.normalize("NFD", nome_minusculo)
    return "".join(
        caractere
        for caractere in nome_decomposto
        if unicodedata.category(caractere) != "Mn"
    )


def nome_bula_do_arquivo(caminho: Path) -> str:
    """Extrai e padroniza o nome da bula a partir do nome do arquivo PDF."""
    return normalizar_nome_medicamento(caminho.stem)


def carregar_agrupado() -> dict:
    """Carrega o arquivo agrupado existente ou retorna dicionário vazio."""
    if ARQUIVO_AGRUPADO.exists():
        with open(ARQUIVO_AGRUPADO, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def salvar_agrupado(dados: dict):
    """Salva o arquivo agrupado."""
    with open(ARQUIVO_AGRUPADO, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def processar_pdfs(arquivos_pdf: list[Path]):
    """Processa uma lista de PDFs, gera JSONs individuais e atualiza o agrupado."""
    BULAS_JSON_DIR.mkdir(exist_ok=True)

    # Carregar agrupado existente
    agrupado = carregar_agrupado()

    novos = 0
    atualizados = 0

    for arquivo in arquivos_pdf:
        if not arquivo.exists():
            print(f"✗ Arquivo não encontrado: {arquivo}")
            continue

        nome = nome_bula_do_arquivo(arquivo)

        # Extrair conteúdo das seções
        conteudo = extrair_conteudo_secoes(arquivo)

        # Salvar JSON individual
        caminho_json = BULAS_JSON_DIR / f"bula_{nome}.json"
        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(conteudo, f, ensure_ascii=False, indent=2)

        # Atualizar agrupado (sem duplicatas - usa nome como chave)
        if nome in agrupado:
            atualizados += 1
            status = "atualizado"
        else:
            novos += 1
            status = "adicionado"

        agrupado[nome] = conteudo

        campos_presentes = sum(1 for v in conteudo.values() if v is not None)
        campos_none = sum(1 for v in conteudo.values() if v is None)
        print(f"✓ {nome} ({status}): {campos_presentes} campos preenchidos, {campos_none} None")

    # Salvar agrupado
    salvar_agrupado(agrupado)

    print(f"\n{'='*60}")
    print(f"Processamento concluído!")
    print(f"  - Novos: {novos}")
    print(f"  - Atualizados: {atualizados}")
    print(f"  - Total no arquivo agrupado: {len(agrupado)} bulas")
    print(f"  - Arquivo agrupado: {ARQUIVO_AGRUPADO}")
    print(f"  - Campos por bula: {len(SECOES_PADRAO)}")


def main():
    if len(sys.argv) > 1:
        # Processar PDFs específicos passados como argumento
        arquivos = [Path(a) for a in sys.argv[1:]]
    else:
        # Processar todos os PDFs do diretório
        arquivos = sorted(BULAS_PDF_DIR.glob("*.pdf"))

    if not arquivos:
        print(f"Nenhum PDF encontrado em '{BULAS_PDF_DIR}/'")
        sys.exit(1)

    print(f"Processando {len(arquivos)} bula(s)...")
    print(f"Seções padronizadas: {SECOES_PADRAO}\n")

    processar_pdfs(arquivos)


if __name__ == "__main__":
    main()
