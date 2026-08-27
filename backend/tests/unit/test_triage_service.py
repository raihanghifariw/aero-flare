"""
Unit tests for the triage orchestrator (triage_service.py) and prompt builder.

Covers:
- build_triage_prompt: loads versioned prompt + injects event metadata
- run_triage: VLM success path, VLM failure -> fallback model, both fail ->
  rule-based fallback, Ollama down -> rule-based, canonical triage_source values
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.triage.prompt_builder import build_triage_prompt
from app.services.triage.triage_service import (
    TRIAGE_SOURCE_RULE_BASED,
    TRIAGE_SOURCE_VLM,
    run_triage,
)

VLM_JSON = (
    '{"classification": "CONFIRMED_FIRE", "confidence": 0.92, "danger_level": 4,'
    ' "fire_area_ha": 15.0, "smoke_direction": "NE",'
    ' "summary": "Active fire front visible.", "recommended_action": "DISPATCH_LOCAL"}'
)


def _mock_event(frp: float | None = 78.3, tile_url: str | None = "tiles/2026/x.jpg"):
    e = MagicMock()
    e.id = uuid.uuid4()
    e.lat = -2.345
    e.lon = 112.456
    e.frp = frp
    e.satellite = "NOAA-20"
    e.tile_url = tile_url
    e.detected_at = datetime.now(timezone.utc)
    return e


class TestBuildTriagePrompt:
    def test_includes_event_metadata(self) -> None:
        event = _mock_event()
        prompt = build_triage_prompt(event)
        assert "-2.3450" in prompt
        assert "112.4560" in prompt
        assert "78.3" in prompt
        assert "NOAA-20" in prompt

    def test_includes_versioned_system_prompt(self) -> None:
        prompt = build_triage_prompt(_mock_event())
        assert "Triage Prompt v" in prompt

    def test_unknown_frp_rendered(self) -> None:
        prompt = build_triage_prompt(_mock_event(frp=None))
        assert "unknown" in prompt


class TestRunTriage:
    @pytest.mark.asyncio
    async def test_vlm_success_persists_vlm_source(self) -> None:
        event = _mock_event()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy

        with patch(
            "app.services.triage.triage_service.check_ollama_reachable",
            new=AsyncMock(return_value=True),
        ), patch(
            "app.services.triage.triage_service._download_tile_for_vlm",
            new=AsyncMock(return_value="C:/tmp/tile.jpg"),
        ), patch(
            "app.services.triage.triage_service.call_vlm",
            new=AsyncMock(return_value=VLM_JSON),
        ), patch(
            "app.services.ingestion.gibs_tile_fetcher.get_r2_presigned_url",
            return_value="https://r2/signed",
        ), patch(
            "pathlib.Path.unlink"
        ):
            report = await run_triage(event, mock_db)

        assert report.classification == "CONFIRMED_FIRE"
        assert report.triage_source == TRIAGE_SOURCE_VLM
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_primary_fails_fallback_model_succeeds(self) -> None:
        event = _mock_event()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy

        call_results = [RuntimeError("qwen2-vl crashed"), VLM_JSON]

        async def _vlm_side_effect(**kwargs):  # type: ignore[no-untyped-def]
            r = call_results.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

        with patch(
            "app.services.triage.triage_service.check_ollama_reachable",
            new=AsyncMock(return_value=True),
        ), patch(
            "app.services.triage.triage_service._download_tile_for_vlm",
            new=AsyncMock(return_value="C:/tmp/tile.jpg"),
        ), patch(
            "app.services.triage.triage_service.call_vlm",
            new=AsyncMock(side_effect=_vlm_side_effect),
        ) as mock_vlm, patch(
            "app.services.ingestion.gibs_tile_fetcher.get_r2_presigned_url",
            return_value="https://r2/signed",
        ), patch(
            "pathlib.Path.unlink"
        ):
            report = await run_triage(event, mock_db)

        assert report.triage_source == TRIAGE_SOURCE_VLM
        assert mock_vlm.call_count == 2  # primary + fallback model

    @pytest.mark.asyncio
    async def test_both_vlm_models_fail_uses_rule_based(self) -> None:
        event = _mock_event(frp=78.3)  # > 50 MW threshold
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy

        with patch(
            "app.services.triage.triage_service.check_ollama_reachable",
            new=AsyncMock(return_value=True),
        ), patch(
            "app.services.triage.triage_service._download_tile_for_vlm",
            new=AsyncMock(return_value="C:/tmp/tile.jpg"),
        ), patch(
            "app.services.triage.triage_service.call_vlm",
            new=AsyncMock(side_effect=RuntimeError("all models down")),
        ), patch(
            "app.services.ingestion.gibs_tile_fetcher.get_r2_presigned_url",
            return_value="https://r2/signed",
        ), patch(
            "app.services.triage.triage_service.AlertService"
        ) as mock_alert_cls, patch(
            "pathlib.Path.unlink"
        ):
            mock_alert_cls.return_value.send_alert = AsyncMock(return_value={})
            report = await run_triage(event, mock_db)

        assert report.triage_source == TRIAGE_SOURCE_RULE_BASED
        assert report.classification == "PROBABLE_FIRE"
        assert report.danger_level == 3  # FRP > 50 â†’ level 3
        # Rule-based path must trigger an immediate alert
        mock_alert_cls.return_value.send_alert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ollama_down_uses_rule_based_low_frp(self) -> None:
        event = _mock_event(frp=20.0)  # below threshold
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy

        with patch(
            "app.services.triage.triage_service.check_ollama_reachable",
            new=AsyncMock(return_value=False),
        ), patch(
            "app.services.triage.triage_service.AlertService"
        ) as mock_alert_cls:
            mock_alert_cls.return_value.send_alert = AsyncMock(return_value={})
            report = await run_triage(event, mock_db)

        assert report.triage_source == TRIAGE_SOURCE_RULE_BASED
        assert report.danger_level == 2  # FRP â‰¤ 50 â†’ level 2

    @pytest.mark.asyncio
    async def test_no_tile_url_skips_vlm(self) -> None:
        """Without a tile there is nothing for the VLM to see â†’ rule-based."""
        event = _mock_event(tile_url=None)
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy

        with patch(
            "app.services.triage.triage_service.check_ollama_reachable",
            new=AsyncMock(return_value=True),
        ), patch(
            "app.services.triage.triage_service.call_vlm",
            new=AsyncMock(),
        ) as mock_vlm, patch(
            "app.services.triage.triage_service.AlertService"
        ) as mock_alert_cls:
            mock_alert_cls.return_value.send_alert = AsyncMock(return_value={})
            report = await run_triage(event, mock_db)

        mock_vlm.assert_not_called()
        assert report.triage_source == TRIAGE_SOURCE_RULE_BASED

    @pytest.mark.asyncio
    async def test_alert_failure_on_rule_based_path_does_not_raise(self) -> None:
        event = _mock_event(frp=90.0)
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy

        with patch(
            "app.services.triage.triage_service.check_ollama_reachable",
            new=AsyncMock(return_value=False),
        ), patch(
            "app.services.triage.triage_service.AlertService"
        ) as mock_alert_cls:
            mock_alert_cls.return_value.send_alert = AsyncMock(
                side_effect=RuntimeError("telegram down")
            )
            report = await run_triage(event, mock_db)  # must not raise

        assert report.triage_source == TRIAGE_SOURCE_RULE_BASED


