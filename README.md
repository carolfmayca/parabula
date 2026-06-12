# parabula

Uma solução digital (inicialmente uma API) que verifica a segurança do uso de medicamentos considerando não apenas interações entre fármacos, mas também o perfil clínico do paciente (idade, gênero, gravidez, comorbidades, via de administração) e as informações oficiais das bulas dos medicamentos registrados no Brasil.

---
# Sobre o Repositório e Boas Práticas

## Estrutura final recomendada

**main** 

**develop**

feature/login-api 

feature/parser-bulas

feature/frontend-dashboard // _cada feature uma branch nova_

hotfix/correcao-token // _fez a feature, subiu pra development, matou a branch que fez e tem que consertar_

## Recomendações importantes

**Nunca desenvolver direto em:**
- main
- develop

**Sempre:**
- feature branch pequena
- PR pequeno
- commits descritivos
- merge frequente da develop

## Convenção boa de nomes
- Branches
    - feature/nome-feature
    -fix/nome-correcao
    -hotfix/nome-urgente
    -refactor/nome-refatoracao

- Commits
    - feat: adiciona parser de pdf
    - fix: corrige autenticação JWT
    - refactor: separa serviços de inferência
    - docs: atualiza README

## 1. Fluxo diário de cada desenvolvedor

Atualizar a develop local

Antes de começar qualquer tarefa:
``` bash
git checkout develop
git pull origin develop
```

Criar uma branch de feature

Exemplo:
```bash
git checkout -b feature/login-api

ou

git checkout -b feature/parser-bulas
```

## 2. Trabalhar normalmente

Ver arquivos alterados
```bash
git status
```

Adicionar alterações

Tudo:

``` bash
git add .
```

Ou arquivos específicos:
```bash
git add backend/auth.py
Fazer commit
git commit -m "feature: Implementa autenticação JWT"
```

## 3. Enviar a branch para o GitHub

Primeira vez:

```bash
git push -u origin feature/login-api
```

Depois:

```bash
git push
```

## 4. Atualizar sua feature com mudanças da develop

Isso evita conflitos enormes.

Estando na sua branch:

```bash
git checkout feature/login-api
git pull origin develop
```

ou de forma mais limpa:

``` bash
git fetch origin
git merge origin/develop
```

Se houver conflitos:

1. editar arquivos

2. resolver manualmente

depois:
```bash
git add .
git commit
```

## 5. Fazer Pull Request (PR)

**No GitHub:**

Abrir o repositório

**Ir em:**

_Pull Requests_

**Clicar:**

_New Pull Request_

**Selecionar:**

_Base branch:_
_develop_
_Compare branch:_
_feature/feature-trabalhada_

Então ficará:

_feature/login-api → develop_

**Criar o PR**

**Adicionar:**

- `título`
- `descrição do que foi feito`

### Exemplo:

**Implementa autenticação JWT**

**Descrição:**

- adiciona login
- adiciona middleware JWT
- cria endpoint de refresh token

**Depois:**

**Create Pull Request**

## 6. Revisão e merge

Após aprovação:

__Merge Pull Request__

Preferencialmente:

__Squash and Merge__

porque mantém o histórico limpo.

## 7. Atualizar develop local após merge

**Todos do time:**
```bash
git checkout develop
git pull origin develop
```

## 8. Subir para produção

Quando o sistema estiver estável:

```bash
git checkout main
git pull origin main
git merge develop
git push origin main
```