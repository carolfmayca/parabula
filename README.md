# parabula

Uma solução digital (inicialmente uma API) que verifica a segurança do uso de medicamentos considerando não apenas interações entre fármacos, mas também o perfil clínico do paciente (idade, gênero, gravidez, comorbidades, via de administração) e as informações oficiais das bulas dos medicamentos registrados no Brasil.


## Para quem é o produto?


**Opção 1: Profissionais da saúde e hospitais (B2B)**

- **Prós:** Mercado mais estável, disposição a pagar, integração com sistemas existentes (EMR/EHR)
- **Contras:** Ciclo de vendas longo, necessidade de certificações e validação clínica

**Opção 2: Qualquer pessoa interessada (B2C) (??????)**

- **Prós:** Mercado massivo, escalabilidade viral, baixa barreira de entrada
- **Contras:** Responsabilidade legal maior, necessidade de linguagem acessível, usuários menos dispostos a pagar


## Qual dor específica ele resolve?


O alto risco de eventos adversos evitáveis causados por prescrições ou administrações de medicamentos **sem a devida checagem do contexto clínico do paciente**.

Essa dor se desdobra em três camadas:

1. **Interações medicamentosas perigosas** – quando dois ou mais fármacos são combinados sem conhecimento de que juntos podem causar toxicidade, perda de eficácia ou reações graves.
2. **Contraindicações ligadas ao perfil do paciente** – um medicamento pode ser seguro para uma pessoa, mas **fatal para outra** dependendo de:
    - **Faixa etária** (ex: certos antibióticos contraindicados em crianças; aspirina em menores de 12 anos)
    - **Gênero / gravidez / lactação** (ex: isotretinoína absolutamente contraindicada na gravidez por risco de malformações)
    - **Condições genotípicas / metabólicas** (ex: deficiência de G6PD → risco de hemólise com certos analgésicos)
    - **Comorbidades** (ex: AINEs em pacientes com insuficiência renal)
    - **Via de administração errada** – adrenalina aplicada **por via intravenosa** para tratar uma crise de tosse, quando o correto seria **intramuscular**, levando à morte de um menino.
3. **Falta de ferramentas acessíveis no ponto de decisão** – tanto profissionais de saúde quanto cuidadores e pacientes não têm um meio rápido, simples e confiável de cruzar **medicamento + paciente + contexto** antes de administrar ou dispensar um remédio.



## O que tornaria a proposta de vocês diferente?

1. Foco em **bula** como fonte de dados

2. **IA generativa para feedback contextualizado (?)**

Enquanto a maioria dá um alerta genérico ("interação moderada"), você pode oferecer:

- **Explicação em linguagem simples:** *"Este remédio para pressão pode reduzir o efeito do seu anticoncepcional. Consulte seu médico sobre ajuste."* 
    - no caso de B2C
- **Consideração de contexto:** idade, gênero, condições pré-existentes
3. Modelo em API

## Como a startup ganharia dinheiro?

**Modelo Proposto: API por uso + Assinaturas**

**1. API para desenvolvedores e empresas**

- **Preço sugerido:** US$ 0,20 - 0,30 por 1.000 consultas (competitivo com Apify)
- **Clientes:** Telemedicinas, farmácias digitais, apps de saúde, hospitais

**2. Planos de assinatura B2B (hospitais/clínicas)**

- **Plano Básico:** Acesso via API com suporte
- **Plano Enterprise:** Integração com EHR/EMR, SLAs, compliance HIPAA

**3. Freemium B2C**

- Consultas grátis limitadas (ex: 5 interações por mês)
- Upgrade para assinatura mensal (US$ 4,99/mês) com consultas ilimitadas + funcionalidades premium (histórico, relatórios para médicos)


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