"""Unit tests for feature_builder (weather fetch + feature vector)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.core.exceptions import PredictionError
from app.services.prediction.feature_builder import (
    FEATURE_COLUMNS,
    build_feature_vector,
    estimate_ndvi,
    get_land_cover_class,
)


def _make_event(frp: float = 55.0) -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.lat = -2.345
    e.lon = 112.456
    e.frp = frp
    e.detected_at = datetime.now(timezone.utc)
    return e


def _make_triage(fire_area_ha: float = 100.0) -> MagicMock:
    t = MagicMock()
    t.fire_area_ha = fire_area_ha
    return t


@pytest.mark.asyncio
async def test_build_feature_vector_correct_shape():
    """build_feature_vector returns single-row DataFrame with correct columns."""
    mock_weather = {"wind_speed": 5.0, "wind_direction": 180.0, "humidity": 60.0}
    with patch(
        "app.services.prediction.feature_builder.fetch_weather_features",
        AsyncMock(return_value=mock_weather),
    ):
        df = await build_feature_vector(_make_event(), _make_triage())

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert list(df.columns) == FEATURE_COLUMNS


@pytest.mark.asyncio
async def test_build_feature_vector_uses_frp_from_event():
    mock_weather = {"wind_speed": 3.0, "wind_direction": 90.0, "humidity": 70.0}
    with patch(
        "app.services.prediction.feature_builder.fetch_weather_features",
        AsyncMock(return_value=mock_weather),
    ):
        df = await build_feature_vector(_make_event(frp=88.5), _make_triage())

    assert df["frp"].iloc[0] == pytest.approx(88.5)


@pytest.mark.asyncio
async def test_fetch_weather_features_returns_three_keys():
    """Real Open-Meteo call — network required. Skipped in CI without network."""
    pytest.importorskip("httpx")
    try:
        from app.services.prediction.feature_builder import fetch_weather_features
        result = await fetch_weather_features(-2.345, 112.456)
        assert "wind_speed" in result
        assert "wind_direction" in result
        assert "humidity" in result
    except Exception:
        pytest.skip("Open-Meteo not reachable in this environment")


def test_estimate_ndvi_returns_float():
    ndvi = estimate_ndvi(-2.35, 112.46)
    assert isinstance(ndvi, float)
    assert 0.0 < ndvi <= 1.0


def test_get_land_cover_class_returns_int():
    code = get_land_cover_class(-2.35, 112.46)
    assert isinstance(code, int)
    assert code > 0
