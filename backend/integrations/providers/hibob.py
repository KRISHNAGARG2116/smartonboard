import logging
import uuid
import time
from integrations.base.interfaces import BaseHRISProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class HiBobProvider(BaseHRISProvider):
    def provision_employee(self, employee_data: dict, credentials: dict) -> dict:
        if "service_id" not in credentials or "service_token" not in credentials:
            raise ValueError("Invalid HiBob credentials: Service ID and Token required")

        start_time = time.time()
        time.sleep(0.05)
        latency_ms = (time.time() - start_time) * 1000

        if credentials.get("service_token") == "invalid_token":
            raise ValueError("HiBob Access Forbidden: Invalid Service Token")

        hris_id = f"HIBOB-EMP-{uuid.uuid4().hex[:8].upper()}"
        return {
            "hris_id": hris_id,
            "latency_ms": latency_ms,
            "payload": employee_data
        }

    def import_candidates(self, credentials: dict) -> list:
        return [
            {"email": "bob.import1@example.com", "full_name": "Bob Import One", "job_title": "Frontend Lead", "source": "HiBob"},
        ]


# Register
IntegrationRegistry.register("hris", "hibob", HiBobProvider)
