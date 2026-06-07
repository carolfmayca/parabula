def prompt_interacao (A, B, interA, interB) ->  str:
    """
    @params A: nome da medicação A
    @params interA: seção sobre interação medicamentosa da bula A
    @params B: nome da medicação B
    @params interB: seção sobre interação medicamentosa da bula B
    """
    if not A or not B: 
        return AttributeError()
    
    prompt = f"""
                Use as informações e responda:

                Os medicamentos {A} e {B} possuem interações entre si?
                
                Responda apenas "Sim" ou "Não". 

                Informações dos medicamentos:
                {A}: {interA}


                {B}: {interB}

                """
    return prompt
    
def prompt_advertenciasEprecaucoes (infoPat: list[str], infoReme: list[tuple[str,str]] ) -> str:
    """
    @params infoPat: lista de condições e comorbidades do paciente
    @params infoReme: lista de tuplas com (nome, advertencias e precauções)
    """
    if not infoPat or not infoReme:
        print("excecao")
        return AttributeError()
    
    prompt = f"""
                O paciente tem as seguintes condições e comorbidadades: 
                
                sa{infoPat[0]+ ", " + ", ".join(infoPat[1:])}

                Os remédios prescritos tem as seguintes advertências e precauções:
                """
    prompt += "\n" + "\n".join([f"\t\t{nome} : {info}" for nome,info in infoReme])

    return prompt