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
"""

import json
import hashlib
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

from supabase import create_client, Client

# Carregar variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BULAS_AGRUPADAS = Path("bulas_json/bulas_agrupadas.json")
RELATORIO_BULAS = Path("bulas_pdf/relatorio_bulas.json")


def get_client() -> Client:
    """Cria e retorna o cliente Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL e SUPABASE_KEY devem estar definidos no arquivo .env"
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================================
# OPERAÇÕES DE ESCRITA
# ============================================================================


def inserir_medicamento(client: Client, principio_ativo: str) -> dict:
    """Insere um medicamento. Retorna o registro existente se já existir."""
    # Verificar se já existe
    existente = (
        client.table("medicamento")
        .select("*")
        .ilike("principio_ativo", principio_ativo)
        .execute()
    )

    if existente.data:
        return existente.data[0]

    # Inserir novo
    resultado = (
        client.table("medicamento")
        .insert({"principio_ativo": principio_ativo})
        .execute()
    )
    return resultado.data[0]


def inserir_bula(
    client: Client, medicamento_id: int, conteudo_json: dict, pdf_path: str = None
) -> dict:
    """
    Insere ou atualiza a bula de um medicamento.
    Se o conteúdo for idêntico (mesmo hash), não duplica.
    """
    # Calcular hash do conteúdo
    hash_conteudo = hashlib.sha256(
        json.dumps(conteudo_json, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    # Verificar se já existe bula com mesmo hash
    existente = (
        client.table("bula_medicamento")
        .select("*")
        .eq("medicamento_id", medicamento_id)
        .eq("hash_conteudo", hash_conteudo)
        .execute()
    )

    if existente.data:
        return existente.data[0]

    # Marcar bulas anteriores como não vigentes
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

    resultado = client.table("bula_medicamento").insert(dados).execute()
    return resultado.data[0]


def inserir_alias(
    client: Client, medicamento_id: int, alias: str, tipo_alias: str = "comercial"
) -> dict:
    """Insere um alias para um medicamento. Retorna o existente se já existir."""
    existente = (
        client.table("medicamento_alias")
        .select("*")
        .ilike("alias", alias)
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
    # Buscar por princípio ativo
    resultado = (
        client.table("medicamento")
        .select("*")
        .ilike("principio_ativo", f"%{nome}%")
        .execute()
    )

    if resultado.data:
        return resultado.data

    # Buscar por alias
    resultado_alias = (
        client.table("medicamento_alias")
        .select("*, medicamento(*)")
        .ilike("alias", f"%{nome}%")
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
        pdf_path = f"bulas_pdf/bula_profissional_{nome}.pdf"
        bula = inserir_bula(client, med_id, conteudo, pdf_path)

        status = "já existia" if bula.get("vigente") else "inserida"
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

    else:
        # Padrão: carregar todas as bulas
        carregar_bulas_json(client)


if __name__ == "__main__":
    main()
