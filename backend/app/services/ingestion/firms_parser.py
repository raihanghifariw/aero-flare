"""
FIRMS CSV parser and API fetcher.
Parses NASA VIIRS/MODIS hotspot CSV data into normalized fire event dicts.
FR-01: Pull FIRMS data for Indonesia bounding box.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd
import structlog

from app.core.exceptions import IngestionError

logger = structlog.get_logger()

REQUIRED_COLUMNS = {
    "latitude", "longitude", "brightness", "frp",
    "acq_date", "acq_time", "satellite",
}

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api"
INDONESIA_BBOX = "95,-11,141,6"


def parse_firms_csv(filepath: str) -> list[dict]:
    """
    Parse a FIRMS CSV file into a list of normalized event dicts.

    Deduplication key: (lat rounded to 2dp, lon rounded to 2dp, acq_date, satellite).
    This eliminates overlapping multi-pass detections of the same hotspot.

    Raises:
        IngestionError: if required columns are missing or file is unreadable.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise IngestionError(f"Failed to read FIRMS CSV at {filepath}: {e}") from e

    # FIRMS area downloads expose VIIRS brightness as bright_ti4.
    df.columns = df.columns.str.lower()
    if "brightness" not in df.columns and "bright_ti4" in df.columns:
        df = df.rename(columns={"bright_ti4": "brightness"})

    missing = REQUIRED_COLUMNS - set(df.columns.str.lower())
    if missing:
        raise IngestionError(
            f"FIRMS CSV missing required columns: {missing}. "
            f"Found: {list(df.columns)}"
        )

    # Parse detected_at from acq_date (YYYY-MM-DD) + acq_time (HHMM)
    def _parse_dt(row: pd.Series) -> datetime:
        time_str = str(int(row["acq_time"])).zfill(4)
        dt_str = f"{row['acq_date']} {time_str[:2]}:{time_str[2:]}"
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

    df["detected_at"] = df.apply(_parse_dt, axis=1)

    # Deduplication key
    df["lat_2dp"] = df["latitude"].round(2)
    df["lon_2dp"] = df["longitude"].round(2)
    df = df.drop_duplicates(subset=["lat_2dp", "lon_2dp", "acq_date", "satellite"])

    # Build firms_id: unique key per hotspot
    df["firms_id"] = (
        df["lat_2dp"].astype(str) + "_"
        + df["lon_2dp"].astype(str) + "_"
        + df["acq_date"].astype(str) + "_"
        + df["satellite"].astype(str)
    )

    records = []
    for _, row in df.iterrows():
        records.append({
            "firms_id": row["firms_id"],
            "detected_at": row["detected_at"],
            "lat": float(row["latitude"]),
            "lon": float(row["longitude"]),
            "frp": float(row["frp"]) if pd.notna(row["frp"]) else None,
            "brightness": float(row["brightness"]) if pd.notna(row["brightness"]) else None,
            "satellite": str(row["satellite"]),
        })

    logger.info(
        "firms_csv_parsed",
        filepath=filepath,
        raw_rows=len(df),
        deduped_events=len(records),
    )
    return records


async def fetch_firms_data(
    api_key: str,
    area: str = INDONESIA_BBOX,
    days: int = 1,
    output_dir: str = "data/firms",
    max_retries: int = 3,
) -> str:
    """
    Download latest VIIRS/MODIS NRT hotspot data for Indonesia with automatic
    retries, exponential backoff, and country/sensor fallbacks.

    Returns:
        Filepath of the saved CSV file.
    Raises:
        IngestionError: if all retry attempts and fallback endpoints fail.
    """
    if not api_key:
        raise IngestionError("FIRMS_API_KEY is not set or empty in environment.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = os.path.join(output_dir, f"firms_{timestamp}.csv")

    # Candidate endpoints to try (Primary BBox -> Country IDN fallback -> NOAA-20 VIIRS fallback)
    candidate_urls = [
        f"{FIRMS_BASE_URL}/area/csv/{api_key}/VIIRS_SNPP_NRT/{area}/{days}",
        f"{FIRMS_BASE_URL}/country/csv/{api_key}/VIIRS_SNPP_NRT/IDN/{days}",
        f"{FIRMS_BASE_URL}/area/csv/{api_key}/VIIRS_NOAA20_NRT/{area}/{days}",
    ]

    timeout_config = httpx.Timeout(connect=25.0, read=90.0, write=25.0, pool=25.0)
    headers = {
        "User-Agent": "AeroFlare-Wildfire-Triage/1.0 (NASA EOSDIS Client; Indonesia Ops)",
        "Accept": "text/csv, application/json, text/plain, */*",
    }

    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=timeout_config, follow_redirects=True, headers=headers) as client:
        for url_idx, url in enumerate(candidate_urls, 1):
            sanitized_url = url.replace(api_key, "***")
            logger.info(
                "firms_fetch_attempt_endpoint",
                endpoint_index=url_idx,
                total_endpoints=len(candidate_urls),
                url=sanitized_url,
            )

            for attempt in range(1, max_retries + 1):
                try:
                    logger.info("firms_fetch_send", attempt=attempt, max_retries=max_retries, url=sanitized_url)
                    resp = await client.get(url)

                    # Check for FIRMS rate limit or maintenance responses
                    if resp.status_code == 200:
                        content_text = resp.text.strip()
                        # If NASA returns an error message inside 200 text (e.g. invalid key or no data)
                        if "Invalid MAP_KEY" in content_text or "Bad request" in content_text:
                            raise IngestionError(f"NASA FIRMS API rejected key or request: {content_text}")

                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(resp.text)

                        logger.info(
                            "firms_fetch_complete",
                            filepath=output_path,
                            bytes=len(resp.content),
                            lines=resp.text.count("\n"),
                            attempt=attempt,
                        )
                        return output_path

                    if resp.status_code in (429, 500, 502, 503, 504):
                        logger.warning(
                            "firms_fetch_server_status",
                            status_code=resp.status_code,
                            attempt=attempt,
                            url=sanitized_url,
                        )
                    else:
                        resp.raise_for_status()

                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError, httpx.RequestError) as e:
                    last_error = e
                    logger.warning(
                        "firms_fetch_transient_error",
                        error_type=type(e).__name__,
                        error_msg=str(e),
                        attempt=attempt,
                        url=sanitized_url,
                    )
                except httpx.HTTPStatusError as e:
                    last_error = e
                    logger.warning(
                        "firms_fetch_http_error",
                        status_code=e.response.status_code,
                        attempt=attempt,
                        url=sanitized_url,
                    )

                # Exponential backoff before next retry on same endpoint
                if attempt < max_retries:
                    backoff = 2 ** attempt
                    logger.info("firms_fetch_backoff_sleep", seconds=backoff)
                    await asyncio.sleep(backoff)

    raise IngestionError(
        f"FIRMS API request failed after {len(candidate_urls)} endpoints and retries: {last_error}"
    ) from last_error

