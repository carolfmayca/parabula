# Frontend

Interface web do ParaBula, construída com Express.js e Handlebars.

## Instalação

```bash
cd frontend
npm install
```

## Execução

Com o backend rodando em `http://localhost:8000`:

```bash
BACKEND_URL=http://localhost:8000 npm start
```

Acesse:

```text
http://localhost:3000
```

## Uso

1. Adicione pelo menos dois medicamentos.
2. Informe dados do paciente, se disponíveis.
3. Clique em `ANALISAR INTERAÇÕES`.
4. O frontend envia a requisição para o backend.
5. A tela de resultados exibe interações e riscos clínicos.

Dados clínicos atualmente considerados:

- idade;
- sexo biológico;
- gravidez;
- comorbidades.

A análise por via de administração ainda será adicionada.

## Estrutura

```text
frontend/
├── app.js
├── controllers/
│   └── interactionController.js
├── helpers/
│   └── handlebars-helpers.js
├── public/
│   ├── css/
│   ├── img/
│   └── js/
├── routes/
│   └── index.js
└── views/
    ├── interaction.hbs
    ├── results.hbs
    └── layouts/
```

## Problemas Comuns

### Frontend não conecta ao backend

Confirme se o backend está rodando:

```text
http://localhost:8000
```

E inicie o frontend com:

```bash
BACKEND_URL=http://localhost:8000 npm start
```

### `process.cwd failed`

Esse erro geralmente acontece quando o terminal está aberto em uma pasta que foi movida ou apagada. Abra um novo terminal e entre novamente na pasta:

```bash
cd /home/carole/FACULDADE/7o\ Periodo/SD/parabula/frontend
```

