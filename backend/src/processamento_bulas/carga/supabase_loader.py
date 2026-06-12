from pathlib import Path

from backend.src.processamento_bulas.paths import BULAS_AGRUPADAS_PATH


def carregar_no_banco(caminho: str | Path = BULAS_AGRUPADAS_PATH):
    """Carrega o JSON agrupado das bulas no Supabase."""
    from backend.db.supabase_client import carregar_bulas_json, get_client

    client = get_client()
    carregar_bulas_json(client, Path(caminho))


def main():
    carregar_no_banco()


if __name__ == "__main__":
    main()
