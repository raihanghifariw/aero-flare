"""
Unit tests for the prediction pipeline:
- model_loader.load_model (cache, ModelNotFoundError, repo-root path resolution)
- feature_builder.fetch_weather_features / build_feature_vector
- prediction_service.run_prediction (clamping, DB writes, alert hand-off)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import numpy as np
import pytest

from app.core.exceptions import ModelNotFoundError, PredictionError
from app.services.prediction import model_loader
from app.services.prediction.feature_builder import (
    FEATURE_COLUMNS,
    build_feature_vector,
    estimate_ndvi,
    fetch_weather_features,
    get_land_cover_class,
)
from app.services.prediction.prediction_service import run_prediction


def _mock_event() -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.lat = -2.345
    e.lon = 112.456
    e.frp = 78.3
    e.detected_at = datetime.now(timezone.utc)
    return e


def _mock_triage(fire_area_ha: float | None = 12.5) -> MagicMock:
    t = MagicMock()
    t.fire_area_ha = fire_area_ha
    t.classification = "CONFIRMED_FIRE"
    t.danger_level = 4
    return t


class TestLoadModel:
    def test_raises_when_missing(self) -> None:
        model_loader.clear_model_cache()
        with pytest.raises(ModelNotFoundError, match="XGBoost model not found"):
            model_loader.load_model("definitely/not/here.ubj")

    def test_loads_real_artifact_via_repo_root_resolution(self) -> None:
        """Relative configured path must resolve regardless of CWD."""
        model_loader.clear_model_cache()
        model = model_loader.load_model("ml/models/xgboost_spread_v1.0.0.ubj")
        assert model is not None

    def test_second_load_is_cached(self) -> None:
        model_loader.clear_model_cache()
        path = "ml/models/xgboost_spread_v1.0.0.ubj"
        m1 = model_loader.load_model(path)
        m2 = model_loader.load_model(path)
        assert m1 is m2  # same object â†’ served from cache

    def test_clear_cache_forces_reload(self) -> None:
        path = "ml/models/xgboost_spread_v1.0.0.ubj"
        m1 = model_loader.load_model(path)
        model_loader.clear_model_cache()
        m2 = model_loader.load_model(path)
        assert m1 is not m2


class TestFetchWeatherFeatures:
    @pytest.mark.asyncio
    async def test_parses_open_meteo_response(self) -> None:
        mock_resp = MagicMock(status_code=200)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "current": {
                "wind_speed_10m": 7.5,
                "wind_direction_10m": 225.0,
                "relative_humidity_2m": 55.0,
            }
        }
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__.return_value = mock_client

            out = await fetch_weather_features(-2.0, 112.0)

        assert out == {"wind_speed": 7.5, "wind_direction": 225.0, "humidity": 55.0}

    @pytest.mark.asyncio
    async def test_uses_defaults_when_fields_missing(self) -> None:
        mock_resp = MagicMock(status_code=200)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"current": {}}
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__.return_value = mock_client

            out = await fetch_weather_features(-2.0, 112.0)

        assert out["wind_speed"] == 3.0
        assert out["wind_direction"] == 180.0
        assert out["humidity"] == 60.0

    @pytest.mark.asyncio
    async def test_network_error_raises_prediction_error(self) -> None:
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
            mock_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(PredictionError, match="Open-Meteo network error"):
                await fetch_weather_features(-2.0, 112.0)

    @pytest.mark.asyncio
    async def test_http_error_raises_prediction_error(self) -> None:
        mock_resp = MagicMock(status_code=429)
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rate limited", request=MagicMock(), response=mock_resp
        )
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(PredictionError, match="Open-Meteo HTTP 429"):
                await fetch_weather_features(-2.0, 112.0)


class TestTerrainHelpers:
    def test_ndvi_default_for_indonesia(self) -> None:
        assert estimate_ndvi(-2.35, 112.46) == 0.4

    def test_land_cover_default_tree_cover(self) -> None:
        assert get_land_cover_class(-2.35, 112.46) == 10


class TestBuildFeatureVector:
    @pytest.mark.asyncio
    async def test_produces_single_row_in_canonical_order(self) -> None:
        with patch(
            "app.services.prediction.feature_builder.fetch_weather_features",
            new=AsyncMock(
                return_value={
                    "wind_speed": 5.0,
                    "wind_direction": 90.0,
                    "humidity": 70.0,
                }
            ),
        ):
            df = await build_feature_vector(_mock_event(), _mock_triage())

        assert list(df.columns) == FEATURE_COLUMNS
        assert len(df) == 1
        assert df["frp"].iloc[0] == 78.3
        assert df["fire_area_ha"].iloc[0] == 12.5

    @pytest.mark.asyncio
    async def test_none_fire_area_defaults_to_zero(self) -> None:
        with patch(
            "app.services.prediction.feature_builder.fetch_weather_features",
            new=AsyncMock(
                return_value={
                    "wind_speed": 1.0,
                    "wind_direction": 10.0,
                    "humidity": 50.0,
                }
            ),
        ):
            df = await build_feature_vector(_mock_event(), _mock_triage(None))

        assert df["fire_area_ha"].iloc[0] == 0.0


class TestRunPrediction:
    @pytest.mark.asyncio
    async def test_clamps_negative_radii_and_normalizes_direction(self) -> None:
        """Model can emit negative radii / out-of-range bearing â€” must be sanitized."""
        import pandas as pd

        fake_df = pd.DataFrame(
            [[5.0, 90.0, 70.0, 0.4, 10.0, 12.5, 78.3]], columns=FEATURE_COLUMNS
        )
        fake_model = MagicMock()
        fake_model.predict.return_value = np.array([[-95.8, -0.5, 0.12, 3.4]])

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync in SQLAlchemy

        with patch(
            "app.services.prediction.prediction_service.build_feature_vector",
            new=AsyncMock(return_value=fake_df),
        ), patch(
            "app.services.prediction.prediction_service.load_model",
            return_value=fake_model,
        ), patch(
            "app.services.prediction.prediction_service.AlertService"
        ) as mock_alert_cls:
            mock_alert_cls.return_value.send_alert = AsyncMock(return_value={})
            pred = await run_prediction(_mock_event(), _mock_triage(), mock_db)

        assert pred.spread_direction_deg == (-95.8 % 360)
        assert pred.radius_6h_km == 0.0     # clamped from -0.5
        assert pred.radius_12h_km == pytest.approx(0.12, rel=1e-3)
        assert pred.radius_24h_km == pytest.approx(3.4, rel=1e-3)
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_inference_failure_raises_prediction_error(self) -> None:
        import pandas as pd

        fake_df = pd.DataFrame(
            [[5.0, 90.0, 70.0, 0.4, 10.0, 12.5, 78.3]], columns=FEATURE_COLUMNS
        )
        fake_model = MagicMock()
        fake_model.predict.side_effect = RuntimeError("bad input")

        with patch(
            "app.services.prediction.prediction_service.build_feature_vector",
            new=AsyncMock(return_value=fake_df),
        ), patch(
            "app.services.prediction.prediction_service.load_model",
            return_value=fake_model,
        ), pytest.raises(PredictionError, match="XGBoost inference failed"):
            await run_prediction(_mock_event(), _mock_triage(), AsyncMock())

    @pytest.mark.asyncio
    async def test_alert_failure_does_not_break_prediction(self) -> None:
        """A failing alert must be logged but must not fail the prediction."""
        import pandas as pd

        fake_df = pd.DataFrame(
            [[5.0, 90.0, 70.0, 0.4, 10.0, 12.5, 78.3]], columns=FEATURE_COLUMNS
        )
        fake_model = MagicMock()
        fake_model.predict.return_value = np.array([[120.0, 1.0, 2.0, 3.0]])

        with patch(
            "app.services.prediction.prediction_service.build_feature_vector",
            new=AsyncMock(return_value=fake_df),
        ), patch(
            "app.services.prediction.prediction_service.load_model",
            return_value=fake_model,
        ), patch(
            "app.services.prediction.prediction_service.AlertService"
        ) as mock_alert_cls:
            mock_alert_cls.return_value.send_alert = AsyncMock(
                side_effect=RuntimeError("telegram down")
            )
            db = AsyncMock()
            db.add = MagicMock()  # db.add is sync in SQLAlchemy
            pred = await run_prediction(_mock_event(), _mock_triage(), db)

        assert pred.spread_direction_deg == 120.0

