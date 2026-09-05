import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

try:
    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: RecoverAI AI agent connected successfully."
            }
        ],
        max_tokens=100
    )

    print("API request successful!")
    print("Response:")
    print(response.choices[0].message.content)

except Exception as e:
    print("API request failed:")
    print(e)