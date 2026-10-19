import requests
from core.config import config

class GroqClient:
    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def complete(self, model: str, messages: list):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model or "llama-3.1-70b-versatile",
            "messages": messages
        }
        response = requests.post(self.url, headers=headers, json=data)
        return response.json()
