"""
Alert message formatter.
Produces the explainable Aero-Flare alert string for Telegram and webhooks.
FR-12: Alert message format with danger level + spread prediction + decision explainability.
"""
from __future__ import annotations

from datetime import timezone

from app.models.fire_event import FireEvent
from app.models.prediction import Prediction
from app.models.triage_report import TriageReport

# Spread direction degrees → compass label
_COMPASS = [
    (22.5, "N (Utara)"), (67.5, "NE (Timur Laut)"), (112.5, "E (Timur)"), (157.5, "SE (Tenggara)"),
    (202.5, "S (Selatan)"), (247.5, "SW (Barat Daya)"), (292.5, "W (Barat)"), (337.5, "NW (Barat Laut)"),
    (360.1, "N (Utara)"),
]

DASHBOARD_URL = "https://aero-flare.vercel.app"


def _compass_label(degrees: float | None) -> str:
    if degrees is None:
        return "—"
    deg = degrees % 360
    for threshold, label in _COMPASS:
        if deg < threshold:
            return label
    return "N (Utara)"


def get_frp_explanation(frp: float | None) -> tuple[str, str, str]:
    """
    Categorize Fire Radiative Power (FRP) with domain explainability.

    Returns:
        (category_label, emoji, explanation)
    """
    val = frp or 0.0
    if val < 30.0:
        return (
            "0 – 30 MW (Low)",
            "🟢",
            "Titik api kecil. Sering kali merupakan pembakaran tunggul pertanian (slash-and-burn), pembakaran sampah, atau pantulan panas permukaan.",
        )
    if val < 100.0:
        return (
            "30 – 100 MW (Moderate/Mid)",
            "🟡",
            "Kebakaran vegetasi aktif, semak belukar, atau api permukaan di hutan.",
        )
    if val <= 500.0:
        return (
            "100 – 500 MW (High)",
            "🟠",
            "Kebakaran hutan skala besar yang menjalar cepat dengan intensitas tinggi.",
        )
    return (
        "> 500 MW (Extreme)",
        "🔴",
        "Bencana kebakaran masif, sering kali melibatkan kanopi pohon besar (crown fires).",
    )


def get_danger_explanation(danger_level: int | str | None) -> str:
    """Provide contextual title for danger level."""
    try:
        level = int(danger_level) if danger_level is not None else 1
    except (ValueError, TypeError):
        return str(danger_level)

    titles = {
        1: "Rendah / False Positive",
        2: "Waspada / Probable Fire",
        3: "Siaga / Active Fire",
        4: "Bahaya Tinggi / Critical Fire",
        5: "Darurat Ekstrem / Disaster Level",
    }
    return titles.get(level, f"Level {level}")


def get_action_protocol(action: str | None) -> str:
    """Translate recommended action into actionable field instruction."""
    act = (action or "").upper()
    if any(k in act for k in ("WATER_BOMBING", "AERIAL", "DISPATCH_WATER_BOMBING")):
        return "Kerahkan helikopter pemadam (water bombing) dan satgas terdekat segera."
    if any(k in act for k in ("GROUND", "PATROL", "DEPLOY_FIREFIGHTERS")):
        return "Kirim regu patroli darat / Manggala Agni untuk verifikasi dan lokalisir titik api."
    if "MONITOR" in act:
        return "Lakukan pemantauan intensif via satelit pada siklus lintas orbit berikutnya."
    if "NO_ACTION" in act:
        return "Tidak diperlukan penanganan lapangan (teridentifikasi aman/bukan ancaman)."
    return f"Protokol: {action or 'Koordinasi dengan BPBD / Satgas Karhutla setempat.'}"


