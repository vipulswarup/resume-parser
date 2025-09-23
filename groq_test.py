from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")  # load env vars

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
resp = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Say hello in JSON"}],
)
print(resp.choices[0].message.content)
