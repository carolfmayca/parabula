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


def _normalizar_para_chave(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {
            chave: _normalizar_para_chave(valor[chave])
            for chave in sorted(valor)
        }

    if isinstance(valor, (list, tuple)):
        return [_normalizar_para_chave(item) for item in valor]

    return valor


def _normalizar_medicamentos_para_chave(
    medicamentos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    medicamentos_normalizados = [
        _normalizar_para_chave(medicamento)
        for medicamento in medicamentos
    ]
    return sorted(
        medicamentos_normalizados,
        key=lambda medicamento: json.dumps(
            medicamento,
            ensure_ascii=False,
            sort_keys=True,
        ),
    )


def montar_chave_analise(
    medication_input: list[dict[str, Any]],
    patient_input: dict[str, Any],
) -> str:
    payload_chave = {
        "medication_input": _normalizar_medicamentos_para_chave(medication_input),
        "patient_input": _normalizar_para_chave(patient_input),
    }
    return json.dumps(payload_chave, ensure_ascii=False, sort_keys=True)


def montar_chave_medicamentos(
    medication_input: list[dict[str, Any]],
) -> str:
    return json.dumps(
        _normalizar_medicamentos_para_chave(medication_input),
        ensure_ascii=False,
        sort_keys=True,
    )


def _log_permitido_para_usuario(
    log: dict[str, Any],
    auth_context: dict[str, Any],
) -> bool:
    log_user_id = log.get("user_id")
    log_user_key = log.get("user_key")
    if log_user_id and log_user_id != auth_context.get("user_id"):
        return False
    if log_user_key and log_user_key != auth_context.get("user_key"):
        return False
    return True


def _iterar_logs_analise_validos(auth_context: dict[str, Any]):
    if not LOCAL_ANALYSIS_LOG.exists():
        return

    with LOCAL_ANALYSIS_LOG.open("r", encoding="utf-8") as arquivo:
        for linha in reversed(arquivo.readlines()):
            try:
                log = json.loads(linha)
            except json.JSONDecodeError:
                continue

            if log.get("endpoint") != "/drug-interactions/check":
                continue
            if log.get("status") != "success":
                continue
            if log.get("error_json"):
                continue
            if not _log_permitido_para_usuario(log, auth_context):
                continue

            response_json = log.get("response_json")
            if not isinstance(response_json, dict):
                continue

            yield log, response_json


def buscar_resultado_analise_local(
    *,
    medication_input: list[dict[str, Any]],
    patient_input: dict[str, Any],
    auth_context: dict[str, Any],
) -> dict[str, Any] | None:
    chave_atual = montar_chave_analise(medication_input, patient_input)

    for log, response_json in _iterar_logs_analise_validos(auth_context):
        try:
            chave_log = montar_chave_analise(
                log.get("medication_input") or [],
                log.get("patient_input") or {},
            )
        except TypeError:
            continue

        if chave_log == chave_atual:
            return {
                "log_id": log.get("id"),
                "response_json": response_json,
            }

    return None


def buscar_interacoes_analise_local(
    *,
    medication_input: list[dict[str, Any]],
    auth_context: dict[str, Any],
) -> dict[str, Any] | None:
    chave_atual = montar_chave_medicamentos(medication_input)

    for log, response_json in _iterar_logs_analise_validos(auth_context):
        if "interactions" not in response_json:
            continue

        try:
            chave_log = montar_chave_medicamentos(log.get("medication_input") or [])
        except TypeError:
            continue

        if chave_log == chave_atual:
            return {
                "log_id": log.get("id"),
                "response_json": response_json,
                "interactions": response_json["interactions"],
            }

    return None


def buscar_riscos_analise_local(
    *,
    medication_input: list[dict[str, Any]],
    patient_input: dict[str, Any],
    auth_context: dict[str, Any],
) -> dict[str, Any] | None:
    chave_atual = montar_chave_analise(medication_input, patient_input)

    for log, response_json in _iterar_logs_analise_validos(auth_context):
        if "clinical_risks" not in response_json:
            continue

        try:
            chave_log = montar_chave_analise(
                log.get("medication_input") or [],
                log.get("patient_input") or {},
            )
        except TypeError:
            continue

        if chave_log == chave_atual:
            return {
                "log_id": log.get("id"),
                "response_json": response_json,
                "clinical_risks": response_json["clinical_risks"],
            }

    return None


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
