import requests
import os
import logging
from core.config import config

logger = logging.getLogger("gateway.ollama")

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
        timeout = getattr(config, "UPSTREAM_TIMEOUT", 30.0)

        try:
            response = requests.post(url, json=payload, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                msg = data.get("message", {})
                tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
                return {
                    "mode": "local",
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
                    "message": f"Ollama returned HTTP {response.status_code}: {response.text}",
                    "code": response.status_code
                }
            }
        except requests.exceptions.Timeout:
            logger.error(f"Local Ollama request timed out after {timeout} seconds.")
            return {
                "error": {
                    "message": f"Local Ollama inference timed out after {timeout}s.",
                    "code": 504
                }
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": {
                    "message": f"Could not connect to Ollama at {self.base_url}. Ensure Ollama is running ('ollama serve') or use Groq.",
                    "code": 502
                }
            }
        except Exception as e:
            return {
                "error": {
                    "message": f"Ollama client error: {str(e)}",
                    "code": 502
                }
            }
