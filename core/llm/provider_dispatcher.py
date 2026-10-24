from core.config import config
from core.llm.groq_client import GroqClient
from core.llm.ollama_client import OllamaClient


class ProviderDispatcher:
    def __init__(self):
        self.groq = GroqClient()
        self.ollama = OllamaClient()

    @staticmethod
    def parse_spec(model_spec: str) -> tuple[str, str]:
        """Parses 'provider/model' spec into (provider, model_name)."""
        spec = model_spec or "groq/llama-3.3-70b-versatile"
        if "/" in spec:
            provider, model_name = spec.split("/", 1)
        else:
            provider, model_name = "groq", spec
        return provider.lower().strip(), model_name.strip()

    def complete(self, model_spec: str, messages: list) -> dict:
        """
        Dispatches request to appropriate LLM provider based on 'provider/model' spec.
        Defaults to Groq if no provider prefix is specified.
        Enforces air-gapped offline restrictions when AIRGAPPED_MODE is active.
        """
        provider, model_name = self.parse_spec(model_spec)

        if getattr(config, "AIRGAPPED_MODE", False):
            if provider != "ollama":
                return {
                    "error": {
                        "message": f"External cloud provider '{provider}' is prohibited in air-gapped offline mode. Only local providers ('ollama') are permitted.",
                        "code": 403
                    }
                }

        if provider == "ollama":
            return self.ollama.complete(model_name, messages)
        else:
            return self.groq.complete(model_name, messages)

dispatcher = ProviderDispatcher()
