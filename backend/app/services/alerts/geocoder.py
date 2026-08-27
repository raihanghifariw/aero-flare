"""
Reverse geocoder — converts lat/lon to human-readable location name.
Uses Nominatim (OpenStreetMap) — free, no API key.
Results cached in-memory with lru_cache to avoid redundant requests.
"""
from __future__ import annotations

import functools

import httpx
import structlog

logger = structlog.get_logger()

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "AeroFlare/1.0 (fire detection system; contact: admin@aeroflare.local)"


def _truncate(coord: float) -> float:
    """Truncate coordinate to 2 decimal places for cache key (~1km grid)."""
    return round(coord, 2)


@functools.lru_cache(maxsize=512)
def _cached_geocode(lat_2dp: float, lon_2dp: float) -> str:
    """
    Synchronous cached geocode call (lru_cache requires sync function).
    Cache key: (lat, lon) truncated to 2 decimal places.
    """
    try:
        import httpx as _httpx
        with _httpx.Client(timeout=10.0) as client:
            resp = client.get(
                NOMINATIM_URL,
                params={"format": "json", "lat": lat_2dp, "lon": lon_2dp},
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
            addr = data.get("address", {})
            parts = [
                addr.get("state") or addr.get("county") or addr.get("city"),
                addr.get("country"),
            ]
            location = ", ".join(p for p in parts if p)
            return location or f"{lat_2dp:.3f}, {lon_2dp:.3f}"
    except Exception as e:
        logger.warning("geocode_failed", lat=lat_2dp, lon=lon_2dp, error=str(e))
        return f"{lat_2dp:.3f}, {lon_2dp:.3f}"


async def reverse_geocode(lat: float, lon: float) -> str:
    """
    Return a human-readable location name for the given coordinates.
    Caches results by (lat, lon) truncated to 2 decimal places.
    Falls back to coordinate string on any error.
    """
    return _cached_geocode(_truncate(lat), _truncate(lon))
