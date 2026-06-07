import json
from pathlib import Path

def get_interacoes(i: str) -> str:
    json_path = Path(__file__).parent.parent.parent / "bulas_json" / f"bula_{i.capitalize()}.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        interacoes = data.get("INTERAÇÕES MEDICAMENTOSAS", "")
        if not interacoes:
            cabecalho = data.get("CABECALHO")   
            #print(cabecalho.find("INTERAÇÕES MEDICAMENTOSAS"), cabecalho.find("7. CUIDADOS"), sep=",")         
            interacoes = cabecalho[cabecalho.find("INTERAÇÕES MEDICAMENTOSAS"):cabecalho.find("7. CUIDADOS")]

    
    return interacoes

def get_advertenciasEprecaucoes (i: str) -> str:
    json_path = Path(__file__).parent.parent.parent / "bulas_json" / f"bula_{i.capitalize()}.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        cabecalho = data.get("CABECALHO")   
        #print(cabecalho.find("INTERAÇÕES MEDICAMENTOSAS"), cabecalho.find("7. CUIDADOS"), sep=",")         
        advertenciasEprecaucoes = cabecalho[cabecalho.find("4. CONTRAINDICAÇÕES"):cabecalho.find("6. INTERAÇÕES MEDICAMENTOSAS")]
    return advertenciasEprecaucoes