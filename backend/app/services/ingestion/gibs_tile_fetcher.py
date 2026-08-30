"""
NASA GIBS WMTS tile fetcher + Cloudflare R2 uploader.
Fetches pre-rendered true-color satellite tiles (~50KB each, no auth required).
FR-02: Fetch satellite imagery for each hotspot.

Why GIBS over Sentinel-2:
  Sentinel-2 = 50-200MB per tile via OAuth.
  GIBS WMTS = ~50KB PNG, direct URL, no auth. (ADR-009)
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import httpx
import structlog
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.core.exceptions import TileNotFoundError

logger = structlog.get_logger()

# GIBS WMTS endpoint — Prioritize VIIRS/MODIS TrueColor daylight imagery
GIBS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"
GIBS_LAYER = "VIIRS_SNPP_CorrectedReflectance_TrueColor"
GIBS_FALLBACK_LAYER = "VIIRS_NOAA20_CorrectedReflectance_TrueColor"
GIBS_ZOOM = 8          # ~1.25km tile footprint, more useful for triage
GIBS_TILE_MATRIX = "250m"

GIBS_CANDIDATE_LAYERS = [
    "VIIRS_SNPP_CorrectedReflectance_TrueColor",
    "VIIRS_NOAA20_CorrectedReflectance_TrueColor",
    "MODIS_Terra_CorrectedReflectance_TrueColor",
    "MODIS_Aqua_CorrectedReflectance_TrueColor",
    "MODIS_Aqua_CorrectedReflectance_Bands721",
]


def _is_black_or_empty_tile(tile_bytes: bytes, min_avg_brightness: float = 12.0) -> bool:
    """
    Check if a returned tile is pitch black, nodata mask, or empty.
    Returns True if the image is valid and mostly black.
    """
    import io

    from PIL import Image, ImageStat

    if not tile_bytes:
        return True
    try:
        im = Image.open(io.BytesIO(tile_bytes))
        stat = ImageStat.Stat(im)
        avg = sum(stat.mean) / len(stat.mean)
        return avg < min_avg_brightness
    except Exception:
        return False



def _lat_lon_to_tile(lat: float, lon: float, zoom: int = GIBS_ZOOM) -> tuple[int, int]:
    """
    Convert WGS84 coordinates to NASA GIBS WMTS EPSG:4326 tile row/col indices.
    For NASA GIBS EPSG:4326 250m resolution:
      - At zoom 3: MatrixWidth = 10, MatrixHeight = 5
      - At zoom z (z >= 3): n_col = 10 * 2^(z-3), n_row = 5 * 2^(z-3)
      - At zoom 8: n_col = 320, n_row = 160
    """
    if zoom >= 3:
        n_col = 10 * (2 ** (zoom - 3))
        n_row = 5 * (2 ** (zoom - 3))
    else:
        n_col = 2 ** zoom
        n_row = max(1, 2 ** (zoom - 1))

    col = int((lon + 180.0) / 360.0 * n_col)
    row = int((90.0 - lat) / 180.0 * n_row)
    # Clamp to valid range
    col = max(0, min(col, n_col - 1))
    row = max(0, min(row, n_row - 1))
    return col, row


def _make_r2_client():  # type: ignore[no-untyped-def]
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.CLOUDFLARE_R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY,
        aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


async def fetch_gibs_tile(
    lat: float,
    lon: float,
    date_str: str,  # Format: YYYY-MM-DD
    event_id: str | None = None,
) -> str | None:
    """
    Fetch a GIBS WMTS tile for the given coordinates and date.
    Tries multiple high-resolution TrueColor satellite layers across candidate dates,
    discarding pitch-black/empty swaths and selecting the clearest daylight pass.
    Uploads to Cloudflare R2 and returns the R2 object key.

    Returns:
        R2 object key (str) on success.
        None if tile is unavailable (HTTP 404 — cloud cover or no data).

    Raises:
        TileNotFoundError: on persistent fetch failure (non-404).
    """
    from datetime import timedelta

    settings = get_settings()
    col, row = _lat_lon_to_tile(lat, lon, GIBS_ZOOM)

    # Candidate dates: primary detection date, then previous day if today's swath is pending
    dates_to_try = [date_str]
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        prev_date = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
        dates_to_try.append(prev_date)
    except ValueError:
        pass

    tile_bytes: bytes | None = None
    chosen_date = date_str

    async with httpx.AsyncClient(timeout=30.0) as client:
        for candidate_date in dates_to_try:
            for layer in GIBS_CANDIDATE_LAYERS:
                url = (
                    f"{GIBS_BASE}/{layer}/default/{candidate_date}"
                    f"/{GIBS_TILE_MATRIX}/{GIBS_ZOOM}/{row}/{col}.jpg"
                )
                logger.info("gibs_tile_fetch_start", lat=lat, lon=lon, date=candidate_date, layer=layer, url=url)
                try:
                    r = await client.get(url)
                    if r.status_code == 200:
                        content = r.content
                        if not _is_black_or_empty_tile(content):
                            tile_bytes = content
                            chosen_date = candidate_date
                            logger.info(
                                "gibs_tile_selected",
                                layer=layer,
                                date=candidate_date,
                                size=len(content),
                            )
                            break
                        logger.info("gibs_tile_black_discarded", layer=layer, date=candidate_date)
                    elif r.status_code == 404:
                        continue
                    else:
                        r.raise_for_status()
                except httpx.RequestError as e:
                    raise TileNotFoundError(f"GIBS network error: {e}") from e
                except httpx.HTTPStatusError as e:
                    raise TileNotFoundError(
                        f"GIBS returned HTTP {e.response.status_code} for {url}"
                    ) from e
            if tile_bytes is not None:
                break

    if tile_bytes is None:
        logger.warning("gibs_tile_unavailable", lat=lat, lon=lon, date=date_str)
        return None


    tile_size = len(tile_bytes)

    # Build R2 key: tiles/{date}/{event_id or coord}_{row}_{col}.jpg
    label = event_id or f"{lat:.4f}_{lon:.4f}"
    r2_key = f"tiles/{chosen_date}/{label}_{row}_{col}.jpg"


    # Upload to R2 — synchronous boto3 call (acceptable in background task context)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(tile_bytes)
        tmp_path = tmp.name

    try:
        s3 = _make_r2_client()
        s3.upload_file(
            tmp_path,
            settings.CLOUDFLARE_R2_BUCKET_NAME,
            r2_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )
    except (BotoCoreError, ClientError) as e:
        logger.error("r2_upload_failed", r2_key=r2_key, error=str(e))
        raise TileNotFoundError(f"R2 upload failed: {e}") from e
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    logger.info(
        "gibs_tile_fetched",
        lat=lat, lon=lon, date=date_str,
        tile_size_bytes=tile_size,
        r2_key=r2_key,
    )
    return r2_key


def get_r2_presigned_url(r2_key: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for temporary read access to an R2 tile.
    Used by the frontend to display the satellite tile image.
    """
    settings = get_settings()
    s3 = _make_r2_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.CLOUDFLARE_R2_BUCKET_NAME, "Key": r2_key},
        ExpiresIn=expires_in,
    )


async def fetch_and_upload_tile(event: Any) -> str | None:
    """
    Helper for FireEvent objects — extracts lat, lon, detected_at, id and calls fetch_gibs_tile.
    """
    lat: float = float(event.lat)
    lon: float = float(event.lon)
    event_id: str = str(event.id)
    detected_at = getattr(event, "detected_at", None)

    if detected_at:
        date_str = detected_at.strftime("%Y-%m-%d")
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return await fetch_gibs_tile(
        lat=lat,
        lon=lon,
        date_str=date_str,
        event_id=event_id,
    )

