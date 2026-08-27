"""Unit tests for VLM response parser."""
from __future__ import annotations

import pytest

from app.services.triage.response_parser import parse_vlm_response

VALID_JSON = """{
  "classification": "CONFIRMED_FIRE",
  "confidence": 0.92,
  "danger_level": 4,
  "fire_area_ha": 125.5,
  "smoke_direction": "NW",
  "recommended_action": "DISPATCH_LOCAL",
  "summary": "Active fire with visible smoke plume in peatland area.",
  "triage_source": "vlm"
}"""

MARKDOWN_FENCED_JSON = f"```json\n{VALID_JSON}\n```"
MARKDOWN_FENCED_NO_LANG = f"```\n{VALID_JSON}\n```"

FALSE_POSITIVE_JSON = """{
  "classification": "FALSE_POSITIVE",
  "confidence": 0.85,
  "danger_level": 1,
  "fire_area_ha": 0.0,
  "smoke_direction": null,
  "recommended_action": "MONITOR",
  "summary": "Sun glint on water surface — not a fire.",
  "triage_source": "vlm"
}"""

INDUSTRIAL_JSON = """{
  "classification": "INDUSTRIAL_SOURCE",
  "confidence": 0.78,
  "danger_level": 1,
  "fire_area_ha": 0.0,
  "smoke_direction": null,
  "recommended_action": "MONITOR",
  "summary": "Palm oil mill — persistent industrial heat source.",
  "triage_source": "vlm"
}"""


def test_parse_valid_json():
    output = parse_vlm_response(VALID_JSON)
    assert output.classification == "CONFIRMED_FIRE"
    assert output.confidence == pytest.approx(0.92)
    assert output.danger_level == 4
    assert output.fire_area_ha == pytest.approx(125.5)
    assert output.triage_source == "vlm"


def test_parse_markdown_fenced_json():
    output = parse_vlm_response(MARKDOWN_FENCED_JSON)
    assert output.classification == "CONFIRMED_FIRE"


def test_parse_markdown_fenced_no_lang():
    output = parse_vlm_response(MARKDOWN_FENCED_NO_LANG)
    assert output.classification == "CONFIRMED_FIRE"


def test_parse_false_positive():
    output = parse_vlm_response(FALSE_POSITIVE_JSON)
    assert output.classification == "FALSE_POSITIVE"
    assert output.danger_level == 1


def test_parse_industrial_source():
    output = parse_vlm_response(INDUSTRIAL_JSON)
    assert output.classification == "INDUSTRIAL_SOURCE"


def test_parse_no_json_raises_value_error():
    with pytest.raises(ValueError, match="No JSON object found"):
        parse_vlm_response("This is just a sentence with no JSON.")


def test_parse_invalid_json_raises_value_error():
    with pytest.raises(ValueError):
        parse_vlm_response("{this is not : valid json}")


def test_parse_json_embedded_in_prose():
    """VLM sometimes wraps JSON in explanation text — parser should extract it."""
    prose = f"Sure, here is my analysis:\n{VALID_JSON}\nHope this helps!"
    output = parse_vlm_response(prose)
    assert output.classification == "CONFIRMED_FIRE"
