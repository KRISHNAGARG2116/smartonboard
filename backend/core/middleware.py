import ipaddress
import json
import logging
import os
import uuid
import base64
from jose import jwt
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select

from core.config import get_settings
from core.audit import log_audit_event
from db.session import SessionLocal
from models.enterprise import CompanyIPWhitelist

logger = logging.getLogger("app")


def is_trusted_proxy(ip_str: str, trusted_proxies_list: list[str]) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        for proxy in trusted_proxies_list:
            if "/" in proxy:
                if ip in ipaddress.ip_network(proxy):
                    return True
            else:
                if ip == ipaddress.ip_address(proxy):
                    return True
    except Exception:
        pass
    return False


def resolve_client_ip(request: Request, trusted_proxies_list: list[str]) -> str:
    socket_ip = request.client.host if request.client else "127.0.0.1"
    if socket_ip == "testclient":
        socket_ip = "127.0.0.1"

    # Check X-Forwarded-For header only if socket IP is a trusted load balancer/proxy
    if is_trusted_proxy(socket_ip, trusted_proxies_list):
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                return parts[0]

    return socket_ip


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 1. Bypass public-facing assets, scheduling availability, and global registration/login paths
        is_public = (
            path.startswith("/api/v1/auth/login") or
            path.startswith("/api/v1/auth/register") or
            path.startswith("/api/v1/auth/sso") or
            path.startswith("/api/v1/auth/oidc") or
            path.startswith("/api/v1/auth/calendars/callback") or
            (path.startswith("/api/v1/schedule/") and ("book" in path or "availability" in path))
        )

        if is_public:
            return await call_next(request)

        # 2. Extract company context from JWT Authorization header
        company_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            try:
                token = auth_header.split(" ")[1]
                settings = get_settings()
                payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
                company_id = payload.get("company_id")
            except Exception:
                pass

        # 3. If company ID is present, execute CIDR validations
        if company_id:
            db = SessionLocal()
            try:
                company_uuid = uuid.UUID(company_id)
                
                # Fetch active whitelist ranges
                stmt = select(CompanyIPWhitelist).where(
                    CompanyIPWhitelist.company_id == company_uuid,
                    CompanyIPWhitelist.is_active == True
                )
                whitelists = db.scalars(stmt).all()

                if whitelists:
                    # Resolve proxy-aware client IP
                    proxies_str = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1")
                    trusted_proxies = [p.strip() for p in proxies_str.split(",") if p.strip()]
                    client_ip_str = resolve_client_ip(request, trusted_proxies)
                    client_ip = ipaddress.ip_address(client_ip_str)

                    # Match client IP against whitelists
                    allowed = False
                    for wl in whitelists:
                        try:
                            if client_ip in ipaddress.ip_network(wl.cidr_block):
                                allowed = True
                                break
                        except Exception:
                            pass

                    if not allowed:
                        # Log lockout violation audit trail
                        log_audit_event(
                            db=db,
                            action="enterprise.ip_whitelist_violated",
                            actor_type="UNAUTHENTICATED",
                            company_id=company_uuid,
                            ip_address=client_ip_str,
                            user_agent=request.headers.get("user-agent"),
                            metadata={
                                "blocked_ip": client_ip_str,
                                "requested_url": str(request.url)
                            }
                        )
                        db.commit()

                        logger.warning(f"Access denied: client IP {client_ip_str} not whitelisted for company {company_id}")
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={"detail": f"Access denied: Your IP address ({client_ip_str}) is not whitelisted by your administrator."}
                        )
            except Exception as e:
                logger.error(f"Error in IPWhitelistMiddleware: {str(e)}")
            finally:
                db.close()

        response = await call_next(request)
        if hasattr(request.state, "quota_warning") and request.state.quota_warning:
            response.headers["X-Quota-Warning"] = request.state.quota_warning
        return response


class ContentSecurityPolicyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate CSP nonce
        nonce = base64.b64encode(os.urandom(16)).decode("utf-8")
        request.state.csp_nonce = nonce
        
        response = await call_next(request)
        
        csp_directives = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            f"img-src 'self' data: https:; "
            f"font-src 'self' https://fonts.gstatic.com; "
            f"connect-src 'self' https://api.groq.com; "
            f"frame-ancestors 'none'; "
            f"form-action 'self';"
        )
        
        response.headers["Content-Security-Policy"] = csp_directives
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Inject HTTP Strict Transport Security (HSTS)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        
        # Inject Permissions-Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


def sanitize_dict(d: dict) -> dict:
    import bleach
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, str):
            cleaned[k] = bleach.clean(v, tags=[], attributes={}, strip=True)
        elif isinstance(v, dict):
            cleaned[k] = sanitize_dict(v)
        elif isinstance(v, list):
            cleaned[k] = [
                bleach.clean(item, tags=[], attributes={}, strip=True) if isinstance(item, str)
                else (sanitize_dict(item) if isinstance(item, dict) else item)
                for item in v
            ]
        else:
            cleaned[k] = v
    return cleaned


class RequestSanitizationMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] in ("POST", "PUT", "PATCH"):
            headers = dict(scope.get("headers", []))
            content_type = headers.get(b"content-type", b"").decode("latin1")
            if "application/json" in content_type:
                body_parts = []
                more_body = True
                while more_body:
                    message = await receive()
                    body_parts.append(message.get("body", b""))
                    more_body = message.get("more_body", False)
                
                full_body = b"".join(body_parts)
                new_body = full_body
                if full_body:
                    try:
                        data = json.loads(full_body.decode("utf-8"))
                        sanitized_data = sanitize_dict(data)
                        new_body = json.dumps(sanitized_data).encode("utf-8")
                    except Exception:
                        pass
                
                # Update content-length header
                new_headers = []
                for k, v in scope.get("headers", []):
                    if k.lower() == b"content-length":
                        new_headers.append((k, str(len(new_body)).encode("ascii")))
                    else:
                        new_headers.append((k, v))
                scope["headers"] = new_headers
                
                async def new_receive():
                    return {
                        "type": "http.request",
                        "body": new_body,
                        "more_body": False
                    }
                
                await self.app(scope, new_receive, send)
                return
        
        await self.app(scope, receive, send)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
