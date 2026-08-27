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
) -> str:
    """
    Download latest VIIRS SNPP NRT hotspot data for Indonesia's bounding box.

    Returns:
        Filepath of the saved CSV file.
    Raises:
        IngestionError: if the HTTP request fails.
    """
    url = f"{FIRMS_BASE_URL}/area/csv/{api_key}/VIIRS_SNPP_NRT/{area}/{days}"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = os.path.join(output_dir, f"firms_{timestamp}.csv")

    logger.info("firms_fetch_start", url=url.replace(api_key, "***"), area=area)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise IngestionError(
            f"FIRMS API returned HTTP {e.response.status_code}"
        ) from e
    except httpx.RequestError as e:
        raise IngestionError(f"FIRMS API request failed: {e}") from e

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(resp.text)

    logger.info(
        "firms_fetch_complete",
        filepath=output_path,
        bytes=len(resp.content),
        lines=resp.text.count("\n"),
    )
    return output_path
