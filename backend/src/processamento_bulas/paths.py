from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BULAS_PDF_DIR = PROJECT_ROOT / "bulas_pdf"
BULAS_JSON_DIR = PROJECT_ROOT / "bulas_json"
BULAS_AGRUPADAS_PATH = BULAS_JSON_DIR / "bulas_agrupadas.json"
RELATORIO_BULAS_PATH = BULAS_PDF_DIR / "relatorio_bulas.json"

