import argparse
import json
import time
from typing import Any


try:
    from backend.db.supabase_client import (
        buscar_bula,
        buscar_medicamento,
        calcular_hash_conteudo_bula,
        get_client,
        inserir_bula,
        listar_medicamentos,
        registrar_atualizacao_bula,
    )
except ModuleNotFoundError as exc:
    if exc.name not in {"backend", "backend.db"}:
        raise
    from db.supabase_client import (
        buscar_bula,
        buscar_medicamento,
        calcular_hash_conteudo_bula,
        get_client,
        inserir_bula,
        listar_medicamentos,
        registrar_atualizacao_bula,
    )


def importar_coleta_anvisa():
    try:
        from backend.src.processamento_bulas.coleta.anvisa import (
            criar_scraper,
            get_com_retry,
            pesquisar_por_nome_produto,
            pesquisar_por_principio_ativo,
        )
    except ModuleNotFoundError as exc:
        if exc.name not in {"backend", "backend.src"}:
            raise
        from src.processamento_bulas.coleta.anvisa import (
            criar_scraper,
            get_com_retry,
            pesquisar_por_nome_produto,
            pesquisar_por_principio_ativo,
        )

    return (
        criar_scraper,
        get_com_retry,
        pesquisar_por_nome_produto,
        pesquisar_por_principio_ativo,
    )


def importar_conversor_pdf():
    try:
        from backend.src.processamento_bulas.conversao.pdf_to_json import (
            extrair_conteudo_secoes_de_bytes,
        )
    except ModuleNotFoundError as exc:
        if exc.name not in {"backend", "backend.src"}:
            raise
        from src.processamento_bulas.conversao.pdf_to_json import (
            extrair_conteudo_secoes_de_bytes,
        )

    return extrair_conteudo_secoes_de_bytes


def montar_url_bula_profissional(id_bula: str) -> str:
    return (
        "https://consultas.anvisa.gov.br/api/consulta/medicamentos/arquivo"
        f"/bula/parecer/{id_bula}/?Authorization="
    )


def selecionar_primeira_bula_profissional(resultado: dict | None) -> dict | None:
    if not isinstance(resultado, dict):
        return None

    for medicamento in resultado.get("content", []):
        id_bula = medicamento.get("idBulaProfissionalProtegido")
        if id_bula:
            return medicamento

    return None


def baixar_bula_profissional_atual(nome: str) -> dict[str, Any] | None:
    """
    Busca na ANVISA a primeira bula profissional disponível para o nome informado.

    A busca tenta primeiro por princípio ativo, pois é como os medicamentos são
    armazenados no banco. Se não encontrar, tenta por nome do produto.
    """
    (
        criar_scraper,
        get_com_retry,
        pesquisar_por_nome_produto,
        pesquisar_por_principio_ativo,
    ) = importar_coleta_anvisa()
    scraper = criar_scraper()

    origem = "principio_ativo"
    resultado = pesquisar_por_principio_ativo(scraper, nome)
    medicamento = selecionar_primeira_bula_profissional(resultado)

    if not medicamento:
        origem = "nome_produto"
        resultado = pesquisar_por_nome_produto(scraper, nome)
        medicamento = selecionar_primeira_bula_profissional(resultado)

    if not medicamento:
        return None

    id_bula = medicamento["idBulaProfissionalProtegido"]
    fonte_url = montar_url_bula_profissional(id_bula)
    response = get_com_retry(
        scraper,
        fonte_url,
        descricao=f"download da bula atual '{nome}'",
    )

    if not response or not response.ok:
        return None

    return {
        "pdf_bytes": response.content,
        "fonte_url": fonte_url,
        "id_bula": id_bula,
        "origem_busca": origem,
        "produto": medicamento.get("nomeProduto"),
        "empresa": medicamento.get("razaoSocial"),
        "processo": medicamento.get("numProcesso"),
    }


