import base64
import os
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class SecretVaultService:
    """
    Implements AES-GCM-256 key encryption and decryption abstraction.
    Retrieves a system master key variable to wrap and unwrap sensitive parameters.
    """
    def __init__(self):
        # Retrieve master key, fallback in development
        raw_key = os.getenv("SECRET_VAULT_KEY", "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAEAAACF")
        self.master_key = raw_key.encode("utf-8")[:32]
        if len(self.master_key) < 32:
            self.master_key = self.master_key.ljust(32, b"\0")
        self.current_key_version = "v1"

    def encrypt_secret(self, secret_text: str) -> str:
        """Encrypts plain text and outputs base64 serialized JSON containing IV, Ciphertext, and AuthTag."""
        if not secret_text:
            return ""
        aesgcm = AESGCM(self.master_key)
        iv = os.urandom(12)
        encrypted_bytes = aesgcm.encrypt(iv, secret_text.encode("utf-8"), None)
        
        # GCM has 16-byte authentication tag at the end of encrypted bytes
        ciphertext = encrypted_bytes[:-16]
        tag = encrypted_bytes[-16:]

        payload = {
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            "iv": base64.b64encode(iv).decode("utf-8"),
            "tag": base64.b64encode(tag).decode("utf-8"),
            "key_version": self.current_key_version
        }
        return json.dumps(payload)

    def decrypt_secret(self, encrypted_json: str) -> str:
        """Decrypts AES-GCM JSON payload and returns the original plain text."""
        if not encrypted_json:
            return ""
        
        try:
            payload = json.loads(encrypted_json)
        except Exception as e:
            raise ValueError(f"Malformed encrypted payload: {str(e)}")

        if not isinstance(payload, dict) or "ciphertext" not in payload or "iv" not in payload or "tag" not in payload:
            raise ValueError("Malformed encrypted payload: missing required fields")

        key_version = payload.get("key_version", "v1")
        if key_version not in ("v1", "v2"): # support compatibility with rotation versions
            raise ValueError(f"Unsupported key version: {key_version}")

        try:
            ciphertext = base64.b64decode(payload["ciphertext"])
            iv = base64.b64decode(payload["iv"])
            tag = base64.b64decode(payload["tag"])
        except Exception as e:
            raise ValueError(f"Failed to base64 decode payload components: {str(e)}")

        try:
            aesgcm = AESGCM(self.master_key)
            # Reconstruct full ciphertext with the auth tag appended
            full_encrypted = ciphertext + tag
            decrypted_bytes = aesgcm.decrypt(iv, full_encrypted, None)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Decryption failed (possibly invalid key or corrupted data): {str(e)}")

