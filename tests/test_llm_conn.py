import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("MINIMAX_API_KEY")
base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1/text_experience")

print(f"Testing connectivity to: {base_url}")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": "abab6.5-chat",
    "messages": [{"role": "user", "content": "Hi"}]
}

try:
    response = requests.post(base_url, headers=headers, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Connection Failed: {e}")
