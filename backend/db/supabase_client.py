"""
Módulo de conexão e operações com o banco de dados Supabase.

Funções disponíveis:
  - inserir_medicamento: adiciona um medicamento novo
  - inserir_bula: adiciona/atualiza a bula de um medicamento
  - buscar_medicamento: busca medicamento por nome
  - buscar_bula: busca a bula vigente de um medicamento
  - listar_medicamentos: lista todos os medicamentos
  - carregar_bulas_json: carrega o arquivo agrupado e insere tudo no Supabase

Uso:
    python db/supabase_client.py          # carrega todas as bulas do JSON agrupado
    python db/supabase_client.py --listar # lista medicamentos no banco
    python db/supabase_client.py --backfill-atualizacoes
"""

import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import os

from supabase import create_client, Client

# Carregar variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BULAS_AGRUPADAS = Path("data/bulas_json/bulas_agrupadas.json")
RELATORIO_BULAS = Path("data/bulas_pdf/relatorio_bulas.json")
CONSULTAS_PAGINADAS_PERMITIDAS = {
    ("bula_medicamento", "id,medicamento_id,vigente,pdf_path,fonte_url,created_at"),
}


def get_client() -> Client:
    """Cria e retorna o cliente Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL e SUPABASE_KEY devem estar definidos no arquivo .env"
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def escapar_ilike(valor: str) -> str:
    """Escapa curingas de LIKE para entrada de usuário."""
    return (
        valor
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


# ============================================================================
# OPERAÇÕES DE ESCRITA
# ============================================================================


def inserir_medicamento(client: Client, principio_ativo: str) -> dict:
    """Insere um medicamento. Retorna o registro existente se já existir."""
    # Verificar se já existe
    existente = (
        client.table("medicamento")
        .select("*")
        .ilike("principio_ativo", escapar_ilike(principio_ativo))
        .execute()
    )

    if existente.data:
        return {**existente.data[0], "_status": "já existia"}

    # Inserir novo
    resultado = (
        client.table("medicamento")
        .insert({"principio_ativo": principio_ativo})
        .execute()
    )
    return resultado.data[0]


def registrar_atualizacao_bula(
    client: Client,
    medicamento_id: int,
    status_verificacao: str,
    mensagem: str | None = None,
    fonte_url: str | None = None,
    atualizar_ultima_atualizacao: bool | None = None,
) -> dict | None:
    """Registra o resultado da verificação/atualização da bula do medicamento."""
    agora = datetime.now(timezone.utc).isoformat()
    dados = {
        "medicamento_id": medicamento_id,
        "ultima_verificacao_em": agora,
        "status_verificacao": status_verificacao,
        "mensagem_erro": mensagem,
        "fonte_url": fonte_url,
        "updated_at": agora,
    }

    if atualizar_ultima_atualizacao is None:
        atualizar_ultima_atualizacao = status_verificacao == "atualizada"

    if atualizar_ultima_atualizacao:
        dados["ultima_atualizacao_em"] = agora

    resultado = (
        client.table("bula_atualizacao")
        .upsert(dados, on_conflict="medicamento_id")
        .execute()
    )
    return resultado.data[0] if resultado.data else None


def buscar_todos_registros(
    client: Client,
    tabela: str,
    campos: str,
    tamanho_pagina: int = 1000,
):
    """Busca todos os registros de uma tabela paginando a API do Supabase."""
    if (tabela, campos) not in CONSULTAS_PAGINADAS_PERMITIDAS:
        raise ValueError("Consulta paginada não permitida.")
    if tamanho_pagina < 1 or tamanho_pagina > 1000:
        raise ValueError("tamanho_pagina deve estar entre 1 e 1000.")

    todos = []
    inicio = 0

    while True:
        fim = inicio + tamanho_pagina - 1
        resultado = client.table(tabela).select(campos).range(inicio, fim).execute()
        pagina = resultado.data or []
        todos.extend(pagina)

        if len(pagina) < tamanho_pagina:
            return todos

        inicio += tamanho_pagina


def backfill_atualizacoes_bula(client: Client) -> dict:
    """
    Preenche bula_atualizacao para medicamentos que ja possuem bulas historicas.

    Considera historica toda bula com vigente = False. Para esses medicamentos,
    registra status 'atualizada' e informa os IDs das bulas antigas.
    """
    bulas = buscar_todos_registros(
        client,
        "bula_medicamento",
        "id,medicamento_id,vigente,pdf_path,fonte_url,created_at",
    )
    agora = datetime.now(timezone.utc).isoformat()
    por_medicamento = {}

    for bula in bulas:
        por_medicamento.setdefault(bula["medicamento_id"], []).append(bula)

    registros_criados_ou_atualizados = 0
    medicamentos_com_historico = 0

    for medicamento_id, bulas_medicamento in por_medicamento.items():
        antigas = [bula for bula in bulas_medicamento if not bula.get("vigente")]
        if not antigas:
            continue

        medicamentos_com_historico += 1
        vigente = next((bula for bula in bulas_medicamento if bula.get("vigente")), None)
        ids_antigas = ", ".join(str(bula["id"]) for bula in sorted(antigas, key=lambda b: b["id"]))
        fonte = None
        if vigente:
            fonte = vigente.get("fonte_url") or vigente.get("pdf_path")

        dados = {
            "medicamento_id": medicamento_id,
            "ultima_verificacao_em": agora,
            "ultima_atualizacao_em": vigente.get("created_at") if vigente else agora,
            "status_verificacao": "atualizada",
            "mensagem_erro": (
                "Backfill: medicamento possui bula(s) historica(s) "
                f"marcada(s) como nao vigente(s): {ids_antigas}."
            ),
            "fonte_url": fonte,
            "updated_at": agora,
        }

        client.table("bula_atualizacao").upsert(
            dados,
            on_conflict="medicamento_id",
        ).execute()
        registros_criados_ou_atualizados += 1

    return {
        "bulas_lidas": len(bulas),
        "medicamentos_com_historico": medicamentos_com_historico,
        "registros_criados_ou_atualizados": registros_criados_ou_atualizados,
    }


def calcular_hash_conteudo_bula(conteudo_json: dict) -> str:
    """Calcula o hash estável usado para comparar versões de uma bula."""
    return hashlib.sha256(
        json.dumps(conteudo_json, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def inserir_bula(
    client: Client,
    medicamento_id: int,
    conteudo_json: dict,
    pdf_path: str = None,
    fonte_url: str = None,
) -> dict:
    """
    Insere ou atualiza a bula de um medicamento.
    Se o conteúdo for idêntico (mesmo hash), não duplica.
    """
    # Calcular hash do conteúdo
    hash_conteudo = calcular_hash_conteudo_bula(conteudo_json)

    # Verificar se já existe bula com mesmo hash
    existente = (
        client.table("bula_medicamento")
        .select("*")
        .eq("medicamento_id", medicamento_id)
        .eq("hash_conteudo", hash_conteudo)
        .execute()
    )

    if existente.data:
        return {**existente.data[0], "_status": "já existia"}

    # Marcar bulas anteriores como não vigentes
    bulas_vigentes_anteriores = (
        client.table("bula_medicamento")
        .select("id")
        .eq("medicamento_id", medicamento_id)
        .eq("vigente", True)
        .execute()
        .data
        or []
    )

    client.table("bula_medicamento").update({"vigente": False}).eq(
        "medicamento_id", medicamento_id
    ).eq("vigente", True).execute()

    # Inserir nova bula vigente
    dados = {
        "medicamento_id": medicamento_id,
        "conteudo_json": conteudo_json,
        "hash_conteudo": hash_conteudo,
        "vigente": True,
    }
    if pdf_path:
        dados["pdf_path"] = pdf_path
    if fonte_url:
        dados["fonte_url"] = fonte_url

    resultado = client.table("bula_medicamento").insert(dados).execute()
    bula_inserida = resultado.data[0]

    if bulas_vigentes_anteriores:
        ids_anteriores = ", ".join(str(bula["id"]) for bula in bulas_vigentes_anteriores)
        registrar_atualizacao_bula(
            client,
            medicamento_id,
            status_verificacao="atualizada",
            mensagem=(
                "Nova bula vigente inserida. "
                f"Bula(s) anterior(es) marcada(s) como não vigente(s): {ids_anteriores}."
            ),
            fonte_url=fonte_url or pdf_path,
        )

    return {**bula_inserida, "_status": "adicionado"}


def inserir_alias(
    client: Client, medicamento_id: int, alias: str, tipo_alias: str = "comercial"
) -> dict:
    """Insere um alias para um medicamento. Retorna o existente se já existir."""
    existente = (
        client.table("medicamento_alias")
        .select("*")
        .ilike("alias", escapar_ilike(alias))
        .execute()
    )

    if existente.data:
        return existente.data[0]

    resultado = (
        client.table("medicamento_alias")
        .insert(
            {
                "medicamento_id": medicamento_id,
                "alias": alias,
                "tipo_alias": tipo_alias,
            }
        )
        .execute()
    )
    return resultado.data[0]


# ============================================================================
# OPERAÇÕES DE LEITURA
# ============================================================================


def buscar_medicamento(client: Client, nome: str) -> list[dict]:
    """Busca medicamento por nome (princípio ativo ou alias)."""
    nome = nome.strip()
    nome_ilike = escapar_ilike(nome)

    # Buscar por princípio ativo exato
    resultado_exato = (
        client.table("medicamento")
        .select("*")
        .ilike("principio_ativo", nome_ilike)
        .execute()
    )

    if resultado_exato.data:
        return resultado_exato.data

    # Buscar por alias exato
    resultado_alias_exato = (
        client.table("medicamento_alias")
        .select("*, medicamento(*)")
        .ilike("alias", nome_ilike)
        .execute()
    )

    if resultado_alias_exato.data:
        return [item["medicamento"] for item in resultado_alias_exato.data]

    # Buscar por princípio ativo parcial
    resultado = (
        client.table("medicamento")
        .select("*")
        .ilike("principio_ativo", f"%{nome_ilike}%")
        .execute()
    )

    if resultado.data:
        return resultado.data

    # Buscar por alias parcial
    resultado_alias = (
        client.table("medicamento_alias")
        .select("*, medicamento(*)")
        .ilike("alias", f"%{nome_ilike}%")
        .execute()
    )

    if resultado_alias.data:
        return [item["medicamento"] for item in resultado_alias.data]

    return []


def buscar_bula(client: Client, medicamento_id: int) -> dict | None:
    """Retorna a bula vigente de um medicamento."""
    resultado = (
        client.table("bula_medicamento")
        .select("*")
        .eq("medicamento_id", medicamento_id)
        .eq("vigente", True)
        .execute()
    )

    if resultado.data:
        return resultado.data[0]
    return None


def listar_medicamentos(client: Client) -> list[dict]:
    """Lista todos os medicamentos cadastrados."""
    resultado = (
        client.table("medicamento")
        .select("*")
        .order("principio_ativo")
        .execute()
    )
    return resultado.data


# ============================================================================
# CARGA EM MASSA
# ============================================================================


def nome_bula_do_pdf_path(caminho: str) -> str:
    """Extrai a chave da bula a partir do caminho do PDF."""
    return Path(caminho).stem.replace("bula_profissional_", "")


def carregar_mapa_alias_comercial(caminho: Path = RELATORIO_BULAS) -> dict[str, str]:
    """
    Monta mapa nome_comercial -> principio_ativo a partir do relatório de download.

    Exemplo:
      comercial_tazocin -> principio_piperacilina... vira
      {"tazocin": "piperacilina sodica, tazobactam sodico"}
    """
    if not caminho.exists():
        return {}

    with open(caminho, "r", encoding="utf-8") as f:
        relatorio = json.load(f)

    comerciais_por_nome = {}
    mapa_alias = {}

    for item in relatorio:
        arquivo = item.get("arquivo")
        origem = item.get("origem", "")
        if not arquivo:
            continue

        nome_bula = nome_bula_do_pdf_path(arquivo)

        if nome_bula.startswith("comercial_"):
            alias = nome_bula.replace("comercial_", "", 1)
            produto = item.get("produto")
            if produto:
                comerciais_por_nome[produto.strip().lower()] = alias
            comerciais_por_nome[alias.strip().lower()] = alias
            continue

        if not nome_bula.startswith("principio_"):
            continue

        prefixo_origem = "princípio ativo de "
        if not origem.startswith(prefixo_origem):
            continue

        nome_comercial = origem.replace(prefixo_origem, "", 1).strip().lower()
        alias = comerciais_por_nome.get(nome_comercial)
        if not alias:
            continue

        principio = nome_bula.replace("principio_", "", 1)
        mapa_alias[alias] = principio

    return mapa_alias


def resolver_nome_medicamento(nome_bula: str, mapa_alias: dict[str, str]) -> tuple[str, str | None]:
    """
    Resolve a chave da bula para o princípio ativo e, se aplicável, o alias comercial.
    """
    if nome_bula.startswith("comercial_"):
        alias = nome_bula.replace("comercial_", "", 1)
        principio = mapa_alias.get(alias)
        if principio:
            return principio, alias
        return alias, None

    if nome_bula.startswith("principio_"):
        return nome_bula.replace("principio_", "", 1), None

    return nome_bula, None


def carregar_bulas_json(client: Client, caminho: Path = BULAS_AGRUPADAS):
    """Carrega todas as bulas do arquivo agrupado para o Supabase."""
    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}")
        return

    with open(caminho, "r", encoding="utf-8") as f:
        bulas = json.load(f)

    print(f"Carregando {len(bulas)} bulas para o Supabase...\n")
    mapa_alias = carregar_mapa_alias_comercial()
    aliases_inseridos = 0

    for nome, conteudo in bulas.items():
        principio_ativo, alias_comercial = resolver_nome_medicamento(nome, mapa_alias)

        # Inserir/buscar medicamento
        medicamento = inserir_medicamento(client, principio_ativo)
        med_id = medicamento["id"]

        if alias_comercial:
            inserir_alias(client, med_id, alias_comercial, tipo_alias="comercial")
            aliases_inseridos += 1

        # Inserir bula
        pdf_path = f"data/bulas_pdf/bula_profissional_{nome}.pdf"
        bula = inserir_bula(client, med_id, conteudo, pdf_path)

        status = bula.get("_status", "já existia" if bula.get("id") else "adicionado")
        if alias_comercial:
            print(
                f"  ✓ {nome} -> {principio_ativo} (id={med_id}) - "
                f"alias '{alias_comercial}' - bula {status}"
            )
        else:
            print(f"  ✓ {principio_ativo} (id={med_id}) - bula {status}")

    print(f"\nConcluído! {len(bulas)} bulas processadas.")
    print(f"Aliases comerciais inseridos/encontrados: {aliases_inseridos}")


# ============================================================================
# CLI
# ============================================================================


def main():
    client = get_client()

    if "--listar" in sys.argv:
        medicamentos = listar_medicamentos(client)
        if not medicamentos:
            print("Nenhum medicamento cadastrado.")
            return
        print(f"{'='*50}")
        print(f"Medicamentos cadastrados ({len(medicamentos)}):")
        print(f"{'='*50}")
        for med in medicamentos:
            print(f"  [{med['id']}] {med['principio_ativo']}")

    elif "--buscar" in sys.argv:
        idx = sys.argv.index("--buscar")
        if idx + 1 >= len(sys.argv):
            print("Uso: python db/supabase_client.py --buscar <nome>")
            return
        nome = sys.argv[idx + 1]
        medicamentos = buscar_medicamento(client, nome)
        if not medicamentos:
            print(f"Nenhum medicamento encontrado para '{nome}'")
            return
        for med in medicamentos:
            print(f"\n[{med['id']}] {med['principio_ativo']}")
            bula = buscar_bula(client, med["id"])
            if bula:
                secoes = bula["conteudo_json"]
                print(f"  Bula vigente (id={bula['id']}):")
                for secao, conteudo in secoes.items():
                    if conteudo:
                        print(f"    - {secao}: {len(conteudo)} caracteres")
                    else:
                        print(f"    - {secao}: None")

    elif "--backfill-atualizacoes" in sys.argv:
        resumo = backfill_atualizacoes_bula(client)
        print("Backfill de atualizações concluído:")
        print(f"  - Bulas lidas: {resumo['bulas_lidas']}")
        print(
            "  - Medicamentos com histórico: "
            f"{resumo['medicamentos_com_historico']}"
        )
        print(
            "  - Registros criados/atualizados em bula_atualizacao: "
            f"{resumo['registros_criados_ou_atualizados']}"
        )

    else:
        # Padrão: carregar todas as bulas
        carregar_bulas_json(client)


if __name__ == "__main__":
    main()
