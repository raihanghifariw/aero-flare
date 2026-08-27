"""
Triage prompt builder — loads versioned system prompt and injects event metadata.
"""
from __future__ import annotations

from pathlib import Path

from app.models.fire_event import FireEvent

# In Docker, prompts are mounted at /app/prompts; locally they live at repo root.
PROMPT_PATH = Path("/app/prompts/triage_prompt.md")
if not PROMPT_PATH.exists():
    PROMPT_PATH = Path(__file__).resolve().parents[4] / "prompts" / "triage_prompt.md"


def build_triage_prompt(event: FireEvent) -> str:
    """
    Load the versioned triage system prompt and inject event-specific metadata.

    Returns:
        The complete prompt string to send to the VLM.
    """
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    detected_at_str = (
        event.detected_at.strftime("%Y-%m-%d %H:%M UTC")
        if event.detected_at
        else "unknown"
    )

    metadata_block = f"""
## Event Metadata
- Latitude: {event.lat:.4f}°
- Longitude: {event.lon:.4f}°
- FRP (Fire Radiative Power): {event.frp or 'unknown'} MW
- Satellite: {event.satellite or 'unknown'}
- Detection Time: {detected_at_str}

Analyze the satellite image centered on these coordinates and provide your classification.
Remember: respond with ONLY a valid JSON object — no prose, no markdown fences.
"""

    return system_prompt + metadata_block
