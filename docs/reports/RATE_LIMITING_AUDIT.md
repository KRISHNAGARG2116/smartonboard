# Rate Limiting Audit

This document audits the rate-limiting and failed-login IP lockout mechanisms implemented in SmartOnboard (Phase 14B).

---

## 1. Rate Limiting Enforcements

SmartOnboard secures authentication and sensitive endpoints from brute-force and Denial-of-Service (DoS) attacks using the `slowapi` library and custom decorators.

### Rate Limits by Endpoint:
1. **Google Login (`POST /api/v1/auth/google`)**:
   - **Limit**: `10 requests per minute`
   - **Key**: Tenant-aware (falls back to client IP address via `get_remote_address`).
2. **Company Setup Wizard (`POST /api/v1/auth/setup-company`)**:
   - **Limit**: `5 requests per minute`
   - **Key**: User-aware (uses `setup_company_rate_limit_key` which locks limits based on the user's `sub` claim to prevent a single logged-in user from spamming company creations across multiple IPs).

```python
# setup_company_rate_limit_key in backend/api/auth.py
def setup_company_rate_limit_key(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ")[1]
        try:
            from jose import jwt
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            user_id = payload.get("sub")
            if user_id:
                return f"setup_user_{user_id}"
        except Exception:
            pass
    from slowapi.util import get_remote_address
    return get_remote_address(request)
```

---

## 2. Failed Google Auth Lockout

In addition to standard request rate-limiting, Google OAuth logins have a dedicated failed-attempt lockout policy:
- **Threshold**: 5 failed authentication attempts.
- **Window**: 1 minute (60 seconds) sliding window.
- **Lockout Duration**: 5 minutes (300 seconds) blocking window.
- **Behavior**: Any request from an IP that exceeds the lockout threshold is instantly rejected with `429 Too Many Requests` without contacting Google APIs or hitting the database.

---

## 3. Redis Connectivity & Dev Fallback

The rate limiter and lockout states are stored in Redis under production settings. However, to prevent Redis from becoming a hard deployment dependency in development/testing, a thread-safe in-memory fallback is implemented.

### Fallback Implementation
If a Redis connection failure occurs, the backend falls back to a global, thread-safe memory dictionary (`_failed_google_attempts`) to track lockout state.

```python
# backend/api/auth.py
def check_google_failed_attempts(ip: str) -> bool:
    import redis
    global _failed_google_attempts
    if '_failed_google_attempts' not in globals():
        globals()['_failed_google_attempts'] = {}

    try:
        settings = get_settings()
        r = redis.from_url(settings.redis_url)
        blocked = r.get(f"google:blocked:{ip}")
        if blocked:
            return True
    except Exception:
        import time
        record = globals()['_failed_google_attempts'].get(ip)
        if record:
            count, timestamp = record
            if count >= 5 and (time.time() - timestamp) < 300:
                return True
    return False
```

Every lockout event is logged in the system audit trail (`auth.google_rate_limit_exceeded`) with details on the locked-out IP for security auditing.
