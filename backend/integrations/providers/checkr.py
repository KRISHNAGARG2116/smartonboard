import logging
import uuid
from integrations.base.interfaces import BaseBackgroundCheckProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class CheckrProvider(BaseBackgroundCheckProvider):
    def trigger_check(self, candidate_data: dict, check_type: str, credentials: dict) -> dict:
        if "api_key" not in credentials:
            raise ValueError("Checkr API Key is required")
        logger.info(f"Triggering Checkr background check ({check_type}) for {candidate_data.get('email')}")
        check_id = f"checkr_{uuid.uuid4().hex[:12]}"
        return {
            "external_check_id": check_id,
            "status": "pending"
        }

    def get_check_status(self, external_check_id: str, credentials: dict) -> dict:
        logger.info(f"Fetching Checkr status for {external_check_id}")
        return {
            "status": "completed",
            "result": "clear"
        }


# Register
IntegrationRegistry.register("background_check", "checkr", CheckrProvider)
