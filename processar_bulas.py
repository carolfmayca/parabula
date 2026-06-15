"""
Processador de bulas em PDF para JSON padronizado.

Extrai as seções das bulas em PDF e gera arquivos JSON individuais
e um arquivo agrupado (bulas_agrupadas.json) sem duplicatas.

Uso:
    python processar_bulas.py                    # Processa todos os PDFs
    python processar_bulas.py bula1.pdf bula2.pdf  # Processa PDFs específicos
"""

import re
import json
import sys
from pathlib import Path
from PyPDF2 import PdfReader


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

BULAS_PDF_DIR = Path("bulas_pdf")
BULAS_JSON_DIR = Path("bulas_json")
ARQUIVO_AGRUPADO = BULAS_JSON_DIR / "bulas_agrupadas.json"


def extrair_conteudo_secoes(caminho_pdf: Path) -> dict:
    """Extrai o conteúdo de cada seção numerada do PDF."""
    reader = PdfReader(str(caminho_pdf))

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

    # Remove cabeçalhos repetidos extraídos do PDF
    texto_normalizado = re.sub(
        r'^[^\n]*_VPS_V\d+\s*$',
        '',
        texto_normalizado,
        flags=re.MULTILINE
    )

    texto_normalizado = re.sub(
        r'^[^\n]*_VP_V\d+\s*$',
        '',
        texto_normalizado,
        flags=re.MULTILINE
    )

    # Remove linhas isoladas com número de página
    texto_normalizado = re.sub(
        r'^\s*\d+\s*$',
        '',
        texto_normalizado,
        flags=re.MULTILINE
    )

    texto_normalizado = re.sub(r'\n{3,}', '\n\n', texto_normalizado)

    # Encontrar posições de cada seção no texto
    # Mapeamento oficial ANVISA
    SECOES_NUMERADAS = {
        1: "INDICAÇÕES",
        2: "RESULTADOS DE EFICÁCIA",
        3: "CARACTERÍSTICAS FARMACOLÓGICAS",
        4: "CONTRAINDICAÇÕES",
        5: "ADVERTÊNCIAS E PRECAUÇÕES",
        6: "INTERAÇÕES MEDICAMENTOSAS",
        7: "CUIDADOS DE ARMAZENAMENTO DO MEDICAMENTO",
        8: "POSOLOGIA E MODO DE USAR",
        9: "REAÇÕES ADVERSAS",
        10: "SUPERDOSE",
    }

    # Detecta apenas títulos reais de seção
    PADRAO_SECAO = re.compile(
        r'^\s*(\d{1,2})\.\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ\s]+?)\s*$',
        re.MULTILINE
    )

    posicoes = []

    for match in PADRAO_SECAO.finditer(texto_normalizado):
        numero = int(match.group(1))
        titulo = " ".join(match.group(2).split())

        if numero not in SECOES_NUMERADAS:
            continue

        titulo_esperado = SECOES_NUMERADAS[numero]

        if titulo != titulo_esperado:
            continue

        posicoes.append(
            (
                titulo_esperado,
                match.start(),
                match.end()
            )
        )

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


def nome_bula_do_arquivo(caminho: Path) -> str:
    """Extrai o nome da bula a partir do nome do arquivo PDF."""
    return caminho.stem.replace("bula_profissional_", "")


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
