import requests
import os
from core.config import config

class OllamaClient:
    @property
    def base_url(self):
        return os.getenv("OLLAMA_URL") or config.OLLAMA_URL or "http://localhost:11434"

    def complete(self, model: str, messages: list) -> dict:
        """
        Completes chat prompts against local Ollama instance with standard OpenAI-compatible format.
        """
        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": model or "llama3",
            "messages": messages,
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                msg = data.get("message", {})
                tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
                return {
                    "choices": [{
                        "message": {
                            "role": msg.get("role", "assistant"),
                            "content": msg.get("content", "")
                        }
                    }],
                    "usage": {
                        "total_tokens": tokens or 25
                    }
                }
            return {
                "error": {
                    "message": f"Ollama returned HTTP {response.status_code}: {response.text}"
                }
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": {
                    "message": f"Could not connect to Ollama at {self.base_url}. Ensure Ollama is running ('ollama serve') or use a Groq model."
                }
            }
        except Exception as e:
            return {
                "error": {
                    "message": f"Ollama client error: {str(e)}"
                }
            }
