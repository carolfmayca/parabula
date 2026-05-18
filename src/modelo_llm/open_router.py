from openrouter import OpenRouter
from processador_texto.processador_texto import get_interacoes
import os

A = "cefalexina"
B = "dipirona"

content = f"""
                Use as informações e responda:

                Os medicamentos {A} e {B} possuem interações entre si?
                
                Responda apenas "Sim" ou "Não". 

                Informações dos medicamentos:
                {A}: {get_interacoes(A)}


                {B}: {get_interacoes(B)}

                """

print(content)

with OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY")) as client:
    response = client.chat.send(
        model = "openai/gpt-oss-120b:free",
        # max_tokens = 200,
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]

    )
print(response.model)
print(response.choices[0].message.content)


# response = requests.post(
#   url="https://openrouter.ai/api/v1/chat/completions",
#   headers={
#     "Authorization": "Bearer <OPENROUTER_API_KEY>",
#     "Content-Type": "application/json",
#   },
#   data=json.dumps({
#     )
# )

# data = response.json()
# print(data['choices'][0]['message']['content'])
# # Check which model was selected
# print('Model used:', data['model'])

