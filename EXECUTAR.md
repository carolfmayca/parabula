# Instruções de Execução

## Instalação

1. Instale as dependências:
```bash
pip install -r requirements.txt
pip install -e .
```

## Executando os módulos

**Opção 1: Usando Python módulo (recomendado)**
```bash
python -m src.modelo_llm.open_router
```

**Opção 2: Usando script de wrapper**
```bash
python run.py
```

**Opção 3: Teste interativo**
```bash
python -m src.processador_texto.teste
```

## Variáveis de ambiente

Configure a seguinte variável de ambiente antes de executar:

```bash
export OPENROUTER_API_KEY="sua_chave_aqui"
```

## Estrutura do Projeto

```
parabula/
├── src/
│   ├── __init__.py
│   ├── modelo_llm/
│   │   ├── __init__.py
│   │   └── open_router.py
│   └── processador_texto/
│       ├── __init__.py
│       ├── processador_texto.py
│       └── teste.py
├── bulas_json/          # Arquivos JSON com bulas de medicamentos
├── bulas_pdf/           # Arquivos PDF originais
├── setup.py             # Configuração do pacote
├── run.py              # Script wrapper para executar com imports corretos
└── requirements.txt    # Dependências
```

## O que foi corrigido

1. **Adicionados `__init__.py`** em todos os pacotes Python
2. **Importações relativas** agora usam caminhos corretos
3. **Caminhos de arquivo** agora usam `pathlib` com caminho absoluto baseado no arquivo
4. **setup.py** criado para permitir instalação como pacote
