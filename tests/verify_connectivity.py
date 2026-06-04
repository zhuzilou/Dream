import os
import requests
from dotenv import load_dotenv

def test_minimax_connectivity():
    load_dotenv()
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        print("❌ MINIMAX_API_KEY not found in environment")
        return False
    
    print(f"Testing connectivity with API Key: {api_key[:10]}...")
    
    base_url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "MiniMax-M2.7", 
        "messages": [
            {"role": "user", "content": "Ping"}
        ]
    }

    try:
        response = requests.post(base_url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        if "choices" in result and result["choices"]:
            print("✅ MiniMax Connectivity Verified!")
            print(f"Response: {result['choices'][0]['message']['content']}")
            return True
        else:
            print(f"❌ Unexpected response structure: {result}")
            return False
    except Exception as e:
        print(f"❌ MiniMax Connectivity Failed: {e}")
        if 'response' in locals():
            print(f"Response text: {response.text}")
        return False

if __name__ == "__main__":
    test_minimax_connectivity()
