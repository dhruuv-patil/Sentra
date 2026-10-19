import pytest
from core.crypto import crypto

def test_encryption_and_decryption():
    secret_text = "Highly confidential LLM audit log entry with private parameters."
    encrypted = crypto.encrypt(secret_text)
    
    # Must be encrypted and not equal to plaintext
    assert encrypted != secret_text
    assert encrypted != "[Encryption Disabled]"
    assert encrypted.startswith("gAAAAA")

    # Decrypt must restore exact original text
    decrypted = crypto.decrypt(encrypted)
    assert decrypted == secret_text
