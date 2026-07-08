import logging
from integrations.base.interfaces import BaseHRISProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class GreenhouseProvider(BaseHRISProvider):
    def provision_employee(self, employee_data: dict, credentials: dict) -> dict:
        raise NotImplementedError("Greenhouse provider does not support outbound employee provisioning")

    def import_candidates(self, credentials: dict) -> list:
        logger.info("Executing mock Greenhouse import")
        return [
            {
                "first_name": "Alice",
                "last_name": "Greenhouse",
                "email": "alice.gh@example.com",
                "phone": "555-0192",
                "job_title": "Backend Engineer",
                "department": "Engineering",
                "source": "Greenhouse"
            },
            {
                "first_name": "Bob",
                "last_name": "Greenhouse",
                "email": "bob.gh@example.com",
                "phone": "555-0193",
                "job_title": "DevOps Specialist",
                "department": "Infrastructure",
                "source": "Greenhouse"
            }
        ]


# Register
IntegrationRegistry.register("hris", "greenhouse", GreenhouseProvider)
