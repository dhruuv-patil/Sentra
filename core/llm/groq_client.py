import logging
import os

import requests

from core.config import config

logger = logging.getLogger("gateway.groq")

class GroqClient:
    def __init__(self):
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def api_key(self):
        return os.getenv("GROQ_API_KEY") or config.GROQ_API_KEY

    def complete(self, model: str, messages: list) -> dict:
        api_key = self.api_key
        if not api_key or api_key.startswith("your_") or api_key in ("demo", "test"):
            logger.warning("GROQ_API_KEY not configured or set to demo/test. Executing completion in explicit DEMO mock mode.")
            last_prompt = messages[-1]["content"] if messages and isinstance(messages[-1], dict) else ""
            return {
                "mode": "demo",
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "[Gateway Security Verified]: Prompt passed all security guardrails. (Running in demo mode. Provide a valid GROQ_API_KEY in .env for live Groq inference)."
                    }
                }],
                "usage": {
                    "total_tokens": len(str(last_prompt).split()) * 2 + 25
                }
            }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model or "llama-3.3-70b-versatile",
            "messages": messages
        }
        timeout = getattr(config, "UPSTREAM_TIMEOUT", 15.0)

        try:
            response = requests.post(self.url, headers=headers, json=data, timeout=timeout)
        except requests.exceptions.Timeout:
            logger.error(f"Groq upstream request timed out after {timeout} seconds.")
            return {
                "error": {
                    "message": f"Upstream Groq request timed out after {timeout} seconds.",
                    "code": 504
                }
            }
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to upstream Groq API.")
            return {
                "error": {
                    "message": "Failed to connect to upstream Groq API endpoint.",
                    "code": 502
                }
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Upstream Groq request error: {e}")
            return {
                "error": {
                    "message": f"Upstream Groq network error: {str(e)}",
                    "code": 502
                }
            }

        try:
            res_json = response.json()
        except Exception:
            return {
                "error": {
                    "message": f"Malformed non-JSON response from Groq (HTTP {response.status_code})",
                    "code": 502
                }
            }

        if response.status_code != 200:
            err_msg = res_json.get("error", {}).get("message") if isinstance(res_json, dict) else response.text
            return {
                "error": {
                    "message": f"Groq provider returned HTTP {response.status_code}: {err_msg}",
                    "code": response.status_code
                }
            }

        if not isinstance(res_json, dict) or "choices" not in res_json or not res_json["choices"]:
            return {
                "error": {
                    "message": "Malformed provider response: missing 'choices' array in completion payload.",
                    "code": 502
                }
            }

        res_json["mode"] = "live"
        return res_json
