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
    Sua tarefa é identificar interações medicamentosas entre os medicamentos listados,
    com base exclusivamente nas informações das bulas fornecidas.

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
    - Analise APENAS interações entre os medicamentos. Ignore dados do paciente.
    - Não escreva texto fora do JSON.
    - Use severity como: low, medium ou high.
    - Se não houver interação relevante, retorne interactions_found como false e details como lista vazia.
    - O summary.description deve permitir que um usuário identifique rapidamente quais medicamentos apresentam risco sem precisar ler os detalhes.
    - O summary.description deve citar explicitamente os medicamentos envolvidos.
    - Baseie-se EXCLUSIVAMENTE nas informações das bulas fornecidas. Se uma interação não estiver descrita nas bulas, não a reporte.
    - O details.description deve conter uma descrição detalhada da interação, se disponíveis nas bulas.
    - O details.description deve citar explicitamente os medicamentos envolvidos na interação. 
    - Se a interação não estiver descrita nas bulas, não a reporte.

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

    Informações das bulas:
    {bulas_texto}
"""
