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


def apply_triage_guardrails(output: TriageOutput) -> TriageOutput:
    """
    Sanity validation guardrails to prevent visual hallucination contradictions:
      1. If fire_area_ha == 0.0 or None, cap danger_level to max 2 and prevent high severity actions.
      2. If smoke_visible is False and classification == "CONFIRMED_FIRE", downgrade to "PROBABLE_FIRE".
    """
    area = output.fire_area_ha or 0.0
    danger = output.danger_level or 2
    classification = output.classification
    action = output.recommended_action
    confidence = output.confidence or 0.5
    smoke_visible = output.smoke_visible

    # Guardrail 1: Contradiction check (0.0 ha area cannot be Level 4/5 Critical/Dispatch)
    if area == 0.0:
        if danger >= 4:
            danger = 2
            if action in ("DISPATCH_REGIONAL", "EVACUATE", "DISPATCH"):
                action = "INVESTIGATE"
        if classification == "CONFIRMED_FIRE" and smoke_visible is False:
            classification = "PROBABLE_FIRE"
            confidence = min(confidence, 0.6)

    # Guardrail 2: Visual smoke/flame check
    if smoke_visible is False and classification == "CONFIRMED_FIRE":
        classification = "PROBABLE_FIRE"
        if danger >= 4:
            danger = 3
            action = "DISPATCH_LOCAL"

    return output.model_copy(update={
        "classification": classification,
        "danger_level": danger,
        "recommended_action": action,
        "confidence": confidence,
    })


def parse_vlm_response(raw_text: str) -> TriageOutput:
    """
    Parse raw VLM text output into a validated TriageOutput object.

    Attempts:
      1. Strip markdown code fences
      2. Extract first {...} JSON object from text
      3. Validate with Pydantic + Apply Guardrails

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
        output = apply_triage_guardrails(output)
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
