from cryptography.fernet import Fernet
from core.config import config

class CryptoManager:
    def __init__(self):
        self.fernet = None
        if config.ENCRYPTION_KEY:
            try:
                self.fernet = Fernet(config.ENCRYPTION_KEY.encode())
            except Exception:
                print("Warning: Invalid ENCRYPTION_KEY provided.")

    def _ensure_fernet(self):
        if not self.fernet:
            import os
            key = os.getenv("ENCRYPTION_KEY") or config.ENCRYPTION_KEY
            if key:
                try:
                    self.fernet = Fernet(key.encode())
                except Exception:
                    pass
        return self.fernet

    def encrypt(self, text: str) -> str:
        fernet = self._ensure_fernet()
        if not fernet:
            return "[Encryption Disabled]"
        return fernet.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        fernet = self._ensure_fernet()
        if not fernet:
            return "[Decryption Key Missing]"
        try:
            return fernet.decrypt(encrypted_text.encode()).decode()
        except Exception:
            return "[Decryption Failed]"

crypto = CryptoManager()
