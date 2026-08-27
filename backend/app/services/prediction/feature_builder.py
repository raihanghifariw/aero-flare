"""
Feature builder for XGBoost fire spread prediction.
Fetches weather from Open-Meteo (free, no key) and computes the full feature vector.
FR-08: XGBoost features from weather + terrain.
"""
from __future__ import annotations

import functools

import httpx
import pandas as pd
import structlog

from app.core.exceptions import PredictionError
from app.models.fire_event import FireEvent
from app.models.triage_report import TriageReport

logger = structlog.get_logger()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Canonical feature column order — must match training schema exactly
FEATURE_COLUMNS = [
    "wind_speed",
    "wind_direction",
    "humidity",
    "ndvi",
    "land_cover",
    "fire_area_ha",
    "frp",
]


async def fetch_weather_features(lat: float, lon: float) -> dict[str, float]:
    """
    Fetch current weather for a coordinate from Open-Meteo (free, no API key).

    Returns:
        {"wind_speed": float, "wind_direction": float, "humidity": float}
    Raises:
        PredictionError: if the request fails.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "wind_speed_10m,wind_direction_10m,relative_humidity_2m",
        "wind_speed_unit": "ms",
        "forecast_days": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise PredictionError(f"Open-Meteo HTTP {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise PredictionError(f"Open-Meteo network error: {e}") from e

    data = resp.json().get("current", {})
    return {
        "wind_speed": float(data.get("wind_speed_10m", 3.0)),
        "wind_direction": float(data.get("wind_direction_10m", 180.0)),
        "humidity": float(data.get("relative_humidity_2m", 60.0)),
    }


@functools.lru_cache(maxsize=512)
def estimate_ndvi(lat_2dp: float, lon_2dp: float) -> float:
    """
    Estimate NDVI for a location using a simple tropical biome lookup.
    Default 0.4 = tropical mixed forest/shrubland (conservative for Indonesia).

    v1.0 limitation: static default. v1.1 will use Sentinel-2 derived NDVI.
    Cached by (lat, lon) truncated to 2 decimal places.
    """
    # Indonesia is almost entirely tropical — 0.4 is a safe conservative default
    # Higher values (dense forest) = more fuel = faster spread
    _ = lat_2dp, lon_2dp  # future: lookup from cached geotiff
    return 0.4


@functools.lru_cache(maxsize=512)
def get_land_cover_class(lat_2dp: float, lon_2dp: float) -> int:
    """
    Return ESA World Cover land cover class code for a coordinate.
    Default 10 = Tree Cover (tropical forest, dominant in Kalimantan/Sumatra).

    ESA codes: 10=Tree Cover, 20=Shrubland, 30=Grassland, 40=Cropland,
               50=Built-up, 60=Bare/Sparse, 80=Permanent Water, 90=Wetland
    """
    _ = lat_2dp, lon_2dp  # future: lookup from cached geojson
    return 10


async def build_feature_vector(
    event: FireEvent,
    triage: TriageReport,
) -> pd.DataFrame:
    """
    Build the full feature vector for XGBoost inference.

    Returns:
        Single-row DataFrame with columns in FEATURE_COLUMNS order.
    Raises:
        PredictionError: if weather fetch fails.
    """
    weather = await fetch_weather_features(event.lat, event.lon)

    lat_2dp = round(event.lat, 2)
    lon_2dp = round(event.lon, 2)

    features = {
        "wind_speed": weather["wind_speed"],
        "wind_direction": weather["wind_direction"],
        "humidity": weather["humidity"],
        "ndvi": estimate_ndvi(lat_2dp, lon_2dp),
        "land_cover": float(get_land_cover_class(lat_2dp, lon_2dp)),
        "fire_area_ha": triage.fire_area_ha if triage.fire_area_ha is not None else 0.0,
        "frp": event.frp if event.frp is not None else 0.0,
    }

    df = pd.DataFrame([features], columns=FEATURE_COLUMNS)

    if list(df.columns) != FEATURE_COLUMNS:
        raise PredictionError(
            f"Feature column mismatch: got {list(df.columns)}, expected {FEATURE_COLUMNS}"
        )

    logger.info(
        "feature_vector_built",
        event_id=str(event.id),
        wind_speed=features["wind_speed"],
        frp=features["frp"],
    )
    return df
