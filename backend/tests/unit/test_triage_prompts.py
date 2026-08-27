"""
Golden response tests for VLM triage prompt parser.

These tests validate that parse_vlm_response() correctly handles the full
range of VLM output formats found in production — including markdown fences,
prose wrappers, and plain JSON.

Golden response files in tests/fixtures/vlm_golden_responses/ are captured
from real Qwen2-VL / LLaVA responses during manual testing.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas.triage_report import TriageOutput
from app.services.triage.response_parser import parse_vlm_response

GOLDEN_DIR = Path(__file__).parent.parent / "fixtures" / "vlm_golden_responses"

VALID_CLASSIFICATIONS = {
    "CONFIRMED_FIRE", "PROBABLE_FIRE", "FALSE_POSITIVE", "INDUSTRIAL_SOURCE"
}
VALID_ACTIONS = {
    "MONITOR", "INVESTIGATE", "DISPATCH_LOCAL", "DISPATCH_REGIONAL", "EVACUATE"
}
VALID_SOURCES = {"vlm", "rule_based"}


class TestGoldenResponses:
    """All saved golden VLM responses must parse cleanly."""

    def test_golden_dir_exists_and_has_files(self) -> None:
        """Ensure fixtures directory is present and non-empty."""
        assert GOLDEN_DIR.is_dir(), f"Golden fixture directory not found: {GOLDEN_DIR}"
        golden_files = list(GOLDEN_DIR.glob("*.txt"))
        assert len(golden_files) >= 4, (
            f"Expected at least 4 golden response files, found {len(golden_files)}"
        )

    def test_all_golden_responses_parse_successfully(self) -> None:
        """Every .txt file in the golden dir must parse without raising."""
        for golden_file in sorted(GOLDEN_DIR.glob("*.txt")):
            raw = golden_file.read_text(encoding="utf-8")
            result = parse_vlm_response(raw)
            assert isinstance(result, TriageOutput), (
                f"{golden_file.name}: expected TriageOutput, got {type(result)}"
            )

    def test_all_golden_classifications_are_valid(self) -> None:
        for golden_file in sorted(GOLDEN_DIR.glob("*.txt")):
            raw = golden_file.read_text(encoding="utf-8")
            result = parse_vlm_response(raw)
            assert result.classification in VALID_CLASSIFICATIONS, (
                f"{golden_file.name}: invalid classification {result.classification!r}"
            )

    def test_all_golden_confidence_in_range(self) -> None:
        for golden_file in sorted(GOLDEN_DIR.glob("*.txt")):
            raw = golden_file.read_text(encoding="utf-8")
            result = parse_vlm_response(raw)
            assert 0.0 <= result.confidence <= 1.0, (
                f"{golden_file.name}: confidence {result.confidence} out of range"
            )

    def test_all_golden_danger_level_in_range(self) -> None:
        for golden_file in sorted(GOLDEN_DIR.glob("*.txt")):
            raw = golden_file.read_text(encoding="utf-8")
            result = parse_vlm_response(raw)
            assert 1 <= result.danger_level <= 5, (
                f"{golden_file.name}: danger_level {result.danger_level} out of range"
            )

    def test_all_golden_recommended_action_valid(self) -> None:
        for golden_file in sorted(GOLDEN_DIR.glob("*.txt")):
            raw = golden_file.read_text(encoding="utf-8")
            result = parse_vlm_response(raw)
            assert result.recommended_action in VALID_ACTIONS, (
                f"{golden_file.name}: invalid action {result.recommended_action!r}"
            )

    def test_all_golden_triage_source_valid(self) -> None:
        for golden_file in sorted(GOLDEN_DIR.glob("*.txt")):
            raw = golden_file.read_text(encoding="utf-8")
            result = parse_vlm_response(raw)
            assert result.triage_source in VALID_SOURCES, (
                f"{golden_file.name}: invalid triage_source {result.triage_source!r}"
            )


class TestSpecificGoldenFiles:
    """File-specific assertions for expected values."""

    def test_confirmed_fire_golden(self) -> None:
        raw = (GOLDEN_DIR / "confirmed_fire_1.txt").read_text()
        result = parse_vlm_response(raw)
        assert result.classification == "CONFIRMED_FIRE"
        assert result.danger_level >= 3
        assert result.confidence > 0.85
        assert result.smoke_direction == "NW"

    def test_false_positive_golden(self) -> None:
        raw = (GOLDEN_DIR / "false_positive_reflection.txt").read_text()
        result = parse_vlm_response(raw)
        assert result.classification == "FALSE_POSITIVE"
        assert result.danger_level == 1
        assert result.recommended_action == "MONITOR"

    def test_industrial_source_golden(self) -> None:
        raw = (GOLDEN_DIR / "industrial_source.txt").read_text()
        result = parse_vlm_response(raw)
        assert result.classification == "INDUSTRIAL_SOURCE"
        assert result.danger_level == 1

    def test_probable_fire_cloudy_golden(self) -> None:
        raw = (GOLDEN_DIR / "probable_fire_cloudy.txt").read_text()
        result = parse_vlm_response(raw)
        assert result.classification == "PROBABLE_FIRE"
        assert result.confidence < 0.80  # reduced confidence due to cloud cover
