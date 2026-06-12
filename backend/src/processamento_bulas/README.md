# Processamento de Bulas

Pipeline responsável por coletar bulas profissionais na ANVISA, converter PDFs para JSON e carregar os dados no Supabase.

## Fluxo

```text
ANVISA -> PDF -> JSON -> Supabase
```

Etapas:

1. `coleta/`: baixa as bulas profissionais no site da ANVISA em PDF.
2. `conversao/`: transforma PDFs em JSON padronizado por seção.
3. `carga/`: carrega o JSON agrupado no Supabase.
4. `verificacao.py`: compara a bula vigente no banco com a bula atual da ANVISA.
5. `importacao_automatica.py`: importa uma bula sob demanda quando a API recebe um medicamento desconhecido.

## Estrutura

```text
processamento_bulas/
├── coleta/
│   └── anvisa.py
├── conversao/
│   └── pdf_to_json.py
├── carga/
│   └── supabase_loader.py
├── importacao_automatica.py
├── notebooks/
├── pipeline.py
├── paths.py
└── verificacao.py
```

## Comandos

Converter todos os PDFs já baixados:

```bash
python processar_bulas.py
```

Executar pipeline completa a partir da raiz:

```bash
python -m backend.src.processamento_bulas.pipeline --medicamentos "paracetamol" "dipirona"
```

Pular coleta e usar PDFs existentes:

```bash
python -m backend.src.processamento_bulas.pipeline --pular-coleta
```

Carregar JSON agrupado no Supabase:

```bash
python -m backend.src.processamento_bulas.carga.supabase_loader
```

Verificar uma bula:

```bash
python -m backend.src.processamento_bulas.verificacao --medicamento "paracetamol"
```

Verificar todas as bulas:

```bash
python -m backend.src.processamento_bulas.verificacao --todos
```

## Banco

Tabelas relacionadas:

- `medicamento`;
- `medicamento_alias`;
- `bula_medicamento`;
- `bula_atualizacao`.

A inserção de bula calcula um hash do JSON para evitar duplicidade. Quando uma nova versão é inserida, a versão anterior é marcada como não vigente.

