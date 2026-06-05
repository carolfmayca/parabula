from openrouter import OpenRouter
import os

def llm (content):
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
    
    return response.choices[0].message.content


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

