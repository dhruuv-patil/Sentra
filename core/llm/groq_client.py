import os
import requests
from core.config import config

class GroqClient:
    def __init__(self):
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def api_key(self):
        return os.getenv("GROQ_API_KEY") or config.GROQ_API_KEY

    def complete(self, model: str, messages: list):
        api_key = self.api_key
        if not api_key or api_key.startswith("your_") or api_key in ("demo", "test"):
            last_prompt = messages[-1]["content"] if messages else ""
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": f"[Gateway Security Verified]: Prompt passed all security guardrails. (Running in demo mode. Provide a valid GROQ_API_KEY in .env for live Groq inference)."
                    }
                }],
                "usage": {
                    "total_tokens": len(last_prompt.split()) * 2 + 25
                }
            }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model or "llama-3.1-70b-versatile",
            "messages": messages
        }
        response = requests.post(self.url, headers=headers, json=data)
        return response.json()

