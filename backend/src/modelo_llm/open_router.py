from openrouter import OpenRouter
import os

def llm (content):
    with OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY")) as client:
        try:
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
        
            return response.choices[0].message.content
        
        except Exception as e:
            print("Error:", e)
            return None

from fastapi import HTTPException
import json
def chamar_modelo(client: OpenRouter, prompt: str) -> dict:
    """Chama o modelo e já retorna o JSON parseado, lançando HTTPException se falhar."""
    response = client.chat.send(
        model="openai/gpt-oss-120b:free",
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INVALID_MODEL_RESPONSE",
                "message": "O modelo retornou uma resposta inválida."
            }
        )

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

