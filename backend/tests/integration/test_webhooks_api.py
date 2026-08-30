"""
Integration tests for Webhooks API (POST /api/v1/webhooks/register).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_webhook_success(client: AsyncClient) -> None:
    payload = {
        "url": "https://example.com/webhook",
        "secret": "my-secret-key-123",
    }
    response = await client.post("/api/v1/webhooks/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["url"] == "https://example.com/webhook"
    assert "registered" in data["message"]
