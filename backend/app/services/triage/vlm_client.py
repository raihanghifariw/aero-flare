"""
Ollama VLM HTTP client with tenacity retry.
FR-04: VLM classification of satellite tiles.
"""
from __future__ import annotations

import base64
from pathlib import Path

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import TriageError
from app.schemas.common import get_trace_id

logger = structlog.get_logger()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
async def call_vlm(
    image_path: str | Path,
    prompt: str,
    model: str,
    base_url: str,
) -> str:
    """
    Send a satellite tile image + prompt to Ollama and return the raw text response.

    Args:
        image_path: Local path to the JPEG/PNG tile.
        prompt: System + user prompt string.
        model: Ollama model name, e.g. 'qwen2-vl:7b'.
        base_url: Ollama base URL, e.g. 'http://localhost:11434'.

    Returns:
        Raw text response from the VLM.

    Raises:
        TriageError: on HTTP error or non-200 response.
    """
    # Base64-encode the image
    image_bytes = Path(image_path).read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{base_url}/api/generate", json=payload)
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            "vlm_call_http_error",
            status_code=e.response.status_code,
            model=model,
            trace_id=get_trace_id(),
        )
        raise TriageError(f"VLM HTTP error {e.response.status_code}") from e
    except httpx.RequestError as e:
        logger.error("vlm_call_network_error", model=model, error=str(e), trace_id=get_trace_id())
        raise

    data = resp.json()
    raw_text: str = data.get("response", "")

    logger.info(
        "vlm_call_success",
        model=model,
        response_chars=len(raw_text),
        trace_id=get_trace_id(),
    )
    return raw_text


async def check_ollama_reachable(base_url: str) -> bool:
    """Return True if Ollama is reachable at the given base URL."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
