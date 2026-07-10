import abc
import os
import base64
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


class KeyManagementService(abc.ABC):
    @abc.abstractmethod
    def encrypt_dek(self, dek: bytes) -> bytes:
        """Encrypts a Data Encryption Key (DEK) using the master KEK."""
        pass

    @abc.abstractmethod
    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        """Decrypts an encrypted Data Encryption Key (DEK) using the master KEK."""
        pass


class LocalEnvKeyManagementService(KeyManagementService):
    """
    Local environment Key Management Service storing KEK in config.
    Can be replaced with AWS KMS / HashiCorp Vault without modifying envelope logic.
    """
    def __init__(self):
        kek_b64 = os.getenv("MASTER_KEK", "YV92ZXJ5X3NlY3VyZV9tYXN0ZXJfa2VrX2tleV8zMmI=")
        self.kek = base64.b64decode(kek_b64)

    def encrypt_dek(self, dek: bytes) -> bytes:
        # Envelope encryption of DEK using master KEK
        aesgcm = AESGCM(self.kek)
        nonce = os.urandom(12)
        # Encrypt DEK
        encrypted = aesgcm.encrypt(nonce, dek, None)
        return nonce + encrypted

    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        aesgcm = AESGCM(self.kek)
        nonce = encrypted_dek[:12]
        ciphertext = encrypted_dek[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)


# Pluggable KMS factory
def get_kms_provider() -> KeyManagementService:
    # Pluggable backends: 'local', 'aws', 'hashicorp_vault'
    return LocalEnvKeyManagementService()


class EnvelopeEncryptionService:
    @classmethod
    def encrypt_secret(cls, plaintext: str, kms: KeyManagementService = None) -> Dict[str, str]:
        """
        Encrypts a secret using AES-256-GCM envelope encryption.
        Generates a unique DEK per secret, encrypts it with the KEK, and encrypts the payload.
        """
        if kms is None:
            kms = get_kms_provider()
            
        # 1. Generate unique 256-bit DEK
        dek = AESGCM.generate_key(bit_length=256)
        
        # 2. Encrypt plaintext payload with DEK
        aesgcm = AESGCM(dek)
        nonce = os.urandom(12)
        encrypted_payload = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        
        # 3. Encrypt DEK with KEK
        encrypted_dek = kms.encrypt_dek(dek)
        
        return {
            "encrypted_data": base64.b64encode(encrypted_payload).decode("utf-8"),
            "encrypted_dek": base64.b64encode(encrypted_dek).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8")
        }

    @classmethod
    def decrypt_secret(cls, payload: Dict[str, str], kms: KeyManagementService = None) -> str:
        """
        Decrypts an envelope-encrypted secret.
        Decrypts the DEK using KEK, then decrypts payload.
        """
        if kms is None:
            kms = get_kms_provider()
            
        encrypted_payload = base64.b64decode(payload["encrypted_data"])
        encrypted_dek = base64.b64decode(payload["encrypted_dek"])
        nonce = base64.b64decode(payload["nonce"])
        
        # 1. Decrypt DEK using KEK
        dek = kms.decrypt_dek(encrypted_dek)
        
        # 2. Decrypt payload using DEK
        aesgcm = AESGCM(dek)
        decrypted = aesgcm.decrypt(nonce, encrypted_payload, None)
        
        return decrypted.decode("utf-8")


class SecretsInventoryService:
    """Manages tracking, versions, and rotation intervals of encrypted secrets."""
    _INVENTORY: Dict[str, Dict[str, Any]] = {
        "smtp_credentials": {
            "secret_type": "SMTP Config",
            "version": 1,
            "last_rotated": (datetime.now(timezone.utc) - timedelta(days=45)).isoformat(),
            "rotation_interval_days": 90,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=45)).isoformat()
        },
        "calendar_oauth": {
            "secret_type": "OAuth Credentials",
            "version": 2,
            "last_rotated": (datetime.now(timezone.utc) - timedelta(days=95)).isoformat(),
            "rotation_interval_days": 90,
            "expiry": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()  # Overdue
        }
    }

    @classmethod
    def get_inventory(cls) -> Dict[str, Dict[str, Any]]:
        return cls._INVENTORY

    @classmethod
    def check_rotation_health(cls) -> List[Dict[str, Any]]:
        """Returns alerts for credentials that are expiring or overdue for rotation."""
        alerts = []
        now = datetime.now(timezone.utc)
        
        for name, info in cls._INVENTORY.items():
            expiry = datetime.fromisoformat(info["expiry"])
            last_rotated = datetime.fromisoformat(info["last_rotated"])
            rotation_due = last_rotated + timedelta(days=info["rotation_interval_days"])
            
            if now > expiry:
                alerts.append({
                    "secret": name,
                    "type": "Secret Expired",
                    "severity": "Critical",
                    "details": f"Credentials expired on {expiry.isoformat()}"
                })
            elif now > rotation_due:
                alerts.append({
                    "secret": name,
                    "type": "Rotation Overdue",
                    "severity": "High",
                    "details": f"Rotation scheduled on {rotation_due.isoformat()} is overdue."
                })
            elif expiry - now < timedelta(days=7):
                alerts.append({
                    "secret": name,
                    "type": "Expiring Soon",
                    "severity": "Medium",
                    "details": f"Credentials will expire in less than 7 days ({expiry.isoformat()})"
                })
                
        return alerts
