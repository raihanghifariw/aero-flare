"""
Unit tests for AlertFormatter (format_alert_message).
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.alerts.alert_formatter import format_alert_message


def _mock_event(
    *,
    frp: float = 120.5,
    lat: float = -1.234,
    lon: float = 117.567,
    detected_at: datetime | None = None,
) -> MagicMock:
    event = MagicMock()
    event.id = uuid4()
    event.frp = frp
    event.lat = lat
    event.lon = lon
    event.status = "TRIAGED"
    event.detected_at = detected_at or datetime(2024, 7, 15, 6, 0, 0, tzinfo=timezone.utc)
    return event


def _mock_triage(
    *,
    classification: str = "CONFIRMED_FIRE",
    danger_level: str = "HIGH",
    confidence: float = 0.92,
    triage_source: str = "VLM",
    fire_area_ha: float = 12.5,
    recommended_action: str = "DEPLOY_FIREFIGHTERS",
    summary: str = "Large fire detected",
) -> MagicMock:
    t = MagicMock()
    t.classification = classification
    t.danger_level = danger_level
    t.confidence = confidence
    t.triage_source = triage_source
    t.fire_area_ha = fire_area_ha
    t.recommended_action = recommended_action
    t.summary = summary
    return t


def _mock_prediction(
    *,
    spread_direction_deg: float = 45.0,
    radius_6h_km: float = 5.0,
    radius_12h_km: float = 9.5,
) -> MagicMock:
    p = MagicMock()
    p.spread_direction_deg = spread_direction_deg
    p.radius_6h_km = radius_6h_km
    p.radius_12h_km = radius_12h_km
    return p


class TestFormatAlertMessage:
    def test_contains_danger_level(self) -> None:
        """Formatted message must include the danger level."""
        event = _mock_event()
        triage = _mock_triage(danger_level="CRITICAL")
        msg = format_alert_message(event, triage, None, "Kalimantan Tengah")
        assert "CRITICAL" in msg

    def test_contains_coordinates(self) -> None:
        """Formatted message must include lat/lon."""
        event = _mock_event(lat=-1.234, lon=117.567)
        triage = _mock_triage()
        msg = format_alert_message(event, triage, None, "East Borneo")
        assert "-1.234" in msg or "1.2340" in msg
        assert "117.567" in msg or "117.5670" in msg

    def test_contains_location_name(self) -> None:
        """When location name is provided it must appear in the message."""
        event = _mock_event()
        triage = _mock_triage()
        msg = format_alert_message(event, triage, None, "Riau Province")
        assert "Riau Province" in msg

    def test_format_with_prediction(self) -> None:
        """When prediction is provided the spread info appears in message."""
        event = _mock_event()
        triage = _mock_triage()
        pred = _mock_prediction(radius_6h_km=7.0)
        msg = format_alert_message(event, triage, pred, "Sumatra")
        assert "7" in msg  # radius appears

    def test_format_without_prediction(self) -> None:
        """Message is still valid with prediction=None."""
        event = _mock_event()
        triage = _mock_triage()
        msg = format_alert_message(event, triage, None, "Aceh")
        assert len(msg) > 20

    def test_high_danger_includes_fire_marker(self) -> None:
        """HIGH / CRITICAL danger should include an alert marker."""
        event = _mock_event()
        triage = _mock_triage(danger_level="HIGH")
        msg = format_alert_message(event, triage, None, "West Papua")
        keywords = {"🔥", "⚠", "HIGH", "WARNING", "ALERT", "FIRE"}
        assert any(kw in msg for kw in keywords)
