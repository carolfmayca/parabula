# Processamento de bulas

A pipeline de bulas segue esta ordem:

1. `coleta/`: baixa as bulas profissionais no site da ANVISA em PDF.
2. `conversao/`: transforma os PDFs em JSONs padronizados por seção.
3. `carga/`: carrega o JSON agrupado no banco Supabase.
4. `verificacao.py`: compara a bula vigente no banco com a bula atual da ANVISA.

## Estrutura

```text
processamento_bulas/
├── coleta/
│   └── anvisa.py              # ANVISA -> bulas_pdf/*.pdf
├── conversao/
│   └── pdf_to_json.py         # bulas_pdf/*.pdf -> bulas_json/*.json
├── carga/
│   └── supabase_loader.py     # bulas_json/bulas_agrupadas.json -> banco
├── notebooks/
│   └── pdfs_bulas.ipynb       # exploração/histórico
├── pipeline.py                # executa as etapas em sequência
├── paths.py                   # caminhos compartilhados da pipeline
└── verificacao.py             # banco -> ANVISA -> comparação de hash
```

## Comandos úteis

Converter todos os PDFs já baixados:

```bash
python processar_bulas.py
```

Executar a pipeline completa:

```bash
python -m backend.src.processamento_bulas.pipeline --medicamentos "paracetamol" "dipirona"
```

Pular a coleta e usar PDFs já existentes:

```bash
python -m backend.src.processamento_bulas.pipeline --pular-coleta
```

Carregar no banco usando o JSON agrupado já existente:

```bash
python -m backend.src.processamento_bulas.carga.supabase_loader
```

Verificar se a bula de um medicamento está atualizada:

```bash
python -m backend.src.processamento_bulas.verificacao --medicamento "paracetamol"
```

Verificar todos os medicamentos cadastrados:

```bash
python -m backend.src.processamento_bulas.verificacao --todos
```
