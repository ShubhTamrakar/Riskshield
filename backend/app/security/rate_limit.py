"""
Rate limiting using slowapi (Starlette-native, Redis-backed).

Limits:
  - POST /payments (critical path):           30 req/min per IP
  - GET /payments/{id}/investigate (LLM):     10 req/min per IP
  - POST /simulation/runs:                    20 req/min per IP
  - Global fallback:                          RATE_LIMIT_PER_MINUTE per IP

Degrades gracefully: if Redis is unavailable, requests are allowed through
with a warning log rather than hard-failing.
"""
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _get_remote_addr_safe(request):
    """Prefer X-Forwarded-For (set by reverse proxy), fall back to direct IP."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_remote_addr_safe,
    default_limits=["60/minute"],
    # slowapi picks up the Redis URL from the storage_uri parameter
    # Falls back to in-memory if not provided / unavailable
    storage_uri=None,  # overridden in main.py from settings
)
