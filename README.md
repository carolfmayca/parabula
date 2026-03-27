# parabula

Uma solução digital (inicialmente uma API) que verifica a segurança do uso de medicamentos considerando não apenas interações entre fármacos, mas também o perfil clínico do paciente (idade, gênero, gravidez, comorbidades, via de administração) e as informações oficiais das bulas dos medicamentos registrados no Brasil.



# Respostas Prof

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

## Quais soluções já existem?

### Interações medicamentosas:



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

# To do

## Top Prioridade

- Fazer o pitch
- Validar ideias com professor
- Validar ideias com povo de farmácia
- Verificar se será necessário fazer interface

## Outros

- Verificar qual SGBD vamos utilizar
- Ter uma minibase de dados com medicamentos e suas bulas salvas para medicamentos que são mais comumente chamados/utilizados
- Manter um dicionário com os nomes comerciais
