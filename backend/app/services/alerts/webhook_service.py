"""
Webhook dispatcher — POSTs alert payloads to registered external URLs.
Payloads signed with HMAC-SHA256 for authenticity verification.
FR-13: Webhook alert dispatch.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import WebhookRegistration

logger = structlog.get_logger()

_WEBHOOK_TIMEOUT = 10.0


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Return HMAC-SHA256 hex digest of the payload using the webhook secret."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


async def dispatch_webhooks(
    event_id: str,
    payload: dict,
    db: AsyncSession,
) -> int:
    """
    POST alert payload to all active registered webhooks.
    Signs each request with X-Aero-Flare-Signature: sha256=<hex>.
    Failures are logged but do NOT block Telegram delivery.

    Returns:
        Count of successful deliveries.
    """
    result = await db.execute(
        select(WebhookRegistration).where(WebhookRegistration.is_active == True)  # noqa: E712
    )
    webhooks = result.scalars().all()

    if not webhooks:
        return 0

    payload_bytes = json.dumps(payload, default=str).encode("utf-8")
    success_count = 0

    async with httpx.AsyncClient(timeout=_WEBHOOK_TIMEOUT) as client:
        for webhook in webhooks:
            headers = {
                "Content-Type": "application/json",
                "X-Aero-Flare-Event-Id": str(event_id),
            }
            if webhook.secret:
                sig = _sign_payload(payload_bytes, webhook.secret)
                headers["X-Aero-Flare-Signature"] = f"sha256={sig}"

            try:
                resp = await client.post(
                    webhook.url,
                    content=payload_bytes,
                    headers=headers,
                )
                resp.raise_for_status()
                success_count += 1
                logger.info(
                    "webhook_delivered",
                    webhook_id=str(webhook.id),
                    url=webhook.url,
                    status=resp.status_code,
                )
            except Exception as e:
                logger.warning(
                    "webhook_delivery_failed",
                    webhook_id=str(webhook.id),
                    url=webhook.url,
                    error=str(e),
                )

    logger.info(
        "webhook_dispatch_complete",
        event_id=str(event_id),
        total=len(webhooks),
        success=success_count,
    )
    return success_count
