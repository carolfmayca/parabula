"""
Script para executar módulos com importações corretas.
Adiciona src/ ao PYTHONPATH para que os imports funcionem.
"""
import sys
from pathlib import Path

# Adiciona o diretório src/ ao Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Importa e executa o módulo
if __name__ == "__main__":
    from modelo_llm.open_router import *
