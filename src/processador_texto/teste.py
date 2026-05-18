from processador_texto.processador_texto import get_interacoes   

while True:
    texto = input("Digite um texto (ou 'sair' para encerrar): ")
    if texto.lower() == 'sair':
        break
    resultado = get_interacoes(texto)
    print("Resultado:", resultado)