def verificar_bula_mais_recente(client, nome_medicamento: str) -> dict[str, Any]:
    """
    Compara a bula vigente no banco com a bula profissional atual da ANVISA.

    Retorna status 'atualizada' quando o hash do JSON extraído da ANVISA é igual
    ao hash salvo no banco. Retorna 'desatualizada' quando os hashes diferem.
    """
    medicamentos = buscar_medicamento(client, nome_medicamento)
    if not medicamentos:
        return {
            "success": False,
            "status_verificacao": "erro",
            "mais_recente": None,
            "mensagem": f"Medicamento '{nome_medicamento}' não encontrado no banco.",
        }

    medicamento = medicamentos[0]
    bula_banco = buscar_bula(client, medicamento["id"])
    if not bula_banco:
        registrar_atualizacao_bula(
            client,
            medicamento["id"],
            "erro",
            mensagem="Medicamento encontrado, mas sem bula vigente no banco.",
        )
        return {
            "success": False,
            "medicamento": medicamento,
            "status_verificacao": "erro",
            "mais_recente": None,
            "mensagem": "Medicamento encontrado, mas sem bula vigente no banco.",
        }

    bula_anvisa = baixar_bula_profissional_atual(medicamento["principio_ativo"])
    if not bula_anvisa:
        registrar_atualizacao_bula(
            client,
            medicamento["id"],
            "erro",
            mensagem="Não foi possível obter a bula profissional atual na ANVISA.",
        )
        return {
            "success": False,
            "medicamento": medicamento,
            "bula_banco": {
                "id": bula_banco["id"],
                "hash_conteudo": bula_banco.get("hash_conteudo"),
                "created_at": bula_banco.get("created_at"),
            },
            "status_verificacao": "erro",
            "mais_recente": None,
            "mensagem": "Não foi possível obter a bula profissional atual na ANVISA.",
        }

    extrair_conteudo_secoes_de_bytes = importar_conversor_pdf()
    conteudo_anvisa = extrair_conteudo_secoes_de_bytes(bula_anvisa["pdf_bytes"])
    hash_anvisa = calcular_hash_conteudo_bula(conteudo_anvisa)
    hash_banco = bula_banco.get("hash_conteudo")
    mais_recente = hash_banco == hash_anvisa
    status = "atualizada" if mais_recente else "desatualizada"
    mensagem = (
        "A bula vigente no banco corresponde à bula atual da ANVISA."
        if mais_recente
        else "A bula vigente no banco é diferente da bula atual encontrada na ANVISA."
    )

    registrar_atualizacao_bula(
        client,
        medicamento["id"],
        status,
        mensagem=mensagem,
        fonte_url=bula_anvisa["fonte_url"],
        atualizar_ultima_atualizacao=False,
    )

    return {
        "success": True,
        "medicamento": {
            "id": medicamento["id"],
            "principio_ativo": medicamento["principio_ativo"],
        },
        "bula_banco": {
            "id": bula_banco["id"],
            "hash_conteudo": hash_banco,
            "created_at": bula_banco.get("created_at"),
            "pdf_path": bula_banco.get("pdf_path"),
        },
        "bula_anvisa": {
            "hash_conteudo": hash_anvisa,
            "fonte_url": bula_anvisa["fonte_url"],
            "id_bula": bula_anvisa["id_bula"],
            "origem_busca": bula_anvisa["origem_busca"],
            "produto": bula_anvisa["produto"],
            "empresa": bula_anvisa["empresa"],
            "processo": bula_anvisa["processo"],
        },
        "status_verificacao": status,
        "mais_recente": mais_recente,
        "mensagem": mensagem,
    }


