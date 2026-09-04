"""
Secure headers middleware.

Adds security-relevant HTTP response headers on every response.
These headers prevent a range of browser-based attacks.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # HSTS — only useful over HTTPS but harmless in dev
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Minimal CSP for an API (no HTML served)
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        # Don't send the Referer header to other origins
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Disable browser features not needed by an API
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response