def format_alert_message(
    event: FireEvent,
    triage: TriageReport,
    prediction: Prediction | None,
    location_name: str,
) -> str:
    """
    Render the explainable Aero-Flare alert string for Telegram.

    Includes:
      - Danger level & classification with confidence
      - Thermal intensity (FRP) with domain-specific explanation
      - AI Triage reasoning justification & visual indicators
      - XGBoost spread direction & risk radius (6h / 12h)
      - Recommended operational response protocol
      - Direct incident link to the dashboard
    """
    ts = event.detected_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    confidence_pct = round((triage.confidence or 0.0) * 100)
    fire_area = f"{triage.fire_area_ha:.1f}" if triage.fire_area_ha else "—"
    triage_src = "🤖 AI Vision (VLM)" if triage.triage_source == "VLM" else "📐 Rule-Based Engine"

    # FRP explainability
    frp_val = float(event.frp) if isinstance(event.frp, (int, float)) else 0.0
    frp_cat, frp_emoji, frp_desc = get_frp_explanation(frp_val)
    danger_title = get_danger_explanation(getattr(triage, "danger_level", 1))

    # Spread prediction
    if prediction:
        spread_deg = getattr(prediction, "spread_direction_deg", None)
        spread_dir = _compass_label(spread_deg if isinstance(spread_deg, (int, float)) else None)
        r6 = getattr(prediction, "radius_6h_km", None)
        r12 = getattr(prediction, "radius_12h_km", None)
        radius_6h = f"{r6:.1f} km" if isinstance(r6, (int, float)) else "—"
        radius_12h = f"{r12:.1f} km" if isinstance(r12, (int, float)) else "—"
        spread_info = f"Arah: *{spread_dir}* | 6h: *{radius_6h}* | 12h: *{radius_12h}*"
    else:
        spread_info = "Prediksi cuaca/rambatan belum tersedia"

    # AI Reasoning
    reasoning_summary = getattr(triage, "summary", None) or "Terdeteksi anomali termal aktif oleh sensor satelit."
    action_protocol = get_action_protocol(getattr(triage, "recommended_action", None))

    cloud = getattr(triage, "cloud_cover_percent", None)
    cloud_text = f"{cloud:.0f}%" if isinstance(cloud, (int, float)) else "—"
    obscured = getattr(triage, "visually_obscured", False) is True
    visual_status = "☁️ Terhalang Awan (High Heat)" if (obscured and frp_val >= 50) else "👁️ Terbuka / Terverifikasi"
    sat_name = event.satellite if isinstance(getattr(event, "satellite", None), str) else "VIIRS/MODIS"

    return (
        f"🚨 *AERO-FLARE EARLY WARNING SYSTEM* 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 *STATUS: ALERTED — DANGER LEVEL {triage.danger_level}/5*\n"
        f"⚠️ *Kategori:* *{danger_title}*\n\n"
        f"📍 *Lokasi:* {location_name}\n"
        f"🌐 *Koordinat:* `{event.lat:.4f}, {event.lon:.4f}`\n"
        f"🛰️ *Satelit:* {sat_name} | 🗓️ *Waktu:* {ts}\n\n"
        f"⚡ *Intensitas Panas (FRP):* *{frp_val:.1f} MW* {frp_emoji}\n"
        f"📊 *Skala FRP:* *{frp_cat}*\n"
        f"📝 *Analisis Termal:* _{frp_desc}_\n\n"
        f"🧠 *Keputusan AI Triage:*\n"
        f"• Klasifikasi: *{triage.classification}* (Keyakinan: {confidence_pct}%) [{triage_src}]\n"
        f"• Estimasi Area Api: *{fire_area} ha* | Tutupan Awan: *{cloud_text}*\n"
        f"• Status Visual: *{visual_status}*\n"
        f"• Dasar Pertimbangan: _{reasoning_summary}_\n\n"
        f"💨 *Prediksi Rambatan Api:*\n"
        f"• {spread_info}\n\n"
        f"🚒 *Rekomendasi Tindakan Cepat:* *{triage.recommended_action or 'MONITOR'}*\n"
        f"📋 *Protokol:* _{action_protocol}_\n\n"
        f"🔗 *Buka Insiden di Dashboard:*\n"
        f"{DASHBOARD_URL}/events/{event.id}\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )

