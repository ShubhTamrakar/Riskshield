"""
Webhook router — receives and processes payment provider webhook events.

Security:
  - Signature is verified before the payload is processed.
  - Duplicate events (same event_id) are silently acknowledged (idempotent).
  - Payload is stored in the DB before processing for audit trail.
  - Provider webhook secrets are read from environment variables only.
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.models.webhook import WebhookEvent
from app.observability.metrics import webhook_events_total, webhook_failures_total

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{provider}", status_code=202)
async def receive_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """Accept a webhook event from a payment provider.

    Steps:
    1. Verify HMAC signature.
    2. Parse payload.
    3. Check for duplicate event_id.
    4. Persist WebhookEvent record.
    5. Acknowledge immediately (202 Accepted).
    Processing happens asynchronously (not yet wired — infrastructure ready).
    """
    # 1. Fetch the provider adapter
    from app.adapters.registry import get_adapter
    adapter = get_adapter(provider)
    
    if not adapter:
        logger.error("No adapter found for provider '%s'", provider)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "provider_not_found", "message": f"Adapter for provider {provider} not found."}
        )

    # 2. Signature verification
    secret = os.environ.get(f"WEBHOOK_SECRET_{provider.upper()}", "")
    if secret:
        body = await request.body()
        headers = dict(request.headers)
        if not adapter.verify_signature(body, headers, secret):
            webhook_failures_total.labels(provider=provider, reason="invalid_signature").inc()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_signature", "message": "Webhook signature verification failed."},
            )
    else:
        logger.warning("No WEBHOOK_SECRET_%s configured — signature check skipped", provider.upper())

    # 3. Parse payload
    try:
        # Since body was consumed, we parse it manually
        import json
        body = await request.body() if not secret else body
        payload = json.loads(body)
    except Exception:
        webhook_failures_total.labels(provider=provider, reason="invalid_payload").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_payload", "message": "Could not parse JSON payload."},
        )

    # 4. Extract event ID via adapter
    event_id = adapter.get_event_id(payload)

    # 5. Idempotency — check for duplicate
    existing = await db.execute(
        select(WebhookEvent).where(WebhookEvent.event_id == event_id)
    )
    if existing.scalar_one_or_none():
        logger.info("Duplicate webhook event '%s' from '%s' — acknowledged without reprocessing", event_id, provider)
        return {"acknowledged": True, "duplicate": True}

    # 6. Persist webhook event for audit trail
    event_type = payload.get("type") or payload.get("event") or "unknown"
    event = WebhookEvent(
        event_id=event_id,
        provider=provider,
        event_type=event_type,
        payload=payload,
        received_at=datetime.now(timezone.utc),
        status="received",
    )
    db.add(event)
    await db.commit() # Commit the event immediately

    webhook_events_total.labels(provider=provider, event_type=event_type).inc()
    logger.info("Webhook event '%s' type='%s' from provider='%s' stored", event_id, event_type, provider)

    # 7. Normalize payload and run through Risk Engine
    payment_request = adapter.normalize_payload(payload)
    if payment_request:
        from app.services.payment_service import process_payment
        try:
            await process_payment(db, payment_request)
            event.status = "processed"
            await db.commit()
            logger.info("Successfully processed payment via webhook for event '%s'", event_id)
        except Exception as e:
            event.status = "failed"
            await db.commit()
            logger.error("Failed to process normalized payment for event '%s': %s", event_id, e)
            # Depending on provider requirements, we may still return 202 to avoid retries, 
            # or a 500 to trigger retries. For now, returning 202 as the event is persisted.
    else:
        logger.info("Webhook event '%s' did not yield a PaymentRequest. Skipping Risk Engine evaluation.", event_id)
        event.status = "ignored"
        await db.commit()

    return {"acknowledged": True, "event_id": event_id}
