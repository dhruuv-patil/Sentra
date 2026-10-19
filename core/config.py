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
    # Server
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", 8000)))
    API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

config = Config()
