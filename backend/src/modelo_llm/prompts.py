from typing import List, Optional
def prompt_interacoes(
    bulas_texto: str,
    contexto_medicamentos_str: Optional[str] = None,
) -> str:
    """
    Prompt focado APENAS em interações entre os medicamentos.
    Não recebe dados do paciente — evita que o modelo misture os contextos.
    """
    return f"""
    Você é um sistema especializado em farmacologia clínica.
    Sua tarefa é identificar interações medicamentosas entre todos os medicamentos listados.
    A interação deve estar sustentada pelas informações das bulas fornecidas.

    Medicamentos:
    {contexto_medicamentos_str}

    RESPONDA APENAS EM JSON VÁLIDO, sem texto fora do JSON.

    Formato obrigatório:
    {{
      "summary": {{
        "interactions_found": true,
        "severity": "high",
        "description": "resumo curto citando explicitamente os medicamentos envolvidos e os principais riscos da interação"
      }},
      "details": [
        {{
          "drugs": ["medicamento A", "medicamento B"],
          "severity": "high",
          "description": "descrição detalhada da interação entre esses medicamentos"
        }}
      ]
    }}

    Regras:
    - Analise APENAS interações entre os medicamentos listados. Ignore dados do paciente.
    - Compare TODOS os medicamentos listados entre si, mesmo quando o nome informado pelo usuário for diferente do princípio ativo oficial.
    - Considere interações descritas em qualquer seção fornecida da bula, incluindo contraindicações, advertências, precauções, interações medicamentosas e posologia.
    - Se uma bula disser que um medicamento interage, potencializa, deve ser evitado ou é contraindicado com uma classe/grupo/categoria terapêutica, avalie se algum dos outros medicamentos listados pertence a essa classe/grupo/categoria.
    - Você pode usar conhecimento farmacológico geral APENAS para reconhecer se um medicamento listado pertence a uma classe/grupo/categoria citada na bula. Não use conhecimento externo para criar interações que não estejam sustentadas pelas bulas fornecidas.
    - Não exija que a bula cite literalmente o nome dos dois medicamentos no mesmo par; uma interação por classe/grupo/categoria também deve ser reportada quando estiver sustentada pelo texto das bulas fornecidas.
    - Não escreva texto fora do JSON.
    - Use severity como: low, medium ou high.
    - Use severity high para combinações descritas como contraindicadas, não recomendadas, potencialmente fatais, ou associadas a risco clinicamente grave.
    - Se não houver interação relevante, retorne interactions_found como false e details como lista vazia.
    - O summary.description deve permitir que um usuário identifique rapidamente quais medicamentos apresentam risco sem precisar ler os detalhes.
    - O summary.description deve citar explicitamente os medicamentos envolvidos.
    - Baseie a existência da interação nas informações das bulas fornecidas. Se uma interação não estiver descrita direta ou indiretamente por classe/grupo/categoria nas bulas, não a reporte.
    - O details.description deve conter uma descrição detalhada da interação, se disponíveis nas bulas.
    - O details.description deve citar explicitamente os medicamentos envolvidos na interação. 
    - Se a interação não estiver descrita direta ou indiretamente por classe/grupo/categoria nas bulas, não a reporte.

    Informações das bulas:
    {bulas_texto}
"""


def prompt_riscos_clinicos(
    bulas_texto: str,
    perfil_paciente_str: str,
    contexto_medicamentos_str: Optional[str] = None,
) -> str:
    """
    Prompt focado APENAS nos riscos clínicos do perfil do paciente com cada medicamento.
    Avalia comorbidades, faixa etária e gravidez — sem analisar interações entre medicamentos.
    """

    return f"""
    Você é um sistema especializado em farmacologia clínica.
    Sua tarefa é avaliar se algum dos medicamentos listados apresenta riscos, contraindicações
    ou alertas específicos para o perfil clínico do paciente abaixo.

    Perfil do paciente:
    {perfil_paciente_str}

    Medicamentos:
    {contexto_medicamentos_str}

    Avalie categorias de risco clínico:
    1. Contraindicações ou cautelas por comorbidade (ex: AINE em paciente hipertenso)
    2. Riscos por faixa etária (ex: sedativos em idosos, doses em crianças)
    3. Dosagem de acordo com as informações do paciente (idade, peso) 
    3. Advertencias específicas da via de administração
    4. Contraindicações ou cautelas na gravidez (apenas se is_pregnant for true)

    RESPONDA APENAS EM JSON VÁLIDO, sem texto fora do JSON.

    Formato obrigatório:
    {{
      "risks_found": true,
      "severity": "high",
      "items": [
        {{
          "drug": "nome do medicamento",
          "risk_factor": "fator do paciente que motivou o risco (ex: asma, idade avançada, gravidez)"
          "severity": "high",
          "description": "descrição detalhada do risco para este paciente"
        }}
      ]
    }}

    Regras:
    - Analise APENAS riscos do medicamento com o perfil do paciente. Não analise interações entre medicamentos.
    - Se is_pregnant for false, não avalie riscos de gravidez.
    - Use severity como: low, medium ou high.
    - O severity raiz deve refletir o maior severity encontrado nos items.
    - Se não houver nenhum risco, retorne risks_found como false e items como lista vazia.
    - Não escreva texto fora do JSON.
    - Baseie-se EXCLUSIVAMENTE nas informações das bulas fornecidas. Se um risco não estiver descrito nas bulas, não o reporte.
    - NÃO reporte interações entre medicamentos. Isso é responsabilidade de outro sistema. Reporte APENAS riscos decorrentes do perfil do paciente (comorbidades, idade, gravidez). 
    - Se o único risco identificado for uma interação entre medicamentos, retorne risks_found como false e items como lista vazia.
    - Nem todas as informações do paciente podem estar disponíveis.
    - Analise apenas os dados clínicos efetivamente fornecidos e não faça suposições sobre informações ausentes.
    - Se idade não foi informada, não avalie riscos relacionados à faixa etária.
    - Se sexo biológico não foi informado, não considere riscos específicos de sexo.
    - Se comorbidades não foram informadas, não considere comorbidades inexistentes.
    - O campo risk_factor deve indicar de forma curta e objetiva qual dado do paciente motivou aquele risco (ex: "Asma", "Idade avançada (75 anos)", "Gravidez", "Hipertensão"). Não repita o nome do medicamento nesse campo.

    Informações das bulas:
    {bulas_texto}
"""
