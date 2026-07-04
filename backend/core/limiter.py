from fastapi import Request
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.config import get_settings


def tenant_rate_limit_key(request: Request) -> str:
    """Return a rate-limiting key that is tenant-aware if a valid JWT is present, or falls back to IP address."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ")[1]
        try:
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            company_id = payload.get("company_id")
            if company_id:
                return f"tenant_{company_id}"
        except JWTError:
            pass
    
    # Fallback to remote IP address
    return get_remote_address(request)


# Initialize global rate limiter using tenant-aware key function
limiter = Limiter(key_func=tenant_rate_limit_key)


def recruiter_rate_limit_key(request: Request) -> str:
    """Return a rate-limiting key that is recruiter-aware if a valid JWT is present, or falls back to IP."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ")[1]
        try:
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            user_id = payload.get("sub")
            if user_id:
                return f"recruiter_{user_id}"
        except JWTError:
            pass
    
    # Fallback to remote IP address
    return get_remote_address(request)

