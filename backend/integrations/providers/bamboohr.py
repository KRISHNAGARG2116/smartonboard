import logging
import uuid
import time
from integrations.base.interfaces import BaseHRISProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class BambooHRProvider(BaseHRISProvider):
    def provision_employee(self, employee_data: dict, credentials: dict) -> dict:
        if "api_key" not in credentials or "subdomain" not in credentials:
            raise ValueError("Invalid BambooHR credentials: API Key and Subdomain required")

        start_time = time.time()
        time.sleep(0.05)  # simulate API latency
        latency_ms = (time.time() - start_time) * 1000

        if credentials.get("api_key") == "invalid_key":
            raise ValueError("BambooHR Authentication Failed: Invalid API Key")

        hris_id = f"BAMBOO-EMP-{uuid.uuid4().hex[:8].upper()}"
        return {
            "hris_id": hris_id,
            "latency_ms": latency_ms,
            "payload": employee_data
        }

    def import_candidates(self, credentials: dict) -> list:
        # Mock Greenhouse/Lever-style import for testing
        return [
            {"email": "bamboo.import1@example.com", "full_name": "Bamboo Import One", "job_title": "Software Engineer", "source": "BambooHR"},
            {"email": "bamboo.import2@example.com", "full_name": "Bamboo Import Two", "job_title": "Product Manager", "source": "BambooHR"}
        ]


# Register
IntegrationRegistry.register("hris", "bamboohr", BambooHRProvider)
