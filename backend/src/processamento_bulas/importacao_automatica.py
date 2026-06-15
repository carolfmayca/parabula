from typing import Any


def _importar_coleta_anvisa():
    try:
        from backend.src.processamento_bulas.coleta.anvisa import (
            HEADERS,
            criar_scraper,
            extrair_principios_ativos,
            get_com_retry,
            get_detalhes_medicamento,
            normalizar_nome,
            pesquisar_por_nome_produto,
            pesquisar_por_principio_ativo,
        )
    except ModuleNotFoundError as exc:
        if exc.name not in {"backend", "backend.src"}:
            raise
        from src.processamento_bulas.coleta.anvisa import (
            HEADERS,
            criar_scraper,
            extrair_principios_ativos,
            get_com_retry,
            get_detalhes_medicamento,
            normalizar_nome,
            pesquisar_por_nome_produto,
            pesquisar_por_principio_ativo,
        )

    return {
        "HEADERS": HEADERS,
        "criar_scraper": criar_scraper,
        "extrair_principios_ativos": extrair_principios_ativos,
        "get_com_retry": get_com_retry,
        "get_detalhes_medicamento": get_detalhes_medicamento,
        "normalizar_nome": normalizar_nome,
        "pesquisar_por_nome_produto": pesquisar_por_nome_produto,
        "pesquisar_por_principio_ativo": pesquisar_por_principio_ativo,
    }


def _importar_conversor_pdf():
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


def _importar_operacoes_banco():
    try:
        from backend.db.supabase_client import (
            inserir_alias,
            inserir_bula,
            inserir_medicamento,
            registrar_atualizacao_bula,
        )
    except ModuleNotFoundError as exc:
        if exc.name not in {"backend", "backend.db"}:
            raise
        from db.supabase_client import (
            inserir_alias,
            inserir_bula,
            inserir_medicamento,
            registrar_atualizacao_bula,
        )

    return inserir_alias, inserir_bula, inserir_medicamento, registrar_atualizacao_bula


def montar_url_bula_profissional(id_bula: str) -> str:
    return (
        "https://consultas.anvisa.gov.br/api/consulta/medicamentos/arquivo"
        f"/bula/parecer/{id_bula}/?Authorization="
    )


def selecionar_primeira_bula_profissional(resultado: dict | None) -> dict | None:
    if not isinstance(resultado, dict):
        return None

    for medicamento in resultado.get("content", []):
        if medicamento.get("idBulaProfissionalProtegido"):
            return medicamento

    return None


def buscar_registro_anvisa(scraper, nome: str) -> tuple[dict | None, str | None]:
    coleta = _importar_coleta_anvisa()

    resultado = coleta["pesquisar_por_principio_ativo"](scraper, nome)
    medicamento = selecionar_primeira_bula_profissional(resultado)
    if medicamento:
        return medicamento, "principio_ativo"

    resultado = coleta["pesquisar_por_nome_produto"](scraper, nome)
    medicamento = selecionar_primeira_bula_profissional(resultado)
    if medicamento:
        return medicamento, "nome_produto"

    return None, None


def resolver_principio_ativo(scraper, nome: str, registro_anvisa: dict, origem_busca: str | None) -> str:
    coleta = _importar_coleta_anvisa()
    processo = registro_anvisa.get("numProcesso")

    if processo:
        detalhes = coleta["get_detalhes_medicamento"](scraper, processo)
        principios = coleta["extrair_principios_ativos"](detalhes)
        if principios:
            return principios[0]

    if origem_busca == "principio_ativo":
        return nome

    return registro_anvisa.get("nomeProduto") or nome


def registro_corresponde_ao_nome(scraper, nome: str, registro_anvisa: dict) -> tuple[bool, list[str]]:
    coleta = _importar_coleta_anvisa()
    normalizar_nome = coleta["normalizar_nome"]

    nome_normalizado = normalizar_nome(nome)
    produto_normalizado = normalizar_nome(registro_anvisa.get("nomeProduto") or "")
    principios = []

    processo = registro_anvisa.get("numProcesso")
    if processo:
        detalhes = coleta["get_detalhes_medicamento"](scraper, processo)
        principios = coleta["extrair_principios_ativos"](detalhes)

    principios_normalizados = {normalizar_nome(principio) for principio in principios}
    corresponde_produto = (
        bool(produto_normalizado)
        and (
            nome_normalizado == produto_normalizado
            or nome_normalizado in produto_normalizado
            or produto_normalizado in nome_normalizado
        )
    )
    corresponde_principio = nome_normalizado in principios_normalizados

    return corresponde_produto or corresponde_principio, principios


