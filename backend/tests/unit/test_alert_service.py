"""
Unit tests for the AlertService orchestrator (alert_service.py).

Covers:
- send_alert: event-not-found, already-alerted (dedup skip), full success path,
  Telegram-not-configured path, partial webhook failure
- retry_failed_alerts: retries ALERTED_FAILED events with force=True
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.alerts.alert_service import AlertService


def _mock_event(alerted_at=None, status="TRIAGED") -> MagicMock:
    event = MagicMock()
    event.id = uuid.uuid4()
    event.lat = -2.345
    event.lon = 112.456
    event.frp = 65.0
    event.status = status
    event.alerted_at = alerted_at
    return event


def _db_returning(*scalar_results: object) -> AsyncMock:
    """Build an AsyncMock DB whose .execute() yields results in sequence."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy
    results = []
    for val in scalar_results:
        r = MagicMock()
        r.scalar_one_or_none.return_value = val
        r.scalars.return_value.all.return_value = val if isinstance(val, list) else []
        results.append(r)
    mock_db.execute = AsyncMock(side_effect=results)
    return mock_db


class TestSendAlert:
    @pytest.mark.asyncio
    async def test_returns_skipped_when_event_not_found(self) -> None:
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        svc = AlertService(mock_db)
        outcome = await svc.send_alert(uuid.uuid4())

        assert outcome == {"skipped": True, "reason": "event_not_found"}

    @pytest.mark.asyncio
    async def test_skips_when_already_alerted_and_not_forced(self) -> None:
        event = _mock_event(alerted_at=datetime.now(timezone.utc))
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = event
        mock_db.execute = AsyncMock(return_value=result_mock)

        svc = AlertService(mock_db)
        outcome = await svc.send_alert(event.id)

        assert outcome == {"skipped": True, "reason": "already_alerted"}

    @pytest.mark.asyncio
    async def test_force_bypasses_dedup(self) -> None:
        event = _mock_event(alerted_at=datetime.now(timezone.utc))
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy

        # execute() call order in send_alert (force path):
        # 1. _load_event -> event
        # 2. _load_triage -> None
        # 3. _load_prediction -> None
        # 4. _deliver_webhooks count query -> []
        # 5. _mark_alerted (UPDATE, no scalar needed)
        # 6. audit log add (no execute call, just db.add)
        r_event = MagicMock()
        r_event.scalar_one_or_none.return_value = event
        r_triage = MagicMock()
        r_triage.scalar_one_or_none.return_value = None
        r_pred = MagicMock()
        r_pred.scalar_one_or_none.return_value = None
        r_webhooks = MagicMock()
        r_webhooks.scalars.return_value.all.return_value = []
        r_update = MagicMock()
        mock_db.execute = AsyncMock(
            side_effect=[r_event, r_triage, r_pred, r_webhooks, r_update]
        )

        with patch(
            "app.services.alerts.alert_service.reverse_geocode",
            new=AsyncMock(return_value="Central Kalimantan, Indonesia"),
        ), patch(
            "app.services.alerts.alert_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.TELEGRAM_BOT_TOKEN = ""
            mock_settings.return_value.TELEGRAM_CHANNEL_ID = ""

            svc = AlertService(mock_db)
            outcome = await svc.send_alert(event.id, force=True)

        assert outcome["skipped"] is False
        # Telegram not configured + no webhooks â†’ delivery fails
        assert outcome["status"] == "ALERTED_FAILED"
        assert outcome["telegram_ok"] is False
        assert outcome["webhooks_ok"] == 0

    @pytest.mark.asyncio
    async def test_successful_telegram_delivery_marks_alerted(self) -> None:
        event = _mock_event(alerted_at=None)
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy

        r_event = MagicMock()

        r_event.scalar_one_or_none.return_value = event
        r_triage = MagicMock()
        r_triage.scalar_one_or_none.return_value = None
        r_pred = MagicMock()
        r_pred.scalar_one_or_none.return_value = None
        r_webhooks = MagicMock()
        r_webhooks.scalars.return_value.all.return_value = []
        r_update = MagicMock()
        mock_db.execute = AsyncMock(
            side_effect=[r_event, r_triage, r_pred, r_webhooks, r_update]
        )

        with patch(
            "app.services.alerts.alert_service.reverse_geocode",
            new=AsyncMock(return_value="Central Kalimantan, Indonesia"),
        ), patch(
            "app.services.alerts.alert_service.get_settings"
        ) as mock_settings, patch(
            "app.services.alerts.alert_service.send_telegram_alert",
            new=AsyncMock(return_value=True),
        ):
            mock_settings.return_value.TELEGRAM_BOT_TOKEN = "tok"
            mock_settings.return_value.TELEGRAM_CHANNEL_ID = "-100123"

            svc = AlertService(mock_db)
            outcome = await svc.send_alert(event.id)

        assert outcome["status"] == "ALERTED"
        assert outcome["telegram_ok"] is True
        mock_db.add.assert_called_once()  # audit log written

    @pytest.mark.asyncio
    async def test_telegram_not_configured_returns_false_reason(self) -> None:
        event = _mock_event(alerted_at=None)
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy
        r_event = MagicMock()
        r_event.scalar_one_or_none.return_value = event
        r_triage = MagicMock()
        r_triage.scalar_one_or_none.return_value = None
        r_pred = MagicMock()
        r_pred.scalar_one_or_none.return_value = None
        r_webhooks = MagicMock()
        r_webhooks.scalars.return_value.all.return_value = []
        r_update = MagicMock()
        mock_db.execute = AsyncMock(
            side_effect=[r_event, r_triage, r_pred, r_webhooks, r_update]
        )

        with patch(
            "app.services.alerts.alert_service.reverse_geocode",
            new=AsyncMock(return_value="loc"),
        ), patch(
            "app.services.alerts.alert_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.TELEGRAM_BOT_TOKEN = ""
            mock_settings.return_value.TELEGRAM_CHANNEL_ID = ""

            svc = AlertService(mock_db)
            outcome = await svc.send_alert(event.id)

        assert outcome["telegram_ok"] is False


class TestRetryFailedAlerts:
    @pytest.mark.asyncio
    async def test_retries_each_failed_event_with_force(self) -> None:
        e1, e2 = _mock_event(status="ALERTED_FAILED"), _mock_event(
            status="ALERTED_FAILED"
        )
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [e1, e2]
        mock_db.execute = AsyncMock(return_value=list_result)

        svc = AlertService(mock_db)
        with patch.object(
            svc, "send_alert", new=AsyncMock(return_value={"skipped": False, "status": "ALERTED"})
        ) as mock_send:
            outcomes = await svc.retry_failed_alerts(limit=10)

        assert len(outcomes) == 2
        assert mock_send.call_count == 2
        # Each call must use force=True
        for call in mock_send.call_args_list:
            assert call.kwargs.get("force") is True

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_failed_events(self) -> None:
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=list_result)

        svc = AlertService(mock_db)
        outcomes = await svc.retry_failed_alerts()
        assert outcomes == []


