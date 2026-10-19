from core.llm.groq_client import GroqClient
from core.llm.ollama_client import OllamaClient

class ProviderDispatcher:
    def __init__(self):
        self.groq = GroqClient()
        self.ollama = OllamaClient()

    def complete(self, model_spec: str, messages: list) -> dict:
        """
        Dispatches request to appropriate LLM provider based on 'provider/model' spec.
        Defaults to Groq if no provider prefix is specified.
        """
        spec = model_spec or "groq/llama-3.3-70b-versatile"
        if "/" in spec:
            provider, model_name = spec.split("/", 1)
        else:
            provider, model_name = "groq", spec

        provider = provider.lower()
        if provider == "ollama":
            return self.ollama.complete(model_name, messages)
        else:
            return self.groq.complete(model_name, messages)

dispatcher = ProviderDispatcher()
