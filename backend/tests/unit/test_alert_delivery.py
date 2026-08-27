"""
Unit tests for alert delivery helpers:
- geocoder.reverse_geocode (+ lru cache fallback)
- telegram_service.send_telegram_alert
- webhook_service.dispatch_webhooks (+ HMAC signing)
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.alerts import geocoder
from app.services.alerts.telegram_service import send_telegram_alert
from app.services.alerts.webhook_service import _sign_payload, dispatch_webhooks


class TestReverseGeocode:
    @pytest.mark.asyncio
    async def test_returns_location_name_from_nominatim(self) -> None:
        geocoder._cached_geocode.cache_clear()
        mock_resp = MagicMock(status_code=200)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "address": {"state": "Central Kalimantan", "country": "Indonesia"}
        }
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__enter__.return_value = mock_client

            name = await geocoder.reverse_geocode(-2.345, 112.456)

        assert name == "Central Kalimantan, Indonesia"

    @pytest.mark.asyncio
    async def test_falls_back_to_coords_on_error(self) -> None:
        geocoder._cached_geocode.cache_clear()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ConnectError("down")
            mock_client_cls.return_value.__enter__.return_value = mock_client

            name = await geocoder.reverse_geocode(-9.99, 100.11)

        # Truncated to 2dp then formatted with 3 decimals in the fallback branch
        assert "-9.99" in name or "-9.990" in name

    @pytest.mark.asyncio
    async def test_result_is_cached(self) -> None:
        geocoder._cached_geocode.cache_clear()
        mock_resp = MagicMock(status_code=200)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"address": {"country": "Indonesia"}}
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__enter__.return_value = mock_client

            await geocoder.reverse_geocode(1.234, 5.678)
            await geocoder.reverse_geocode(1.234, 5.678)  # same 2dp key → cached

            # Only one real HTTP call despite two invocations
            assert mock_client.get.call_count == 1


class TestSendTelegramAlert:
    @pytest.mark.asyncio
    async def test_success_returns_true(self) -> None:
        mock_bot = AsyncMock()
        mock_bot.__aenter__.return_value = mock_bot
        mock_bot.__aexit__.return_value = False
        with patch(
            "app.services.alerts.telegram_service.Bot", return_value=mock_bot
        ):
            ok = await send_telegram_alert("hi", channel_id="-100123", bot_token="tok")
        assert ok is True
        mock_bot.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_telegram_error_returns_false(self) -> None:
        from telegram.error import TelegramError

        mock_bot = AsyncMock()
        mock_bot.__aenter__.return_value = mock_bot
        mock_bot.__aexit__.return_value = False
        mock_bot.send_message.side_effect = TelegramError("bad token")
        with patch(
            "app.services.alerts.telegram_service.Bot", return_value=mock_bot
        ):
            ok = await send_telegram_alert("hi", channel_id="-100123", bot_token="tok")
        assert ok is False

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_false(self) -> None:
        mock_bot = AsyncMock()
        mock_bot.__aenter__.return_value = mock_bot
        mock_bot.__aexit__.return_value = False
        mock_bot.send_message.side_effect = RuntimeError("boom")
        with patch(
            "app.services.alerts.telegram_service.Bot", return_value=mock_bot
        ):
            ok = await send_telegram_alert("hi", channel_id="-100123", bot_token="tok")
        assert ok is False


class TestSignPayload:
    def test_hmac_signature_is_deterministic(self) -> None:
        sig1 = _sign_payload(b"payload", "secret")
        sig2 = _sign_payload(b"payload", "secret")
        assert sig1 == sig2
        assert len(sig1) == 64  # sha256 hex digest

    def test_different_secret_changes_signature(self) -> None:
        assert _sign_payload(b"payload", "a") != _sign_payload(b"payload", "b")


class TestDispatchWebhooks:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_webhooks(self) -> None:
        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result_mock

        count = await dispatch_webhooks("evt", {"k": "v"}, mock_db)
        assert count == 0

    @pytest.mark.asyncio
    async def test_delivers_signed_payload_to_active_webhook(self) -> None:
        wh = MagicMock()
        wh.id = uuid.uuid4()
        wh.url = "https://example.com/hook"
        wh.secret = "s3cr3t"

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [wh]
        mock_db.execute.return_value = result_mock

        mock_resp = MagicMock(status_code=200)
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            count = await dispatch_webhooks("evt", {"k": "v"}, mock_db)

        assert count == 1
        headers = mock_client.post.call_args.kwargs["headers"]
        assert headers["X-Aero-Flare-Signature"].startswith("sha256=")

    @pytest.mark.asyncio
    async def test_failed_delivery_not_counted(self) -> None:
        wh = MagicMock()
        wh.id = uuid.uuid4()
        wh.url = "https://example.com/hook"
        wh.secret = None

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [wh]
        mock_db.execute.return_value = result_mock

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("down"))
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            count = await dispatch_webhooks("evt", {"k": "v"}, mock_db)

        assert count == 0
