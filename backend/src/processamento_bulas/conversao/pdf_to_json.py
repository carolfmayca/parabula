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


# Mapeamento oficial ANVISA para bulas do profissional de saúde.
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
SECOES_IGNORADAS = {"CUIDADOS DE ARMAZENAMENTO DO MEDICAMENTO"}
SECOES_PADRAO = [
    secao
    for secao in SECOES_NUMERADAS.values()
    if secao not in SECOES_IGNORADAS
]
ALIASES_SECOES = {
    "INDICAÇÃO": "INDICAÇÕES",
    "RESULTADO DA EFICÁCIA": "RESULTADOS DE EFICÁCIA",
    "RESULTADO DE EFICÁCIA": "RESULTADOS DE EFICÁCIA",
    "RESULTADOS DA EFICÁCIA": "RESULTADOS DE EFICÁCIA",
    "CUIDADOS DE ARMAZENAMENTO": "CUIDADOS DE ARMAZENAMENTO DO MEDICAMENTO",
    "CUIDADOS DE ARMAZENAGEM DO MEDICAMENTO": "CUIDADOS DE ARMAZENAMENTO DO MEDICAMENTO",
    "CUIDADOS DE ARMAZENAGEM": "CUIDADOS DE ARMAZENAMENTO DO MEDICAMENTO",
    "SUPERDOSAGEM": "SUPERDOSE",
}

ARQUIVO_AGRUPADO = BULAS_AGRUPADAS_PATH


def normalizar_titulo_secao(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.strip().rstrip(":").strip())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto)
    return texto.upper().strip()


def chave_titulo_secao(texto: str) -> str:
    return re.sub(r"[^A-Z]", "", normalizar_titulo_secao(texto))


def titulo_candidato_valido(texto: str) -> bool:
    texto = texto.strip().rstrip(":").strip()
    return bool(texto) and bool(re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿÇç\s]+", texto))


def quebrar_titulos_inline(texto: str) -> str:
    titulos = [
        r"INDICAÇÕES",
        r"RESULTADOS\s+DE\s+EFICÁCIA",
        r"CARACTERÍSTICAS\s+FARMACOLÓGICAS",
        r"CONTRA\s*INDICAÇÕES",
        r"ADVERTÊNCIAS\s+E\s+PRECAUÇÕES",
        r"INTERAÇÕES\s+MEDICAMENTOSAS",
        r"CUIDADOS\s+DE\s+ARMAZENA(?:MENTO|GEM)(?:\s+DO\s+MEDICAMENTO)?",
        r"POSOLOGIA\s+E\s+MODO\s+DE\s+USAR",
        r"REAÇÕES\s+ADVERSAS",
        r"SUPERDOS(?:E|AGEM)",
    ]
    padrao = re.compile(
        r"(?<!\n)\s+(\d{1,2})[.)-]\s*(" + "|".join(titulos) + r")\s*:?\s+"
    )
    return padrao.sub(lambda match: f"\n{match.group(1)}. {match.group(2)}\n", texto)


def linhas_com_offsets(texto: str) -> list[tuple[str, int, int]]:
    linhas = []
    offset = 0
    for linha in texto.splitlines(keepends=True):
        conteudo = linha.rstrip("\n")
        linhas.append((conteudo, offset, offset + len(conteudo)))
        offset += len(linha)
    return linhas


def encontrar_posicoes_secoes(texto: str, fim_documento: int) -> list[tuple[str, int, int]]:
    linhas = linhas_com_offsets(texto)
    posicoes = []
    titulos_por_chave = {
        chave_titulo_secao(titulo): titulo
        for titulo in SECOES_NUMERADAS.values()
    }
    titulos_por_chave.update(
        {
            chave_titulo_secao(alias): secao
            for alias, secao in ALIASES_SECOES.items()
        }
    )

    for i, (linha, inicio_linha, fim_linha) in enumerate(linhas):
        if inicio_linha >= fim_documento:
            break

        if re.fullmatch(r"\s*SUPERDOS(?:E|AGEM)\s*:?\s*", linha, flags=re.IGNORECASE):
            posicoes.append(("SUPERDOSE", inicio_linha, fim_linha))
            continue

        match = re.match(r"^\s*(\d{1,2})[.)-]\s*(.+?)\s*$", linha)
        inicio_titulo = inicio_linha
        fim_titulo_base = fim_linha
        if not match:
            numero_quebrado = re.match(r"^\s*(\d{1,2})\s*$", linha)
            proxima_linha = linhas[i + 1][0].strip() if i + 1 < len(linhas) else ""
            titulo_quebrado = re.match(r"^[.)-]\s*(.+?)\s*$", proxima_linha)
            if not numero_quebrado or not titulo_quebrado:
                continue
            match = numero_quebrado
            fim_titulo_base = linhas[i + 1][2]

        numero = int(match.group(1))
        numero_superdose_incompleto = numero == 0
        if numero not in SECOES_NUMERADAS and not numero_superdose_incompleto:
            continue

        if len(match.groups()) > 1:
            partes = [match.group(2).strip()]
            indice_inicio_complemento = i
        else:
            partes = [titulo_quebrado.group(1).strip()]
            indice_inicio_complemento = i + 1

        for j in range(indice_inicio_complemento, min(indice_inicio_complemento + 3, len(linhas))):
            if j > indice_inicio_complemento:
                proxima_linha = linhas[j][0].strip()
                if re.match(r"^\d{1,2}[.)-]", proxima_linha):
                    break
                partes.append(proxima_linha)

            candidato = " ".join(partes).strip()
            if not titulo_candidato_valido(candidato):
                continue

            secao = titulos_por_chave.get(chave_titulo_secao(candidato))
            if numero_superdose_incompleto and secao != "SUPERDOSE":
                continue
            if secao:
                posicoes.append((secao, inicio_titulo, max(fim_titulo_base, linhas[j][2])))
                break

    posicoes.sort(key=lambda x: x[1])
    return posicoes


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
    texto_normalizado = quebrar_titulos_inline(texto_normalizado)

    # Marcadores de fim do conteúdo relevante
    fim_marcadores = [
        re.compile(r'DIZERES\s+LEGAIS', re.IGNORECASE),
        re.compile(r'D\s*\n\s*I\s*ZERES\s+LEGAIS', re.IGNORECASE),
        re.compile(r'III\s*[-–—]\s*DIZERES', re.IGNORECASE),
        re.compile(r'Em caso de intoxicação ligue para 0800', re.IGNORECASE),
    ]

    fim_documento = len(texto_normalizado)
    for padrao_fim in fim_marcadores:
        match_fim = padrao_fim.search(texto_normalizado)
        if match_fim and match_fim.start() > 0:
            if match_fim.start() < fim_documento:
                fim_documento = match_fim.start()

    posicoes = encontrar_posicoes_secoes(texto_normalizado, fim_documento)

    # Extrair conteúdo entre seções
    resultado = {}
    for i, (secao, inicio, fim_titulo) in enumerate(posicoes):
        if i + 1 < len(posicoes):
            fim_conteudo = posicoes[i + 1][1]
        else:
            fim_conteudo = fim_documento

        if secao not in SECOES_IGNORADAS and secao not in resultado:
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