def verificar_e_atualizar_bula(client, nome_medicamento: str) -> dict[str, Any]:
    """
    Verifica a bula vigente e atualiza o banco quando a ANVISA tiver versão diferente.

    Se o hash do conteúdo atual da ANVISA for igual ao hash vigente no banco, apenas
    registra a verificação. Se for diferente, insere a nova bula como vigente e
    marca a versão anterior como não vigente via inserir_bula.
    """
    medicamentos = buscar_medicamento(client, nome_medicamento)
    if not medicamentos:
        return {
            "success": False,
            "status_verificacao": "erro",
            "acao": "nao_atualizada",
            "mais_recente": None,
            "mensagem": f"Medicamento '{nome_medicamento}' não encontrado no banco.",
        }

    medicamento = medicamentos[0]
    bula_banco = buscar_bula(client, medicamento["id"])
    if not bula_banco:
        registrar_atualizacao_bula(
            client,
            medicamento["id"],
            "erro",
            mensagem="Medicamento encontrado, mas sem bula vigente no banco.",
        )
        return {
            "success": False,
            "medicamento": medicamento,
            "status_verificacao": "erro",
            "acao": "nao_atualizada",
            "mais_recente": None,
            "mensagem": "Medicamento encontrado, mas sem bula vigente no banco.",
        }

    bula_anvisa = baixar_bula_profissional_atual(medicamento["principio_ativo"])
    if not bula_anvisa:
        registrar_atualizacao_bula(
            client,
            medicamento["id"],
            "erro",
            mensagem="Não foi possível obter a bula profissional atual na ANVISA.",
        )
        return {
            "success": False,
            "medicamento": medicamento,
            "bula_banco": {
                "id": bula_banco["id"],
                "hash_conteudo": bula_banco.get("hash_conteudo"),
                "created_at": bula_banco.get("created_at"),
            },
            "status_verificacao": "erro",
            "acao": "nao_atualizada",
            "mais_recente": None,
            "mensagem": "Não foi possível obter a bula profissional atual na ANVISA.",
        }

    extrair_conteudo_secoes_de_bytes = importar_conversor_pdf()
    conteudo_anvisa = extrair_conteudo_secoes_de_bytes(bula_anvisa["pdf_bytes"])
    hash_anvisa = calcular_hash_conteudo_bula(conteudo_anvisa)
    hash_banco = bula_banco.get("hash_conteudo")
    mais_recente = hash_banco == hash_anvisa

    if mais_recente:
        mensagem = "A bula vigente no banco corresponde à bula atual da ANVISA."
        registrar_atualizacao_bula(
            client,
            medicamento["id"],
            "atualizada",
            mensagem=mensagem,
            fonte_url=bula_anvisa["fonte_url"],
            atualizar_ultima_atualizacao=False,
        )
        return {
            "success": True,
            "medicamento": {
                "id": medicamento["id"],
                "principio_ativo": medicamento["principio_ativo"],
            },
            "bula_banco": {
                "id": bula_banco["id"],
                "hash_conteudo": hash_banco,
                "created_at": bula_banco.get("created_at"),
                "pdf_path": bula_banco.get("pdf_path"),
            },
            "bula_anvisa": {
                "hash_conteudo": hash_anvisa,
                "fonte_url": bula_anvisa["fonte_url"],
                "id_bula": bula_anvisa["id_bula"],
                "origem_busca": bula_anvisa["origem_busca"],
                "produto": bula_anvisa["produto"],
                "empresa": bula_anvisa["empresa"],
                "processo": bula_anvisa["processo"],
            },
            "status_verificacao": "atualizada",
            "acao": "mantida",
            "mais_recente": True,
            "mensagem": mensagem,
        }

    nova_bula = inserir_bula(
        client,
        medicamento["id"],
        conteudo_anvisa,
        fonte_url=bula_anvisa["fonte_url"],
    )
    mensagem = "Bula diferente encontrada na ANVISA e cadastrada como nova versão vigente."

    return {
        "success": True,
        "medicamento": {
            "id": medicamento["id"],
            "principio_ativo": medicamento["principio_ativo"],
        },
        "bula_anterior": {
            "id": bula_banco["id"],
            "hash_conteudo": hash_banco,
            "created_at": bula_banco.get("created_at"),
            "pdf_path": bula_banco.get("pdf_path"),
        },
        "bula_nova": {
            "id": nova_bula.get("id"),
            "hash_conteudo": hash_anvisa,
            "status": nova_bula.get("_status"),
            "fonte_url": bula_anvisa["fonte_url"],
            "id_bula_anvisa": bula_anvisa["id_bula"],
            "origem_busca": bula_anvisa["origem_busca"],
            "produto": bula_anvisa["produto"],
            "empresa": bula_anvisa["empresa"],
            "processo": bula_anvisa["processo"],
        },
        "status_verificacao": "atualizada",
        "acao": "atualizada",
        "mais_recente": False,
        "mensagem": mensagem,
    }


