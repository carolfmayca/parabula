import src.modelo_llm.prompts as prompts
import src.processador_texto.processador_texto as pt
import src.modelo_llm.open_router as open_router

# interações médicas 2 remédios 
A = "Cefalexina"
B = "Claritromicina"

def interacao_med ():
    prompt_inter = prompts.prompt_interacao(A, B , pt.get_interacoes(A), pt.get_interacoes(B))

    resposta = open_router.llm(prompt_inter)
    return resposta

# informações do paciente:
def advertEprec():
    infoPat = ["criança (menor de 12 anos)", "diabetes I", "obesidade moderada"]

    prompt_aep = prompts.prompt_advertenciasEprecaucoes(infoPat, [(A, pt.get_advertenciasEprecaucoes(A)),
                                                                (B, pt.get_advertenciasEprecaucoes(B))])

    print(prompt_aep)

    resposta = open_router.llm(prompt_aep)
    return resposta

advertEprec()