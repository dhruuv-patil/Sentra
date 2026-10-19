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

    def encrypt(self, text: str) -> str:
        if not self.fernet:
            return "[Encryption Disabled]"
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        if not self.fernet:
            return "[Decryption Key Missing]"
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except Exception:
            return "[Decryption Failed]"

crypto = CryptoManager()
