"""
Unit tests for the FIRMS event writer (event_writer.py).

Uses the in-memory SQLite session from conftest (db_session fixture)
to exercise real INSERT / duplicate-skip behavior.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fire_event import FireEvent
from app.services.ingestion.event_writer import upsert_fire_events


def _event_dict(firms_id: str = "firms_abc123") -> dict:
    return {
        "firms_id": firms_id,
        "detected_at": datetime.now(timezone.utc),
        "lat": -2.345,
        "lon": 112.456,
        "frp": 55.2,
        "brightness": 320.5,
        "satellite": "NOAA-20",
        "tile_url": None,
    }


class TestUpsertFireEvents:
    @pytest.mark.asyncio
    async def test_empty_input_returns_zero(self, db_session: AsyncSession) -> None:
        new_ids, skipped = await upsert_fire_events([], db_session)
        assert new_ids == []
        assert skipped == 0

    @pytest.mark.asyncio
    async def test_inserts_new_events(self, db_session: AsyncSession) -> None:
        events = [_event_dict("f1"), _event_dict("f2")]
        new_ids, skipped = await upsert_fire_events(events, db_session)

        assert len(new_ids) == 2
        assert skipped == 0

        rows = (await db_session.execute(select(FireEvent))).scalars().all()
        assert len(rows) == 2
        assert all(r.status == "PENDING" for r in rows)

    @pytest.mark.asyncio
    async def test_skips_duplicate_firms_ids(self, db_session: AsyncSession) -> None:
        await upsert_fire_events([_event_dict("dup1")], db_session)

        # Second batch: one duplicate + one new
        new_ids, skipped = await upsert_fire_events(
            [_event_dict("dup1"), _event_dict("new1")], db_session
        )

        assert len(new_ids) == 1
        assert skipped == 1

    @pytest.mark.asyncio
    async def test_all_duplicates_returns_empty(self, db_session: AsyncSession) -> None:
        await upsert_fire_events([_event_dict("x1"), _event_dict("x2")], db_session)
        new_ids, skipped = await upsert_fire_events(
            [_event_dict("x1"), _event_dict("x2")], db_session
        )
        assert new_ids == []
        assert skipped == 2

    @pytest.mark.asyncio
    async def test_returned_ids_are_valid_uuids(self, db_session: AsyncSession) -> None:
        import uuid as uuid_mod

        new_ids, _ = await upsert_fire_events([_event_dict("u1")], db_session)
        parsed = uuid_mod.UUID(new_ids[0])  # raises if invalid
        assert str(parsed) == new_ids[0]
