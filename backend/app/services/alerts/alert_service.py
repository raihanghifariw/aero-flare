"""
Alert Service — orchestrator for fire event alerting.

Pipeline:
  1. Dedup check   — skip if already alerted (alerted_at IS NOT NULL)
  2. Load triage + prediction for the event
  3. Geocode       — reverse-lookup human-readable location
  4. Format        — build canonical alert message
  5. Deliver       — Telegram + registered webhooks (concurrent)
  6. Mark alerted  — write alerted_at + ALERTED / ALERTED_FAILED status
  7. Audit log     — append-only record for every attempt
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.audit_log import EventAuditLog
from app.models.fire_event import FireEvent
from app.models.prediction import Prediction
from app.models.triage_report import TriageReport
from app.services.alerts.alert_formatter import format_alert_message
from app.services.alerts.dedup import is_already_alerted
from app.services.alerts.geocoder import reverse_geocode
from app.services.alerts.telegram_service import send_telegram_alert
from app.services.alerts.webhook_service import dispatch_webhooks

logger = logging.getLogger(__name__)


def should_send_alert(event: FireEvent, triage: TriageReport | None) -> tuple[bool, str]:
    """
    Operational Alert Routing Engine Standards:
      1. Exclude FALSE_POSITIVE and INDUSTRIAL_SOURCE entirely.
      2. Exclude low danger level (danger_level <= 1).
      3. FRP Threshold Standards:
         - 0 - 30 MW (Low): Skip alerting unless Level 4/5 CONFIRMED_FIRE.
         - 30 - 100 MW (Moderate): Alert if CONFIRMED_FIRE or PROBABLE_FIRE with danger_level >= 3.
         - 100 - 500 MW (High): Alert all active fires (danger_level >= 3).
         - > 500 MW (Extreme): Always alert.
    """
    if triage is None:
        frp = event.frp or 0.0
        if frp < 30.0:
            return False, "low_frp_untriaged"
        return True, "untriaged_moderate_high_frp"

    classification = triage.classification
    danger = triage.danger_level or 1
    frp = event.frp or 0.0

    # Rule 1: Exclude non-fire sources
    if classification in ("FALSE_POSITIVE", "INDUSTRIAL_SOURCE"):
        return False, f"classification_{classification.lower()}"

    # Rule 2: Low danger level
    if danger <= 1:
        return False, "danger_level_low"

    # Rule 3: FRP-based routing thresholds
    if frp < 30.0:
        if classification == "CONFIRMED_FIRE" and danger >= 4:
            return True, "low_frp_confirmed_critical"
        return False, "low_frp_below_30mw"

    # Moderate / High / Extreme FRP (>= 30 MW)
    if classification in ("CONFIRMED_FIRE", "PROBABLE_FIRE") and danger >= 2:
        return True, "valid_active_fire"

    return False, "routing_criteria_not_met"


class AlertService:
    """Orchestrate the full alert pipeline for a single FireEvent."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def send_alert(
        self,
        event_id: UUID,
        *,
        force: bool = False,
    ) -> dict:
        """
        Send alert for a fire event.

        Args:
            event_id: UUID of the FireEvent row.
            force:    If True, skip the dedup check (used by retry jobs).

        Returns:
            dict with keys: skipped, telegram_ok, webhooks_ok, webhooks_failed
        """
        event: FireEvent | None = await self._load_event(event_id)
        if event is None:
            logger.warning("alert_service.send_alert: event %s not found", event_id)
            return {"skipped": True, "reason": "event_not_found"}

        # 1. Dedup -----------------------------------------------------------
        if not force and is_already_alerted(event):
            logger.info(
                "alert_service.send_alert: skipping dedup for event %s (alerted_at=%s)",
                event_id,
                event.alerted_at,
            )
            return {"skipped": True, "reason": "already_alerted"}

        # 2. Load related triage + prediction --------------------------------
        triage: TriageReport | None = await self._load_triage(event_id)
        prediction: Prediction | None = await self._load_prediction(event_id)

        # 3. Alert Routing Gating -------------------------------------------
        should_send, route_reason = should_send_alert(event, triage)
        if not force and not should_send:
            logger.info(
                "alert_service.send_alert: routing gate skipped event %s (reason=%s, classification=%s, FRP=%s)",
                event_id,
                route_reason,
                triage.classification if triage else None,
                event.frp,
            )
            return {"skipped": True, "reason": route_reason}

        # 3. Geocode ---------------------------------------------------------
        location_name = await reverse_geocode(event.lat, event.lon)

        # 4. Format ----------------------------------------------------------
        if triage is not None:
            message = format_alert_message(event, triage, prediction, location_name)
        else:
            # Fallback plain message when triage not yet available
            message = (
                f"🔥 AERO-FLARE ALERT\n"
                f"📍 {location_name} ({event.lat:.4f}, {event.lon:.4f})\n"
                f"FRP: {event.frp} MW | Status: {event.status}"
            )

        # 5. Deliver ---------------------------------------------------------
        telegram_ok, telegram_err = await self._deliver_telegram(message, event_id)
        webhooks_ok, webhooks_failed = await self._deliver_webhooks(
            event, message, triage
        )

        delivery_success = telegram_ok or webhooks_ok > 0

        # 6. Mark alerted / failed -------------------------------------------
        new_status = "ALERTED" if delivery_success else "ALERTED_FAILED"
        await self._mark_alerted(event_id, status=new_status)

        # 7. Audit log -------------------------------------------------------
        await self._write_audit_log(
            event_id=event_id,
            status=new_status,
            telegram_ok=telegram_ok,
            telegram_err=telegram_err,
            webhooks_ok=webhooks_ok,
            webhooks_failed=webhooks_failed,
        )

        result = {
            "skipped": False,
            "status": new_status,
            "telegram_ok": telegram_ok,
            "webhooks_ok": webhooks_ok,
            "webhooks_failed": webhooks_failed,
        }
        logger.info("alert_service.send_alert: event %s → %s", event_id, result)
        return result

    # ------------------------------------------------------------------
    # Bulk retry (called by scripts/retry_alerts.py)
    # ------------------------------------------------------------------

    async def retry_failed_alerts(self, limit: int = 50) -> list[dict]:
        """Retry all ALERTED_FAILED events up to `limit`."""
        stmt = (
            select(FireEvent)
            .where(FireEvent.status == "ALERTED_FAILED")
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        outcomes = []
        for event in events:
            outcome = await self.send_alert(event.id, force=True)
            outcomes.append({"event_id": str(event.id), **outcome})
        return outcomes

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_event(self, event_id: UUID) -> FireEvent | None:
        stmt = select(FireEvent).where(FireEvent.id == event_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_triage(self, event_id: UUID) -> TriageReport | None:
        stmt = (
            select(TriageReport)
            .where(TriageReport.event_id == event_id)
            .order_by(TriageReport.processed_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_prediction(self, event_id: UUID) -> Prediction | None:
        stmt = (
            select(Prediction)
            .where(Prediction.event_id == event_id)
            .order_by(Prediction.predicted_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _deliver_telegram(
        self, message: str, event_id: UUID
    ) -> tuple[bool, str | None]:
        """Returns (ok, error_message)."""
        settings = get_settings()
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHANNEL_ID:
            return False, "telegram_not_configured"
        try:
            ok = await send_telegram_alert(
                message,
                channel_id=settings.TELEGRAM_CHANNEL_ID,
                bot_token=settings.TELEGRAM_BOT_TOKEN,
            )
            return ok, None if ok else "telegram_send_returned_false"
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "alert_service: Telegram delivery failed for event %s: %s",
                event_id,
                exc,
            )
            return False, str(exc)

    async def _deliver_webhooks(
        self,
        event: FireEvent,
        message: str,
        triage: TriageReport | None,
    ) -> tuple[int, int]:
        """
        Deliver to all active webhooks. Returns (ok_count, failed_count).

        Total active-webhook count is read first so we can derive the failed
        count from the success count returned by ``dispatch_webhooks``.
        """
        from app.models.webhook import WebhookRegistration

        count_stmt = select(WebhookRegistration).where(
            WebhookRegistration.is_active.is_(True)
        )
        total = len((await self.db.execute(count_stmt)).scalars().all())
        if total == 0:
            return 0, 0

        payload = {
            "event_id": str(event.id),
            "lat": event.lat,
            "lon": event.lon,
            "frp": event.frp,
            "danger_level": triage.danger_level if triage else None,
            "classification": triage.classification if triage else None,
            "alerted_at": datetime.now(timezone.utc).isoformat(),
            "message": message,
        }

        ok = await dispatch_webhooks(str(event.id), payload, self.db)
        failed = max(0, total - ok)
        return ok, failed

    async def _mark_alerted(self, event_id: UUID, *, status: str) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(FireEvent)
            .where(FireEvent.id == event_id)
            .values(
                alerted_at=now,
                status=status,
            )
        )
        await self.db.execute(stmt)

    async def _write_audit_log(
        self,
        *,
        event_id: UUID,
        status: str,
        telegram_ok: bool,
        telegram_err: str | None,
        webhooks_ok: int,
        webhooks_failed: int,
    ) -> None:
        log_entry = EventAuditLog(
            table_name="fire_events",
            operation="ALERT",
            row_id=event_id,
            old_values=None,
            new_values={
                "alert_status": status,
                "telegram_ok": telegram_ok,
                "telegram_error": telegram_err,
                "webhooks_ok": webhooks_ok,
                "webhooks_failed": webhooks_failed,
            },
            changed_by="alert_service",
        )
        self.db.add(log_entry)
