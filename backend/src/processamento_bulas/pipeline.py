import argparse
from pathlib import Path

from backend.src.processamento_bulas.paths import BULAS_PDF_DIR


def carregar_lista_medicamentos(caminho: Path) -> list[str]:
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return [linha.strip() for linha in arquivo if linha.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline ANVISA: coleta PDFs, converte para JSON e carrega no banco."
    )
    parser.add_argument(
        "--medicamentos",
        nargs="*",
        default=[],
        help="Nomes dos medicamentos a coletar na ANVISA.",
    )
    parser.add_argument(
        "--arquivo-medicamentos",
        type=Path,
        help="Arquivo .txt com um medicamento por linha para coleta na ANVISA.",
    )
    parser.add_argument(
        "--pular-coleta",
        action="store_true",
        help="Usa os PDFs ja existentes em data/bulas_pdf/.",
    )
    parser.add_argument(
        "--pular-conversao",
        action="store_true",
        help="Usa o JSON agrupado ja existente em data/bulas_json/.",
    )
    parser.add_argument(
        "--pular-carga",
        action="store_true",
        help="Nao envia os dados processados para o banco.",
    )
    args = parser.parse_args()

    medicamentos = list(args.medicamentos)
    if args.arquivo_medicamentos:
        medicamentos.extend(carregar_lista_medicamentos(args.arquivo_medicamentos))

    if not args.pular_coleta:
        if not medicamentos:
            raise SystemExit(
                "Informe --medicamentos/--arquivo-medicamentos ou use --pular-coleta."
            )
        from backend.src.processamento_bulas.coleta.anvisa import (
            processar_lista_medicamentos,
            salvar_relatorio,
        )

        resultados = processar_lista_medicamentos(medicamentos)
        salvar_relatorio(resultados)

    if not args.pular_conversao:
        from backend.src.processamento_bulas.conversao.pdf_to_json import processar_pdfs

        arquivos_pdf = sorted(BULAS_PDF_DIR.glob("*.pdf"))
        if not arquivos_pdf:
            raise SystemExit(f"Nenhum PDF encontrado em {BULAS_PDF_DIR}")
        processar_pdfs(arquivos_pdf)

    if not args.pular_carga:
        from backend.src.processamento_bulas.carga.supabase_loader import carregar_no_banco

        carregar_no_banco()


if __name__ == "__main__":
    main()
