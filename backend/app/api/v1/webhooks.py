"""
Webhooks endpoint.
POST /api/v1/webhooks/register — register an external URL for fire alert webhooks

NOTE: Do NOT add `from __future__ import annotations` here (breaks slowapi-wrapped endpoints).
"""
import structlog
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.core.security import limiter
from app.models.webhook import WebhookRegistration

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = structlog.get_logger()


class WebhookRegisterRequest(BaseModel):
    url: HttpUrl
    secret: str | None = None  # used for HMAC-SHA256 signature on payloads


class WebhookRegisterResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    url: str
    message: str


@router.post(
    "/register",
    response_model=WebhookRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a webhook URL for fire alerts",
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("5/minute")
async def register_webhook(
    request: Request,  # required by slowapi
    body: WebhookRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> WebhookRegisterResponse:
    """
    Register an external webhook URL to receive fire alert payloads.
    Payloads are signed with HMAC-SHA256 using the provided secret.
    Header: X-Aero-Flare-Signature: sha256=<hex>
    """
    webhook = WebhookRegistration(
        url=str(body.url),
        secret=body.secret,
        is_active=True,
    )
    db.add(webhook)
    await db.flush()

    logger.info("webhook_registered", url=str(body.url), webhook_id=str(webhook.id))
    return WebhookRegisterResponse(
        id=str(webhook.id),
        url=str(body.url),
        message="Webhook registered. You will receive POST requests for fire alerts.",
    )
