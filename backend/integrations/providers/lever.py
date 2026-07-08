import logging
from integrations.base.interfaces import BaseHRISProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class LeverProvider(BaseHRISProvider):
    def provision_employee(self, employee_data: dict, credentials: dict) -> dict:
        raise NotImplementedError("Lever provider does not support outbound employee provisioning")

    def import_candidates(self, credentials: dict) -> list:
        logger.info("Executing mock Lever import")
        return [
            {
                "first_name": "Charlie",
                "last_name": "Lever",
                "email": "charlie.lever@example.com",
                "phone": "555-0200",
                "job_title": "Product Owner",
                "department": "Product Management",
                "source": "Lever"
            },
            {
                "first_name": "Diana",
                "last_name": "Lever",
                "email": "diana.lever@example.com",
                "phone": "555-0201",
                "job_title": "UX Researcher",
                "department": "Design",
                "source": "Lever"
            }
        ]


# Register
IntegrationRegistry.register("hris", "lever", LeverProvider)
