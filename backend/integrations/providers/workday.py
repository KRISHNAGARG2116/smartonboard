import logging
import uuid
import time
from integrations.base.interfaces import BaseHRISProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class WorkdayProvider(BaseHRISProvider):
    def provision_employee(self, employee_data: dict, credentials: dict) -> dict:
        if "tenant_url" not in credentials or "username" not in credentials or "password" not in credentials:
            raise ValueError("Invalid Workday credentials: Tenant URL, Username, and Password required")

        start_time = time.time()
        time.sleep(0.05)
        latency_ms = (time.time() - start_time) * 1000

        if credentials.get("password") == "invalid_password":
            raise ValueError("Workday Security Authentication Failed: Bad Username/Password envelope")

        hris_id = f"WD-EMP-{uuid.uuid4().hex[:8].upper()}"
        return {
            "hris_id": hris_id,
            "latency_ms": latency_ms,
            "payload": employee_data
        }

    def import_candidates(self, credentials: dict) -> list:
        return [
            {"email": "wd.import1@example.com", "full_name": "Workday Import One", "job_title": "ML Engineer", "source": "Workday"},
        ]


# Register
IntegrationRegistry.register("hris", "workday", WorkdayProvider)
