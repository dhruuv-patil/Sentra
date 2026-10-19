import requests
from core.config import config

class OllamaClient:
    def __init__(self):
        self.url = f"{config.OLLAMA_URL}/api/chat"

    def complete(self, model: str, prompt: str):
        data = {
            "model": model or "llama3",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        response = requests.post(self.url, json=data)
        return response.json()
