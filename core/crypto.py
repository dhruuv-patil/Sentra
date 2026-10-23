import logging
from cryptography.fernet import Fernet
from core.config import config

logger = logging.getLogger("gateway.crypto")

class CryptoManager:
    def __init__(self):
        self.fernet = None
        self._init_fernet()

    def _init_fernet(self):
        key = config.ENCRYPTION_KEY
        if key:
            try:
                self.fernet = Fernet(key.encode() if isinstance(key, str) else key)
                return
            except Exception as e:
                logger.warning(f"Invalid ENCRYPTION_KEY configured: {e}. Falling back to ephemeral key.")
        
        # Ephemeral session key fallback to prevent data loss when ENCRYPTION_KEY is unset
        logger.warning("No valid ENCRYPTION_KEY set. Generating ephemeral in-memory Fernet key for session.")
        self.fernet = Fernet(Fernet.generate_key())

    def _ensure_fernet(self):
        if not self.fernet:
            self._init_fernet()
        return self.fernet

    def encrypt(self, text: str) -> str:
        if text is None:
            return ""
        fernet = self._ensure_fernet()
        return fernet.encrypt(text.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text:
            return ""
        fernet = self._ensure_fernet()
        try:
            return fernet.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
        except Exception:
            return "[Decryption Failed]"

crypto = CryptoManager()
