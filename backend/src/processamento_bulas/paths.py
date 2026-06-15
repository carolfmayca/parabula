from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
BULAS_PDF_DIR = DATA_DIR / "bulas_pdf"
BULAS_JSON_DIR = DATA_DIR / "bulas_json"
BULAS_AGRUPADAS_PATH = BULAS_JSON_DIR / "bulas_agrupadas.json"
RELATORIO_BULAS_PATH = BULAS_PDF_DIR / "relatorio_bulas.json"
