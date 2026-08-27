"""Unit tests for rule-based triage fallback."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.services.triage.rule_based_triage import FRP_HIGH_THRESHOLD, rule_based_triage


def _make_event(frp: float | None) -> MagicMock:
    event = MagicMock()
    event.id = uuid.uuid4()
    event.frp = frp
    event.lat = -2.345
    event.lon = 112.456
    event.detected_at = datetime.now(timezone.utc)
    return event


def test_rule_based_high_frp_returns_probable_fire():
    event = _make_event(frp=FRP_HIGH_THRESHOLD + 1)
    result = rule_based_triage(event)
    assert result.classification == "PROBABLE_FIRE"
    assert result.danger_level == 3
    assert result.recommended_action == "DISPATCH_LOCAL"
    assert result.triage_source == "rule_based"


def test_rule_based_low_frp_returns_monitor():
    event = _make_event(frp=10.0)
    result = rule_based_triage(event)
    assert result.classification == "PROBABLE_FIRE"
    assert result.danger_level == 2
    assert result.recommended_action == "MONITOR"
    assert result.triage_source == "rule_based"


def test_rule_based_exact_threshold_is_low():
    """FRP == threshold is NOT high — must be strictly greater."""
    event = _make_event(frp=FRP_HIGH_THRESHOLD)
    result = rule_based_triage(event)
    assert result.danger_level == 2  # not high threshold


def test_rule_based_none_frp_returns_monitor():
    event = _make_event(frp=None)
    result = rule_based_triage(event)
    assert result.triage_source == "rule_based"
    assert result.recommended_action == "MONITOR"


def test_rule_based_confidence_is_lower_than_vlm():
    """Rule-based should always have confidence < 0.7 to indicate uncertainty."""
    event = _make_event(frp=200.0)
    result = rule_based_triage(event)
    assert result.confidence < 0.7
