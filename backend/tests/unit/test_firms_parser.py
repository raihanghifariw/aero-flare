"""Unit tests for FIRMS CSV parser."""
from __future__ import annotations

import os
import textwrap
from datetime import timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import IngestionError
from app.services.ingestion.firms_parser import fetch_firms_data, parse_firms_csv

VALID_CSV = textwrap.dedent("""\
    latitude,longitude,brightness,frp,acq_date,acq_time,satellite,confidence
    -2.345,112.456,320.5,55.2,2024-07-01,1430,NOAA-20,nominal
    -2.346,112.457,310.1,48.0,2024-07-01,1430,NOAA-20,nominal
    -5.100,115.200,295.0,12.3,2024-07-01,0600,TERRA,low
    -2.345,112.456,321.0,56.1,2024-07-01,1430,NOAA-20,nominal
""")

MISSING_COLUMN_CSV = textwrap.dedent("""\
    latitude,longitude,brightness,acq_date,acq_time,satellite
    -2.345,112.456,320.5,2024-07-01,1430,NOAA-20
""")


@pytest.fixture
def valid_csv_file(tmp_path):
    p = tmp_path / "firms_test.csv"
    p.write_text(VALID_CSV)
    return str(p)


@pytest.fixture
def missing_col_csv_file(tmp_path):
    p = tmp_path / "firms_missing.csv"
    p.write_text(MISSING_COLUMN_CSV)
    return str(p)


def test_parse_firms_csv_returns_event_list(valid_csv_file):
    events = parse_firms_csv(valid_csv_file)
    assert isinstance(events, list)
    assert len(events) > 0


def test_parse_firms_csv_deduplicates_same_location(valid_csv_file):
    """Rows with same lat_2dp/lon_2dp/date/satellite should be deduplicated."""
    events = parse_firms_csv(valid_csv_file)
    # Row 0 and Row 3 are the same hotspot (same rounded coords, date, satellite)
    firms_ids = [e["firms_id"] for e in events]
    assert len(firms_ids) == len(set(firms_ids)), "Duplicate firms_ids found"


def test_parse_firms_csv_parses_detected_at(valid_csv_file):
    events = parse_firms_csv(valid_csv_file)
    for e in events:
        assert e["detected_at"].tzinfo == timezone.utc


def test_parse_firms_csv_extracts_frp(valid_csv_file):
    events = parse_firms_csv(valid_csv_file)
    frps = [e["frp"] for e in events if e["frp"] is not None]
    assert len(frps) > 0
    assert all(isinstance(f, float) for f in frps)


def test_parse_firms_csv_missing_column_raises_ingestion_error(missing_col_csv_file):
    with pytest.raises(IngestionError, match="missing required columns"):
        parse_firms_csv(missing_col_csv_file)


def test_parse_firms_csv_missing_file_raises_ingestion_error():
    with pytest.raises(IngestionError, match="Failed to read FIRMS CSV"):
        parse_firms_csv("/nonexistent/path/firms.csv")


@pytest.mark.asyncio
async def test_fetch_firms_data_success(tmp_path):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = VALID_CSV
    mock_resp.content = VALID_CSV.encode("utf-8")

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        out_path = await fetch_firms_data(
            api_key="test_key",
            output_dir=str(tmp_path),
        )
        assert os.path.exists(out_path)
        with open(out_path, encoding="utf-8") as f:
            content = f.read()
        assert "latitude" in content


@pytest.mark.asyncio
async def test_fetch_firms_data_raises_without_api_key():
    with pytest.raises(IngestionError, match="FIRMS_API_KEY is not set"):
        await fetch_firms_data(api_key="")


