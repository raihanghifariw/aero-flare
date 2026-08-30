"""
Unit tests for Celery tasks and Celery-backed Ingestion API endpoints.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fire_event import FireEvent
from app.models.prediction import Prediction
from app.models.triage_report import TriageReport
from app.workers.tasks import (
    _async_ingest_firms,
    _async_process_event,
    ingest_firms_task,
    process_event_task,
)
from tests.conftest import TestSessionLocal


def test_process_event_task_wrapper() -> None:
    """Test process_event_task invokes _async_process_event and returns result."""
    dummy_result = {
        "event_id": "00000000-0000-0000-0000-000000000001",
        "danger_level": "CRITICAL",
        "classification": "CONFIRMED_FIRE",
        "prediction_id": "00000000-0000-0000-0000-000000000002",
    }
    with patch("app.workers.tasks.asyncio.run", return_value=dummy_result):
        res = process_event_task("00000000-0000-0000-0000-000000000001")
        assert res == dummy_result


def test_ingest_firms_task_wrapper() -> None:
    """Test ingest_firms_task dispatches individual process_event_task per event."""
    dummy_ingest = {
        "events_created": 2,
        "events_skipped": 0,
        "new_event_ids": ["id-1", "id-2"],
    }
    with (
        patch("app.workers.tasks.asyncio.run", return_value=dummy_ingest),
        patch("app.workers.tasks.process_event_task.delay") as mock_delay,
    ):
        res = ingest_firms_task(source="test_runner")
        assert res["events_created"] == 2
        assert res["enqueued_jobs"] == 2
        assert mock_delay.call_count == 2


@pytest.mark.asyncio
async def test_trigger_ingestion_api_celery(client: AsyncClient) -> None:
    """Test POST /api/v1/ingestion/trigger dispatches Celery task."""
    mock_celery_task = MagicMock()
    mock_celery_task.id = "celery-job-12345"

    with patch("app.api.v1.ingestion.ingest_firms_task.delay", return_value=mock_celery_task):
        response = await client.post("/api/v1/ingestion/trigger")

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        assert body["job_id"] == "celery-job-12345"


@pytest.mark.asyncio
async def test_get_ingestion_status_api_celery(client: AsyncClient) -> None:
    """Test GET /api/v1/ingestion/status/{job_id} reads AsyncResult from Celery."""
    mock_async_result = MagicMock()
    mock_async_result.state = "SUCCESS"
    mock_async_result.successful.return_value = True
    mock_async_result.failed.return_value = False
    mock_async_result.result = {"events_created": 5, "enqueued_jobs": 5}

    with patch("app.api.v1.ingestion.AsyncResult", return_value=mock_async_result):
        response = await client.get("/api/v1/ingestion/status/celery-job-12345")

        assert response.status_code == 200
        body = response.json()
        assert body["job_id"] == "celery-job-12345"
        assert body["status"] == "completed"
        assert body["result"] == {"events_created": 5, "enqueued_jobs": 5}


@pytest.mark.asyncio
async def test_async_process_event_flow(db_session: AsyncSession) -> None:
    """Test _async_process_event end-to-end with mocks."""
    event = FireEvent(
        id=uuid.uuid4(),
        firms_id="firms_async_test",
        detected_at=datetime.now(timezone.utc),
        lat=-2.0,
        lon=112.0,
        frp=60.0,
        brightness=320.0,
        satellite="NOAA-20",
        status="PENDING",
    )
    db_session.add(event)
    await db_session.commit()

    mock_triage = TriageReport(
        id=uuid.uuid4(),
        event_id=event.id,
        classification="CONFIRMED_FIRE",
        danger_level=5,
        confidence=0.95,
        triage_source="VLM",
        summary="Active flame",
        recommended_action="DISPATCH",
    )
    mock_pred = Prediction(
        id=uuid.uuid4(),
        event_id=event.id,
        spread_direction_deg=45.0,
        radius_6h_km=2.5,
        radius_12h_km=5.0,
        radius_24h_km=10.0,
        wind_speed=15.0,
        wind_direction=45.0,
        humidity=65.0,
        model_version="1.0.0",
        predicted_at=datetime.now(timezone.utc),
    )

    with (
        patch("app.workers.tasks.async_session_factory", TestSessionLocal),
        patch("app.workers.tasks.fetch_and_upload_tile", AsyncMock(return_value="tiles/test.png")),
        patch("app.workers.tasks.run_triage", AsyncMock(return_value=mock_triage)),
        patch("app.workers.tasks.run_prediction", AsyncMock(return_value=mock_pred)),
        patch("app.workers.tasks.cache.delete_pattern", AsyncMock()),
    ):
        res = await _async_process_event(str(event.id))
        assert res["event_id"] == str(event.id)
        assert res["classification"] == "CONFIRMED_FIRE"
        assert res["danger_level"] == 5
        assert res["prediction_id"] == str(mock_pred.id)


@pytest.mark.asyncio
async def test_async_ingest_firms_flow() -> None:
    """Test _async_ingest_firms flow."""
    with (
        patch("app.workers.tasks.fetch_firms_data", AsyncMock(return_value="data/sample.csv")),
        patch("app.workers.tasks.parse_firms_csv", return_value=[{}]),
        patch("app.workers.tasks.async_session_factory", TestSessionLocal),
        patch("app.workers.tasks.upsert_fire_events", AsyncMock(return_value=([uuid.uuid4()], 0))),
        patch("app.workers.tasks.cache.delete_pattern", AsyncMock()),
    ):
        res = await _async_ingest_firms(trigger_source="unit_test")
        assert res["events_created"] == 1
        assert len(res["new_event_ids"]) == 1


@pytest.mark.asyncio
async def test_worker_handle_job_flow() -> None:
    """Test handle_job from worker.py."""
    from app.workers.worker import handle_job

    sem = asyncio.Semaphore(1)
    job = {
        "job_id": "test-job-1",
        "task_name": "process_event",
        "payload": {"event_id": str(uuid.uuid4())},
    }

    with (
        patch("app.workers.worker._async_process_event", AsyncMock(return_value={"status": "ok"})),
        patch("app.workers.worker.task_queue.update_job_status", AsyncMock()) as mock_update,
    ):
        await handle_job(job, sem)
        assert mock_update.call_count == 2  # running, then completed


