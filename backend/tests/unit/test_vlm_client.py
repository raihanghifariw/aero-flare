"""
Unit tests for the Ollama VLM client (vlm_client.py).

Covers:
- call_vlm: success, HTTP error (TriageError), network error with tenacity retry
- check_ollama_reachable: reachable / unreachable / exception paths
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import TriageError
from app.services.triage.vlm_client import call_vlm, check_ollama_reachable


@pytest.fixture
def tile_file(tmp_path: Path) -> Path:
    p = tmp_path / "tile.jpg"
    p.write_bytes(b"\xff\xd8fake-jpeg")
    return p


class TestCallVlm:
    @pytest.mark.asyncio
    async def test_success_returns_response_text(self, tile_file: Path) -> None:
        mock_resp = MagicMock(status_code=200)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": '{"classification": "CONFIRMED_FIRE"}'}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            raw = await call_vlm(
                image_path=tile_file,
                prompt="Analyze this tile.",
                model="qwen2-vl:7b",
                base_url="http://localhost:11434",
            )

        assert raw == '{"classification": "CONFIRMED_FIRE"}'
        # Payload must include base64 image and non-streaming mode
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["model"] == "qwen2-vl:7b"
        assert payload["stream"] is False
        assert len(payload["images"]) == 1

    @pytest.mark.asyncio
    async def test_http_error_raises_triage_error(self, tile_file: Path) -> None:
        mock_resp = MagicMock(status_code=500)
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "boom", request=MagicMock(), response=mock_resp
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises((TriageError, httpx.HTTPStatusError)):
                await call_vlm(
                    image_path=tile_file,
                    prompt="p",
                    model="qwen2-vl:7b",
                    base_url="http://localhost:11434",
                )

    @pytest.mark.asyncio
    async def test_network_error_retries_then_reraises(self, tile_file: Path) -> None:
        """tenacity must retry httpx.RequestError 3 times, then re-raise."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(httpx.ConnectError):
                await call_vlm(
                    image_path=tile_file,
                    prompt="p",
                    model="qwen2-vl:7b",
                    base_url="http://localhost:11434",
                )

            # 3 attempts (stop_after_attempt(3))
            assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_empty_response_field_returns_empty_string(
        self, tile_file: Path
    ) -> None:
        mock_resp = MagicMock(status_code=200)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {}  # missing "response" key

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            raw = await call_vlm(
                image_path=tile_file,
                prompt="p",
                model="m",
                base_url="http://localhost:11434",
            )
        assert raw == ""


class TestCheckOllamaReachable:
    @pytest.mark.asyncio
    async def test_returns_true_on_200(self) -> None:
        mock_resp = MagicMock(status_code=200)
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            assert await check_ollama_reachable("http://localhost:11434") is True

    @pytest.mark.asyncio
    async def test_returns_false_on_non_200(self) -> None:
        mock_resp = MagicMock(status_code=503)
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            assert await check_ollama_reachable("http://localhost:11434") is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self) -> None:
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            assert await check_ollama_reachable("http://localhost:11434") is False