def conteudo_tem_secoes(conteudo_json: dict) -> bool:
    return any(valor for valor in conteudo_json.values())


def importar_medicamento_desconhecido(client, nome: str) -> dict[str, Any]:
    """
    Tenta buscar uma bula profissional na ANVISA e cadastrar no banco.

    Retorna importado=False quando a ANVISA não possui uma bula profissional
    utilizável para o nome informado.
    """
    coleta = _importar_coleta_anvisa()
    extrair_conteudo_secoes_de_bytes = _importar_conversor_pdf()
    inserir_alias, inserir_bula, inserir_medicamento, registrar_atualizacao_bula = (
        _importar_operacoes_banco()
    )

    scraper = coleta["criar_scraper"]()
    normalizar_nome = coleta["normalizar_nome"]

    registro_anvisa, origem_busca = buscar_registro_anvisa(scraper, nome)
    if not registro_anvisa:
        return {
            "importado": False,
            "motivo": "nao_encontrado_anvisa",
            "mensagem": f"Medicamento '{nome}' não encontrado na ANVISA.",
        }

    registro_compativel, principios = registro_corresponde_ao_nome(
        scraper,
        nome,
        registro_anvisa,
    )
    if not registro_compativel:
        return {
            "importado": False,
            "motivo": "resultado_anvisa_incompativel",
            "mensagem": (
                f"A ANVISA retornou '{registro_anvisa.get('nomeProduto')}' "
                f"para '{nome}', mas o resultado não parece corresponder ao medicamento."
            ),
        }

    id_bula = registro_anvisa["idBulaProfissionalProtegido"]
    fonte_url = montar_url_bula_profissional(id_bula)
    response = coleta["get_com_retry"](
        scraper,
        fonte_url,
        headers=coleta["HEADERS"],
        descricao=f"download automático da bula '{nome}'",
    )
    if not response or not response.ok:
        return {
            "importado": False,
            "motivo": "falha_download_bula",
            "mensagem": f"Não foi possível baixar a bula de '{nome}' na ANVISA.",
        }

    conteudo_json = extrair_conteudo_secoes_de_bytes(response.content)
    if not conteudo_tem_secoes(conteudo_json):
        return {
            "importado": False,
            "motivo": "pdf_sem_conteudo_extraido",
            "mensagem": f"A bula de '{nome}' foi encontrada, mas não pôde ser extraída.",
        }

    principio_ativo = normalizar_nome(
        principios[0] if principios else resolver_principio_ativo(
            scraper,
            nome,
            registro_anvisa,
            origem_busca,
        )
    )
    medicamento = inserir_medicamento(client, principio_ativo)
    medicamento_id = medicamento["id"]

    nome_normalizado = normalizar_nome(nome)
    produto = registro_anvisa.get("nomeProduto")
    produto_normalizado = normalizar_nome(produto) if produto else None

    if nome_normalizado != principio_ativo:
        inserir_alias(client, medicamento_id, nome_normalizado, tipo_alias="comercial")

    if produto_normalizado and produto_normalizado not in {principio_ativo, nome_normalizado}:
        inserir_alias(client, medicamento_id, produto_normalizado, tipo_alias="comercial")

    bula = inserir_bula(
        client,
        medicamento_id,
        conteudo_json,
        fonte_url=fonte_url,
    )
    registrar_atualizacao_bula(
        client,
        medicamento_id,
        "atualizada",
        mensagem=f"Bula importada automaticamente após citação de '{nome}'.",
        fonte_url=fonte_url,
        atualizar_ultima_atualizacao=True,
    )

    return {
        "importado": True,
        "medicamento_id": medicamento_id,
        "principio_ativo": principio_ativo,
        "bula_id": bula.get("id"),
        "status_bula": bula.get("_status"),
        "fonte_url": fonte_url,
        "origem_busca": origem_busca,
        "produto": produto,
        "processo": registro_anvisa.get("numProcesso"),
    }
