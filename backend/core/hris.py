import abc
import base64
import hashlib
import json
import logging
import os
import time
import uuid
from typing import Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.vault import SecretVaultService
from models import Employee, CompanyHRISIntegration, HRISFieldMapping

logger = logging.getLogger("app")


class HRISCredentialCrypto:
    """
    Implements AES-256-GCM envelope encryption for sensitive HRIS configurations:
    - Generates a per-tenant Data Encryption Key (DEK).
    - Encrypts credentials plaintext using the DEK.
    - Encrypts the DEK using the system master key (Key Encryption Key - KEK)
      via the SecretVaultService and stores it alongside the payload.
    """
    @staticmethod
    def encrypt_credentials(credentials: dict, KEK_service: SecretVaultService) -> str:
        """
        Encrypts credentials with a brand new DEK, then encrypts the DEK with KEK.
        Returns a single serialized JSON containing the enveloped payload.
        """
        credentials_str = json.dumps(credentials)

        # 1. Generate random 256-bit DEK (32 bytes)
        dek = os.urandom(32)

        # 2. Encrypt credentials with DEK using AES-GCM
        aesgcm_dek = AESGCM(dek)
        iv = os.urandom(12)
        encrypted_bytes = aesgcm_dek.encrypt(iv, credentials_str.encode("utf-8"), None)
        ciphertext = encrypted_bytes[:-16]
        tag = encrypted_bytes[-16:]

        # 3. Encrypt the DEK with KEK using AES-GCM via KEK_service
        # To do this cleanly, KEK_service's master_key is used
        aesgcm_kek = AESGCM(KEK_service.master_key)
        dek_iv = os.urandom(12)
        encrypted_dek_bytes = aesgcm_kek.encrypt(dek_iv, dek, None)
        encrypted_dek = encrypted_dek_bytes[:-16]
        dek_tag = encrypted_dek_bytes[-16:]

        # 4. Serialize all components to JSON
        envelope = {
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            "iv": base64.b64encode(iv).decode("utf-8"),
            "tag": base64.b64encode(tag).decode("utf-8"),
            "encrypted_dek": base64.b64encode(encrypted_dek).decode("utf-8"),
            "dek_iv": base64.b64encode(dek_iv).decode("utf-8"),
            "dek_tag": base64.b64encode(dek_tag).decode("utf-8"),
            "key_version": KEK_service.current_key_version
        }
        return json.dumps(envelope)

    @staticmethod
    def decrypt_credentials(encrypted_envelope_json: str, KEK_service: SecretVaultService) -> dict:
        """
        Decrypts the DEK using the KEK, then decrypts the original payload using the recovered DEK.
        """
        if not encrypted_envelope_json:
            return {}

        try:
            envelope = json.loads(encrypted_envelope_json)
        except Exception as e:
            raise ValueError(f"Malformed encrypted envelope: {str(e)}")

        required_fields = ["ciphertext", "iv", "tag", "encrypted_dek", "dek_iv", "dek_tag"]
        if not all(field in envelope for field in required_fields):
            # Fallback to direct vault decryption for backwards compatibility if needed
            try:
                decrypted = KEK_service.decrypt_secret(encrypted_envelope_json)
                return json.loads(decrypted)
            except Exception:
                raise ValueError("Malformed encrypted envelope: missing required fields")

        try:
            # 1. Base64 decode all components
            ciphertext = base64.b64decode(envelope["ciphertext"])
            iv = base64.b64decode(envelope["iv"])
            tag = base64.b64decode(envelope["tag"])
            encrypted_dek = base64.b64decode(envelope["encrypted_dek"])
            dek_iv = base64.b64decode(envelope["dek_iv"])
            dek_tag = base64.b64decode(envelope["dek_tag"])
        except Exception as e:
            raise ValueError(f"Failed to base64 decode envelope components: {str(e)}")

        # 2. Decrypt the DEK using KEK
        try:
            aesgcm_kek = AESGCM(KEK_service.master_key)
            full_encrypted_dek = encrypted_dek + dek_tag
            dek = aesgcm_kek.decrypt(dek_iv, full_encrypted_dek, None)
        except Exception as e:
            raise ValueError(f"Failed to decrypt DEK envelope: {str(e)}")

        # 3. Decrypt credentials using recovered DEK
        try:
            aesgcm_dek = AESGCM(dek)
            full_encrypted_creds = ciphertext + tag
            decrypted_creds_bytes = aesgcm_dek.decrypt(iv, full_encrypted_creds, None)
            return json.loads(decrypted_creds_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials payload: {str(e)}")


class ProviderTransformationEngine:
    """
    Dedicated field mapping and value transformation engine.
    Ensures that payloads match dynamic tenant configurations or default fallbacks.
    """
    DEFAULT_MAPPINGS = {
        "bamboohr": {
            "email": "workEmail",
            "full_name": "fullName",
            "phone": "mobilePhone",
            "job_title": "jobTitle",
            "department": "department",
            "employment_type": "employmentType"
        },
        "hibob": {
            "email": "email",
            "full_name": "fullName",
            "phone": "phone",
            "job_title": "title",
            "department": "department",
            "employment_type": "employmentType"
        },
        "gusto": {
            "email": "email",
            "full_name": "fullName",
            "phone": "phone_number",
            "job_title": "title",
            "department": "department",
            "employment_type": "employment_type"
        },
        "workday": {
            "email": "email_address",
            "full_name": "first_last_name",
            "phone": "phone_number",
            "job_title": "job_profile",
            "department": "supervisory_organization",
            "employment_type": "time_type"
        }
    }

    @classmethod
    def transform_employee(cls, db: Session, employee: Employee, provider: str) -> dict[str, Any]:
        """
        Maps local Employee fields to the HRIS provider fields, checking for custom database overrides.
        """
        provider_clean = provider.lower()
        
        # 1. Fetch custom mappings from database if exists
        stmt = select(HRISFieldMapping).where(
            HRISFieldMapping.company_id == employee.company_id,
            HRISFieldMapping.provider == provider_clean
        )
        custom_mappings = db.scalars(stmt).all()

        mapping_dict = {}
        if custom_mappings:
            for m in custom_mappings:
                mapping_dict[m.local_field] = m.provider_field
        else:
            # Fallback to defaults
            mapping_dict = cls.DEFAULT_MAPPINGS.get(provider_clean, {}).copy()

        # 2. Extract employee field values
        local_data = {
            "email": employee.email,
            "full_name": employee.full_name,
            "phone": employee.phone,
            "job_title": employee.job_title,
            "department": employee.department,
            "employment_type": employee.employment_type
        }

        # 3. Transform values based on mapping dict
        provider_payload = {}
        for local_f, provider_f in mapping_dict.items():
            val = local_data.get(local_f)
            provider_payload[provider_f] = val

        # 4. Specific provider transformation adaptations (e.g., splitting names)
        # Check if first_name / last_name mapping overrides are set or if provider expects it
        if provider_clean in ("bamboohr", "gusto", "hibob", "workday"):
            # If full name is mapped, but the adapter needs first/last split:
            names = employee.full_name.split(" ", 1)
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else ""

            if provider_clean == "gusto":
                provider_payload["first_name"] = first_name
                provider_payload["last_name"] = last_name
            elif provider_clean == "bamboohr":
                provider_payload["firstName"] = first_name
                provider_payload["lastName"] = last_name
            elif provider_clean == "hibob":
                provider_payload["firstName"] = first_name
                provider_payload["lastName"] = last_name
            elif provider_clean == "workday":
                provider_payload["first_name"] = first_name
                provider_payload["last_name"] = last_name

        return provider_payload


class BaseHRISAdapter(abc.ABC):
    """
    Abstract interface for all HRIS synchronization adapters.
    """
    def __init__(self, db: Session, integration: CompanyHRISIntegration):
        self.db = db
        self.integration = integration
        vault = SecretVaultService()
        self.credentials = HRISCredentialCrypto.decrypt_credentials(
            integration.credentials_encrypted, vault
        )

    @abc.abstractmethod
    def provision_employee(self, employee: Employee) -> dict[str, Any]:
        """
        Compiles the mapped payload and pushes to the HRIS mock endpoint.
        Returns a dict containing {"hris_id": str, "latency_ms": float, "payload": dict}.
        """
        pass


class BambooHRAdapter(BaseHRISAdapter):
    """
    Adapter for BambooHR integration.
    """
    def provision_employee(self, employee: Employee) -> dict[str, Any]:
        # Validate credentials
        if "api_key" not in self.credentials or "subdomain" not in self.credentials:
            raise ValueError("Invalid BambooHR credentials: API Key and Subdomain required")

        start_time = time.time()
        
        # 1. Run mapping transformation
        payload = ProviderTransformationEngine.transform_employee(self.db, employee, "bamboohr")

        # 2. Simulate API Network Dispatch
        time.sleep(0.1) # Network latency simulation
        latency_ms = (time.time() - start_time) * 1000

        # Simulate dynamic failure check if credential is "invalid_key" for test injection
        if self.credentials.get("api_key") == "invalid_key":
            raise ValueError("BambooHR Authentication Failed: Invalid API Key")

        hris_id = f"BAMBOO-EMP-{uuid.uuid4().hex[:8].upper()}"
        return {
            "hris_id": hris_id,
            "latency_ms": latency_ms,
            "payload": payload
        }


class HiBobAdapter(BaseHRISAdapter):
    """
    Adapter for HiBob integration.
    """
    def provision_employee(self, employee: Employee) -> dict[str, Any]:
        if "service_id" not in self.credentials or "service_token" not in self.credentials:
            raise ValueError("Invalid HiBob credentials: Service ID and Token required")

        start_time = time.time()
        payload = ProviderTransformationEngine.transform_employee(self.db, employee, "hibob")
        
        time.sleep(0.15)
        latency_ms = (time.time() - start_time) * 1000

        if self.credentials.get("service_token") == "invalid_token":
            raise ValueError("HiBob Access Forbidden: Invalid Service Token")

        hris_id = f"HIBOB-EMP-{uuid.uuid4().hex[:8].upper()}"
        return {
            "hris_id": hris_id,
            "latency_ms": latency_ms,
            "payload": payload
        }


class GustoAdapter(BaseHRISAdapter):
    """
    Adapter for Gusto payroll integration.
    """
    def provision_employee(self, employee: Employee) -> dict[str, Any]:
        if "client_id" not in self.credentials or "client_secret" not in self.credentials:
            raise ValueError("Invalid Gusto credentials: Client ID and Secret required")

        start_time = time.time()
        payload = ProviderTransformationEngine.transform_employee(self.db, employee, "gusto")
        
        time.sleep(0.08)
        latency_ms = (time.time() - start_time) * 1000

        if self.credentials.get("client_secret") == "invalid_secret":
            raise ValueError("Gusto Token Rejected: Invalid client secret configuration")

        hris_id = f"GUSTO-EMP-{uuid.uuid4().hex[:8].upper()}"
        return {
            "hris_id": hris_id,
            "latency_ms": latency_ms,
            "payload": payload
        }


class WorkdayAdapter(BaseHRISAdapter):
    """
    Adapter for Workday soap integration functional area.
    """
    def provision_employee(self, employee: Employee) -> dict[str, Any]:
        if "tenant_url" not in self.credentials or "username" not in self.credentials or "password" not in self.credentials:
            raise ValueError("Invalid Workday credentials: Tenant URL, Username, and Password required")

        start_time = time.time()
        payload = ProviderTransformationEngine.transform_employee(self.db, employee, "workday")
        
        time.sleep(0.2)
        latency_ms = (time.time() - start_time) * 1000

        if self.credentials.get("password") == "invalid_password":
            raise ValueError("Workday Security Authentication Failed: Bad Username/Password envelope")

        hris_id = f"WD-EMP-{uuid.uuid4().hex[:8].upper()}"
        return {
            "hris_id": hris_id,
            "latency_ms": latency_ms,
            "payload": payload
        }


class HRISAdapterFactory:
    """
    Factory creating concrete adapters based on provider keys.
    """
    _ADAPTERS = {
        "bamboohr": BambooHRAdapter,
        "hibob": HiBobAdapter,
        "gusto": GustoAdapter,
        "workday": WorkdayAdapter
    }

    @classmethod
    def get_adapter(cls, db: Session, integration: CompanyHRISIntegration) -> BaseHRISAdapter:
        provider_clean = integration.provider.lower()
        adapter_class = cls._ADAPTERS.get(provider_clean)
        if not adapter_class:
            raise ValueError(f"Unsupported HRIS Provider: {integration.provider}")
        return adapter_class(db, integration)
