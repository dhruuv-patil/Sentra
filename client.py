import requests
import json

# Configuration
SERVER_URL = "http://localhost:8000/v1/chat/completions"
API_KEY = "dbeca5a1-66bf-4254-9aa4-f6d99e9eb62d"

def send_prompt(prompt, model="groq/llama-3.3-70b-versatile"):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(SERVER_URL, headers=headers, json=data)
        if response.status_code == 200:
            res_json = response.json()
            if "choices" in res_json:
                cache_tag = " [CACHED]" if res_json.get("cache_hit") else ""
                print(f"\n[SUCCESS{cache_tag}]:\n")
                print(res_json["choices"][0]["message"]["content"])
            else:
                req_id = res_json.get('request_id')
                print(f"\n[PENDING APPROVAL]: {res_json.get('message')}")
                print(f"Check status at: http://localhost:8000/v1/requests/{req_id}")
        elif response.status_code == 403:
            print(f"\n[BLOCKED] Safety Guardrail Triggered:\n")
            print(response.json().get("detail") or response.json().get("error"))
        else:
            print(f"\n[ERROR] Status Code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"\n[CONNECTION ERROR] {e}")

if __name__ == "__main__":
    print("--- LLM Security Gateway Terminal Client ---")
    while True:
        user_prompt = input("\nEnter your prompt (or 'quit' to exit): ")
        if user_prompt.lower() in ['quit', 'exit']:
            break
        send_prompt(user_prompt)
