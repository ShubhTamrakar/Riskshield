"""
Idempotency utility.

Provides a dependency to check idempotency keys for critical endpoints (like POST /payments).
Keys are stored in Redis (with a TTL) if available, falling back to a no-op if Redis is down.
"""
import logging
from typing import Optional
from fastapi import Header, Request
import json
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis client initialization (lazy)
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test connection
            await _redis_client.ping()
        except Exception as e:
            logger.warning("Redis not available for idempotency: %s", e)
            _redis_client = None
    return _redis_client


async def check_idempotency(
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Check if the Idempotency-Key has been seen before.
    If yes, we could theoretically return the cached response.
    For now, we just log it and attach it to the request state.
    Real implementation would intercept the response and cache it.
    """
    request.state.idempotency_key = idempotency_key
    if not idempotency_key:
        return None

    r = await get_redis()
    if not r:
        return None
    
    key = f"idemp:{idempotency_key}"
    val = await r.get(key)
    if val:
        logger.info("Idempotency key hit: %s", idempotency_key)
        # Note: A real implementation would raise an HTTPException with the cached response
        # We simplify here for phase 8 demonstration
        return json.loads(val)
    
    return None


async def cache_idempotency_response(idempotency_key: str, response_data: dict, ttl: int = 86400):
    """Cache the successful response for an idempotency key."""
    if not idempotency_key:
        return
        
    r = await get_redis()
    if not r:
        return
        
    key = f"idemp:{idempotency_key}"
    try:
        await r.setex(key, ttl, json.dumps(response_data))
    except Exception as e:
        logger.warning("Failed to cache idempotency response: %s", e)
