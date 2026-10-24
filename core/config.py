import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    # Database
    DATABASE = os.getenv("DATABASE", "llm_gateway.db")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

    # Limits & Timeouts
    RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "60"))
    MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", "131072"))  # 128 KB
    UPSTREAM_TIMEOUT = float(os.getenv("UPSTREAM_TIMEOUT", "15.0"))

    # Pluggable Guardrails & ML Detector
    DETECTOR_TYPE = os.getenv("DETECTOR_TYPE", "ensemble")  # regex | ml | ensemble
    ML_THRESHOLD = float(os.getenv("ML_THRESHOLD", "0.5"))

    # Air-Gapped & Offline Deployment
    AIRGAPPED_MODE = os.getenv("AIRGAPPED_MODE", os.getenv("OFFLINE_MODE", "false")).lower() in ("true", "1", "yes")

    # Server
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", 8000)))
    API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

config = Config()
