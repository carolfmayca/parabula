import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Header, HTTPException, Request

try:
    from backend.src.api.audit_logs import agora_iso
except ModuleNotFoundError:
    from src.api.audit_logs import agora_iso

TOKEN_PREFIX = "pb_"
MAX_USER_KEY_LENGTH = 80
USER_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,79}$")
LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"
LOCAL_ACCESS_LOG = LOGS_DIR / "access_logs.jsonl"


def gerar_token() -> str:
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def extrair_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    partes = authorization.strip().split(" ", 1)
    if len(partes) != 2 or partes[0].lower() != "bearer":
        return None

    token = partes[1].strip()
    return token or None


def normalizar_usuario(user: str) -> str:
    usuario = user.strip().lower()
    if (
        not usuario
        or len(usuario) > MAX_USER_KEY_LENGTH
        or not USER_KEY_PATTERN.fullmatch(usuario)
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_USER",
                "message": (
                    "Informe um usuário válido, com letras minúsculas, números, "
                    "ponto, hífen ou underline."
                ),
            },
        )
    return usuario


def validar_permissao_emissao_token(admin_secret: str | None) -> None:
    segredo_configurado = os.getenv("API_TOKEN_ISSUER_SECRET")
    if not segredo_configurado:
        return

    if not admin_secret or not hmac.compare_digest(admin_secret, segredo_configurado):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "TOKEN_ISSUER_FORBIDDEN",
                "message": "Não autorizado a emitir tokens da API.",
            },
        )


def salvar_log_acesso_local(payload: dict[str, Any]) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with LOCAL_ACCESS_LOG.open("a", encoding="utf-8") as arquivo:
        json.dump(payload, arquivo, ensure_ascii=False)
        arquivo.write("\n")
    return LOCAL_ACCESS_LOG


def registrar_log_acesso(
    client: Any | None,
    *,
    endpoint: str,
    method: str,
    status: str,
    reason: str | None = None,
    user_id: str | None = None,
    user_key: str | None = None,
    api_token_id: str | None = None,
    request: Request | None = None,
) -> None:
    payload = {
        "id": str(uuid4()),
        "user_id": user_id,
        "user_key": user_key,
        "api_token_id": api_token_id,
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "reason": reason,
        "ip_address": request.client.host if request and request.client else None,
        "user_agent": request.headers.get("user-agent") if request else None,
        "created_at": agora_iso(),
    }

    try:
        salvar_log_acesso_local(payload)
    except Exception:
        pass

    if client is None:
        return

    try:
        client.table("api_access_logs").insert(payload).execute()
    except Exception:
        pass


def obter_ou_criar_usuario(client: Any, user: str) -> dict[str, Any]:
    user_key = normalizar_usuario(user)
    existente = (
        client.table("api_users")
        .select("*")
        .eq("user_key", user_key)
        .execute()
    )

    if existente.data:
        return existente.data[0]

    resultado = (
        client.table("api_users")
        .insert({"id": str(uuid4()), "user_key": user_key})
        .execute()
    )
    return resultado.data[0]


def criar_token_usuario(client: Any, user: str) -> dict[str, Any]:
    usuario = obter_ou_criar_usuario(client, user)
    token = gerar_token()
    token_hash = hash_token(token)
    token_preview = f"{token[:6]}...{token[-4:]}"

    registro = {
        "id": str(uuid4()),
        "user_id": usuario["id"],
        "token_hash": token_hash,
        "token_preview": token_preview,
        "active": True,
    }
    resultado = client.table("api_tokens").insert(registro).execute()
    token_salvo = resultado.data[0] if resultado.data else registro

    return {
        "user": usuario["user_key"],
        "token": token,
        "token_preview": token_preview,
        "token_id": token_salvo["id"],
    }


def buscar_token(client: Any, token: str) -> dict[str, Any] | None:
    resultado = (
        client.table("api_tokens")
        .select("id,user_id,active,api_users(id,user_key)")
        .eq("token_hash", hash_token(token))
        .limit(1)
        .execute()
    )
    return resultado.data[0] if resultado.data else None


def autenticar_requisicao(
    request: Request,
    client: Any,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    token = extrair_bearer_token(authorization)
    endpoint = request.url.path
    method = request.method

    if not token:
        registrar_log_acesso(
            client,
            endpoint=endpoint,
            method=method,
            status="forbidden",
            reason="missing_authorization_token",
            request=request,
        )
        raise HTTPException(
            status_code=401,
            detail={
                "code": "MISSING_AUTHORIZATION_TOKEN",
                "message": "Informe o token no header Authorization: Bearer <token>.",
            },
        )

    registro_token = buscar_token(client, token)
    if not registro_token or not registro_token.get("active", True):
        registrar_log_acesso(
            client,
            endpoint=endpoint,
            method=method,
            status="forbidden",
            reason="invalid_authorization_token",
            request=request,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "INVALID_AUTHORIZATION_TOKEN",
                "message": "Token de autorização inválido ou inativo.",
            },
        )

    usuario = registro_token.get("api_users") or {}
    auth_context = {
        "user_id": registro_token["user_id"],
        "user_key": usuario.get("user_key"),
        "api_token_id": registro_token["id"],
    }

    registrar_log_acesso(
        client,
        endpoint=endpoint,
        method=method,
        status="allowed",
        reason=None,
        user_id=auth_context["user_id"],
        user_key=auth_context["user_key"],
        api_token_id=auth_context["api_token_id"],
        request=request,
    )

    return auth_context
