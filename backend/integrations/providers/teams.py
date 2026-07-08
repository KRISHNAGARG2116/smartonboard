import logging
import httpx
from integrations.base.interfaces import BaseChatProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class TeamsChatProvider(BaseChatProvider):
    def send_message(self, webhook_url: str, message: str) -> bool:
        logger.info(f"Sending Teams webhook alert: {message}")

        if "mock-teams" in webhook_url or "localhost" in webhook_url:
            logger.info("Mock Teams message posted successfully.")
            return True

        try:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "summary": "SmartOnboard Notification",
                "themeColor": "6c63ff",
                "sections": [{
                    "activityTitle": "SmartOnboard Notification",
                    "text": message
                }]
            }
            response = httpx.post(webhook_url, json=payload, timeout=5.0)
            if response.status_code == 200 or response.status_code == 201:
                return True
            logger.error(f"Teams webhook failed: HTTP {response.status_code} - {response.text}")
            return False
        except Exception as e:
            logger.error(f"Teams webhook exception: {str(e)}")
            return False


# Register
IntegrationRegistry.register("chat", "teams", TeamsChatProvider)
IntegrationRegistry.register("chat", "microsoft_teams", TeamsChatProvider)
