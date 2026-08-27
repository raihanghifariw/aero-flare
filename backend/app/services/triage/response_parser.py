"""
VLM response parser — strips markdown fences and validates JSON against TriageOutput schema.
FR-05: 4 classification labels. FR-06: Extract all structured fields.
"""
from __future__ import annotations

import json
import re

import structlog

from app.schemas.triage_report import TriageOutput

logger = structlog.get_logger()

# Strips ```json ... ``` or ``` ... ``` markdown code fences
_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
# Tries to extract the first {...} JSON object even without fences
_JSON_OBJ_RE = re.compile(r"\{[\s\S]+\}", re.DOTALL)


def apply_triage_guardrails(
    output: TriageOutput,
    event: object | None = None,
) -> TriageOutput:
    """
    Sanity validation & sensor fusion guardrails to prevent visual hallucination contradictions:
      1. Cloud Obscuration + FRP Fusion: If cloud_cover_percent >= 50% or visually_obscured is True,
         AND sensor FRP >= 50.0 MW, set classification="PROBABLE_FIRE",
         danger_level=3 (or 4 if FRP >= 100), and summary="High Heat Detected (FRP {frp}MW) — Visually Obscured by Cloud Cover".
      2. 0.0 ha Area Contradiction: If fire_area_ha == 0.0 or None, cap danger_level to max 2 and prevent EVACUATE/DISPATCH_REGIONAL.
      3. No Smoke / No Fire Visual: If smoke_visible is False and classification == "CONFIRMED_FIRE", downgrade to "PROBABLE_FIRE".
    """
    area = output.fire_area_ha or 0.0
    danger = output.danger_level or 2
    classification = output.classification
    action = output.recommended_action
    confidence = output.confidence or 0.5
    smoke_visible = output.smoke_visible
    cloud_cover = output.cloud_cover_percent or 0.0
    is_obscured = output.visually_obscured or (cloud_cover >= 50.0)

    frp = getattr(event, "frp", 0.0) if event else 0.0
    summary = output.summary

    # Guardrail A: High Thermal Energy + Cloud Cover Fusion
    if is_obscured:
        is_obscured = True
        if frp >= 50.0:
            classification = "PROBABLE_FIRE"
            danger = 4 if frp >= 100.0 else 3
            action = "DISPATCH_LOCAL" if danger >= 3 else "INVESTIGATE"
            confidence = max(confidence, 0.75)
            summary = f"High Heat Detected (FRP {frp:.1f} MW) — Visually Obscured by Cloud Cover ({cloud_cover:.0f}%)"

    # Guardrail B: Contradiction check (0.0 ha area cannot be Level 4/5 Critical/Dispatch)
    if area == 0.0 and not is_obscured:
        if danger >= 4:
            danger = 2
            if action in ("DISPATCH_REGIONAL", "EVACUATE", "DISPATCH"):
                action = "INVESTIGATE"
        if classification == "CONFIRMED_FIRE" and smoke_visible is False:
            classification = "PROBABLE_FIRE"
            confidence = min(confidence, 0.6)

    # Guardrail C: Visual smoke/flame check
    if smoke_visible is False and classification == "CONFIRMED_FIRE" and not is_obscured:
        classification = "PROBABLE_FIRE"
        if danger >= 4:
            danger = 3
            action = "DISPATCH_LOCAL"

    return output.model_copy(update={
        "classification": classification,
        "danger_level": danger,
        "recommended_action": action,
        "confidence": confidence,
        "visually_obscured": is_obscured,
        "cloud_cover_percent": cloud_cover if cloud_cover > 0 else (65.0 if is_obscured else 0.0),
        "summary": summary,
    })


def parse_vlm_response(raw_text: str, event: object | None = None) -> TriageOutput:
    """
    Parse raw VLM text output into a validated TriageOutput object.

    Attempts:
      1. Strip markdown code fences
      2. Extract first {...} JSON object from text
      3. Validate with Pydantic + Apply Guardrails with FRP Fusion

    Raises:
        ValueError: if no valid JSON or schema validation fails.
    """
    text = raw_text.strip()

    # Step 1: strip markdown fences
    fence_match = _FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Step 2: find first JSON object
    json_match = _JSON_OBJ_RE.search(text)
    if not json_match:
        logger.warning("vlm_response_no_json", raw_chars=len(raw_text))
        raise ValueError(f"No JSON object found in VLM response: {raw_text[:200]!r}")

    json_str = json_match.group(0)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning("vlm_response_json_decode_error", error=str(e), json_str=json_str[:200])
        raise ValueError(f"JSON decode error: {e}") from e

    # Step 3: Validate with Pydantic — normalize triage_source casing
    source = data.get("triage_source", "vlm")
    if isinstance(source, str):
        data["triage_source"] = "rule_based" if "rule" in source.lower() else "vlm"

    try:
        output = TriageOutput.model_validate(data)
        output = apply_triage_guardrails(output, event=event)
    except Exception as e:
        logger.warning("vlm_response_schema_error", error=str(e), data=str(data)[:300])
        raise ValueError(f"TriageOutput schema validation failed: {e}") from e

    logger.info(
        "vlm_response_parsed",
        classification=output.classification,
        confidence=output.confidence,
        danger_level=output.danger_level,
        triage_source=output.triage_source,
    )
    return output
