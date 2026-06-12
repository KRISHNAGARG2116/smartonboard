import logging
from google.oauth2 import id_token
from google.auth.transport import requests

logger = logging.getLogger("smartonboard.auth_providers.google")


def verify_google_id_token(token: str, client_id: str) -> dict:
    """Verifies a Google ID token and returns its decoded payload.

    Raises ValueError if the token is invalid.
    """
    try:
        # verify_oauth2_token verifies signature, expiration, and audience/client_id
        payload = id_token.verify_oauth2_token(token, requests.Request(), client_id)
        return payload
    except Exception as e:
        logger.error(f"Google ID token verification failed: {e}")
        raise ValueError(f"Invalid Google ID token: {e}")
