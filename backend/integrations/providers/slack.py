import logging
import httpx
from integrations.base.interfaces import BaseChatProvider
from integrations.base.registry import IntegrationRegistry

logger = logging.getLogger(__name__)

class SlackChatProvider(BaseChatProvider):
    def send_message(self, webhook_url: str, message: str) -> bool:
        logger.info(f"Sending Slack webhook alert: {message}")
        
        # Test mode checks
        if "mock-slack" in webhook_url or "localhost" in webhook_url:
            logger.info("Mock Slack message posted successfully.")
            return True

        try:
            payload = {"text": message}
            response = httpx.post(webhook_url, json=payload, timeout=5.0)
            if response.status_code == 200:
                return True
            logger.error(f"Slack webhook failed: HTTP {response.status_code} - {response.text}")
            return False
        except Exception as e:
            logger.error(f"Slack webhook exception: {str(e)}")
            return False


# Register
IntegrationRegistry.register("chat", "slack", SlackChatProvider)
