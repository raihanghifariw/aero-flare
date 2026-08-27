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


def parse_vlm_response(raw_text: str) -> TriageOutput:
    """
    Parse raw VLM text output into a validated TriageOutput object.

    Attempts:
      1. Strip markdown code fences
      2. Extract first {...} JSON object from text
      3. Validate with Pydantic

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