def verificar_todas_bulas(client, pausa: float = 2.0) -> list[dict[str, Any]]:
    """Verifica todos os medicamentos cadastrados no banco."""
    resultados = []
    medicamentos = listar_medicamentos(client)

    for medicamento in medicamentos:
        principio_ativo = medicamento["principio_ativo"]
        print(f"\n=== Verificando {principio_ativo} ===")
        try:
            resultado = verificar_bula_mais_recente(client, principio_ativo)
        except Exception as erro:
            resultado = {
                "success": False,
                "medicamento": {
                    "id": medicamento.get("id"),
                    "principio_ativo": principio_ativo,
                },
                "status_verificacao": "erro",
                "mais_recente": None,
                "mensagem": str(erro),
            }
            registrar_atualizacao_bula(
                client,
                medicamento["id"],
                "erro",
                mensagem=str(erro),
            )

        resultados.append(resultado)
        print(resultado["mensagem"])
        time.sleep(pausa)

    return resultados


def verificar_e_atualizar_todas_bulas(client, pausa: float = 2.0) -> list[dict[str, Any]]:
    """Verifica todos os medicamentos cadastrados e atualiza os desatualizados."""
    resultados = []
    medicamentos = listar_medicamentos(client)

    for medicamento in medicamentos:
        principio_ativo = medicamento["principio_ativo"]
        print(f"\n=== Verificando e atualizando {principio_ativo} ===")
        try:
            resultado = verificar_e_atualizar_bula(client, principio_ativo)
        except Exception as erro:
            resultado = {
                "success": False,
                "medicamento": {
                    "id": medicamento.get("id"),
                    "principio_ativo": principio_ativo,
                },
                "status_verificacao": "erro",
                "acao": "nao_atualizada",
                "mais_recente": None,
                "mensagem": str(erro),
            }
            registrar_atualizacao_bula(
                client,
                medicamento["id"],
                "erro",
                mensagem=str(erro),
            )

        resultados.append(resultado)
        print(resultado["mensagem"])
        time.sleep(pausa)

    return resultados


def imprimir_json(dados: Any):
    print(json.dumps(dados, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Verifica se a bula vigente no banco é a mesma disponível na ANVISA."
    )
    parser.add_argument(
        "--medicamento",
        help="Nome ou princípio ativo de um medicamento específico.",
    )
    parser.add_argument(
        "--todos",
        action="store_true",
        help="Verifica todos os medicamentos cadastrados.",
    )
    parser.add_argument(
        "--atualizar",
        action="store_true",
        help="Quando houver diferença, cadastra a bula atual da ANVISA como vigente.",
    )
    parser.add_argument(
        "--pausa",
        type=float,
        default=2.0,
        help="Pausa em segundos entre consultas quando usar --todos.",
    )
    args = parser.parse_args()

    if not args.medicamento and not args.todos:
        parser.error("use --medicamento <nome> ou --todos")

    client = get_client()

    if args.todos and args.atualizar:
        imprimir_json(verificar_e_atualizar_todas_bulas(client, pausa=args.pausa))
        return

    if args.todos:
        imprimir_json(verificar_todas_bulas(client, pausa=args.pausa))
        return

    if args.atualizar:
        imprimir_json(verificar_e_atualizar_bula(client, args.medicamento))
        return

    imprimir_json(verificar_bula_mais_recente(client, args.medicamento))


if __name__ == "__main__":
    main()
