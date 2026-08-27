"""
Alert message formatter.
Produces the canonical Aero-Flare alert string for Telegram and webhooks.
FR-12: Alert message format with danger level + spread prediction.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.fire_event import FireEvent
from app.models.prediction import Prediction
from app.models.triage_report import TriageReport

# Spread direction degrees → compass label
_COMPASS = [
    (22.5, "N"), (67.5, "NE"), (112.5, "E"), (157.5, "SE"),
    (202.5, "S"), (247.5, "SW"), (292.5, "W"), (337.5, "NW"), (360.1, "N"),
]

DASHBOARD_URL = "https://aero-flare.vercel.app"


def _compass_label(degrees: float | None) -> str:
    if degrees is None:
        return "—"
    deg = degrees % 360
    for threshold, label in _COMPASS:
        if deg < threshold:
            return label
    return "N"


def format_alert_message(
    event: FireEvent,
    triage: TriageReport,
    prediction: Prediction | None,
    location_name: str,
) -> str:
    """
    Render the canonical Aero-Flare alert string.

    Args:
        event: FireEvent ORM object with lat/lon/detected_at.
        triage: TriageReport with classification + danger_level.
        prediction: Optional XGBoost spread prediction.
        location_name: Human-readable location from reverse geocoding.

    Returns:
        Formatted alert message string (Telegram-friendly Unicode).
    """
    ts = event.detected_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    confidence_pct = round((triage.confidence or 0.0) * 100)
    fire_area = f"{triage.fire_area_ha:.1f}" if triage.fire_area_ha else "—"
    triage_src = "🤖 VLM" if triage.triage_source == "VLM" else "📐 Rule-Based"

    if prediction:
        spread_dir = _compass_label(prediction.spread_direction_deg)
        radius_6h = f"{prediction.radius_6h_km:.1f}"
        radius_12h = f"{prediction.radius_12h_km:.1f}"
        spread_line = f"Arah: {spread_dir} | 6h={radius_6h}km | 12h={radius_12h}km"
    else:
        spread_line = "Prediksi tidak tersedia"

    return (
        f"🔥 *AERO-FLARE ALERT — LEVEL {triage.danger_level}/5*\n"
        f"📍 {location_name} ({event.lat:.4f}, {event.lon:.4f})\n"
        f"🗓️ {ts}\n"
        f"📊 Klasifikasi: *{triage.classification}* ({confidence_pct}%) {triage_src}\n"
        f"🌲 Area Estimasi: {fire_area} ha\n"
        f"💨 Prediksi Rambatan: {spread_line}\n"
        f"⚡ Tindakan: *{triage.recommended_action or 'MONITOR'}*\n"
        f"🔗 Detail: {DASHBOARD_URL}/events/{event.id}"
    )
