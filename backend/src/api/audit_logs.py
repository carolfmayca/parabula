import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"
LOCAL_ANALYSIS_LOG = LOGS_DIR / "analise_logs.jsonl"


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def novo_log_id() -> str:
    return str(uuid4())


def registrar_prompt(
    prompt_calls: list[dict[str, Any]],
    *,
    name: str,
    prompt: str,
    started_at: str,
    ended_at: str,
    response_json: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> None:
    prompt_calls.append(
        {
            "name": name,
            "prompt": prompt,
            "started_at": started_at,
            "ended_at": ended_at,
            "response_json": response_json,
            "error": error,
        }
    )


def salvar_log_analise(client: Any, payload: dict[str, Any]) -> dict[str, Any] | None:
    resultado = client.table("analise_logs").insert(payload).execute()
    return resultado.data[0] if resultado.data else None


def salvar_bulas_usadas(
    client: Any,
    log_id: str,
    bulas_usadas: list[dict[str, Any]],
) -> None:
    if not bulas_usadas:
        return

    registros = []
    vistos = set()
    for bula in bulas_usadas:
        bula_id = bula.get("bula_medicamento_id")
        if not bula_id or bula_id in vistos:
            continue

        vistos.add(bula_id)
        registros.append(
            {
                "analise_log_id": log_id,
                "bula_medicamento_id": bula_id,
                "medicamento_id": bula.get("medicamento_id"),
                "principio_ativo": bula.get("principio_ativo"),
                "drug_requested": bula.get("drug_requested"),
            }
        )

    if registros:
        client.table("analise_log_bula").insert(registros).execute()


def salvar_log_analise_local(payload: dict[str, Any]) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with LOCAL_ANALYSIS_LOG.open("a", encoding="utf-8") as arquivo:
        json.dump(payload, arquivo, ensure_ascii=False)
        arquivo.write("\n")
    return LOCAL_ANALYSIS_LOG
