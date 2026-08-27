"""
Unit tests for the NASA GIBS tile fetcher (gibs_tile_fetcher.py).

Covers:
- _lat_lon_to_tile: WGS84 -> WMTS EPSG:4326 tile row/col math
- fetch_gibs_tile: success path (upload to R2), 404 (unavailable), network/HTTP errors
- get_r2_presigned_url: delegates to boto3 client
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import TileNotFoundError
from app.services.ingestion.gibs_tile_fetcher import (
    GIBS_ZOOM,
    _lat_lon_to_tile,
    fetch_gibs_tile,
    get_r2_presigned_url,
)


class TestLatLonToTile:
    def test_equator_prime_meridian_is_center_tile(self) -> None:
        """(0, 0) should map to the center column, top-of-bottom-half row."""
        col, row = _lat_lon_to_tile(0.0, 0.0, GIBS_ZOOM)
        n_col = 2**GIBS_ZOOM
        n_row = 2 ** (GIBS_ZOOM - 1)
        assert col == n_col // 2
        assert row == n_row // 2

    def test_extreme_coordinates_are_clamped(self) -> None:
        """North pole / antimeridian must clamp into valid tile range, not overflow."""
        col, row = _lat_lon_to_tile(90.0, 180.0, GIBS_ZOOM)
        n_col = 2**GIBS_ZOOM
        n_row = 2 ** (GIBS_ZOOM - 1)
        assert 0 <= col < n_col
        assert 0 <= row < n_row

    def test_south_pole_west_antimeridian_clamped(self) -> None:
        col, row = _lat_lon_to_tile(-90.0, -180.0, GIBS_ZOOM)
        assert col == 0
        assert row == (2 ** (GIBS_ZOOM - 1)) - 1

    def test_indonesia_coordinates_produce_valid_tile(self) -> None:
        """Sanity check for a real Kalimantan hotspot coordinate."""
        col, row = _lat_lon_to_tile(-2.345, 112.456, GIBS_ZOOM)
        n_col = 2**GIBS_ZOOM
        n_row = 2 ** (GIBS_ZOOM - 1)
        assert 0 <= col < n_col
        assert 0 <= row < n_row


class TestFetchGibsTile:
    @pytest.mark.asyncio
    async def test_returns_none_on_404(self) -> None:
        """A 404 from GIBS means no tile for that date/location — not an error."""
        mock_resp = MagicMock(status_code=404)
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await fetch_gibs_tile(-2.0, 112.0, "2026-01-01")
            assert result is None

    @pytest.mark.asyncio
    async def test_raises_tile_not_found_on_network_error(self) -> None:
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("connection refused")
            )
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TileNotFoundError, match="GIBS network error"):
                await fetch_gibs_tile(-2.0, 112.0, "2026-01-01")

    @pytest.mark.asyncio
    async def test_raises_tile_not_found_on_http_error(self) -> None:
        mock_resp = MagicMock(status_code=500)
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "server error", request=MagicMock(), response=mock_resp
        )
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TileNotFoundError, match="GIBS returned HTTP 500"):
                await fetch_gibs_tile(-2.0, 112.0, "2026-01-01")

    @pytest.mark.asyncio
    async def test_success_uploads_to_r2_and_returns_key(self) -> None:
        """Happy path: 200 response -> uploaded to R2 -> returns the object key."""
        mock_resp = MagicMock(status_code=200, content=b"\xff\xd8fake-jpeg-bytes")
        mock_resp.raise_for_status = MagicMock()

        mock_s3 = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls, patch(
            "app.services.ingestion.gibs_tile_fetcher._make_r2_client",
            return_value=mock_s3,
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await fetch_gibs_tile(
                -2.345, 112.456, "2026-01-15", event_id="evt-123"
            )

        assert result is not None
        assert result.startswith("tiles/2026-01-15/evt-123_")
        assert result.endswith(".jpg")
        mock_s3.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_without_event_id_uses_coord_label(self) -> None:
        mock_resp = MagicMock(status_code=200, content=b"data")
        mock_resp.raise_for_status = MagicMock()
        mock_s3 = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls, patch(
            "app.services.ingestion.gibs_tile_fetcher._make_r2_client",
            return_value=mock_s3,
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await fetch_gibs_tile(-2.345, 112.456, "2026-01-15")

        assert result is not None
        assert "-2.3450_112.4560" in result

    @pytest.mark.asyncio
    async def test_raises_tile_not_found_on_r2_upload_failure(self) -> None:
        mock_resp = MagicMock(status_code=200, content=b"data")
        mock_resp.raise_for_status = MagicMock()
        mock_s3 = MagicMock()
        mock_s3.upload_file.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "denied"}}, "PutObject"
        )

        with patch("httpx.AsyncClient") as mock_client_cls, patch(
            "app.services.ingestion.gibs_tile_fetcher._make_r2_client",
            return_value=mock_s3,
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(TileNotFoundError, match="R2 upload failed"):
                await fetch_gibs_tile(-2.0, 112.0, "2026-01-01")


class TestGetR2PresignedUrl:
    def test_delegates_to_boto3_client(self) -> None:
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://r2.example.com/signed"

        with patch(
            "app.services.ingestion.gibs_tile_fetcher._make_r2_client",
            return_value=mock_s3,
        ):
            url = get_r2_presigned_url("tiles/2026-01-01/foo.jpg", expires_in=1800)

        assert url == "https://r2.example.com/signed"
        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": mock_s3.generate_presigned_url.call_args.kwargs["Params"][
                    "Bucket"
                ],
                "Key": "tiles/2026-01-01/foo.jpg",
            },
            ExpiresIn=1800,
        )
