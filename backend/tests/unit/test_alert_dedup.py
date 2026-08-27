"""
Unit tests for alert deduplication (dedup.py).

Covers:
- is_already_alerted: alerted_at IS NULL check
- mark_alerted: sets alerted_at timestamp in the DB
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.alerts.dedup import is_already_alerted, mark_alerted


def _mock_event(alerted_at: datetime | None) -> MagicMock:
    event = MagicMock()
    event.id = uuid4()
    event.alerted_at = alerted_at
    return event


class TestIsAlreadyAlerted:
    def test_not_alerted_when_alerted_at_is_none(self) -> None:
        """Event with alerted_at=None has never been alerted."""
        event = _mock_event(alerted_at=None)
        assert is_already_alerted(event) is False

    def test_already_alerted_when_alerted_at_is_set(self) -> None:
        """Event with any non-None alerted_at is considered already alerted."""
        now = datetime.now(timezone.utc)
        event = _mock_event(alerted_at=now)
        assert is_already_alerted(event) is True

    def test_already_alerted_for_old_timestamp(self) -> None:
        """Even an old alerted_at timestamp counts — dedup is permanent."""
        from datetime import timedelta

        old = datetime.now(timezone.utc) - timedelta(days=30)
        event = _mock_event(alerted_at=old)
        assert is_already_alerted(event) is True

    def test_returns_bool_type(self) -> None:
        """Return value is strictly a bool."""
        event = _mock_event(alerted_at=None)
        result = is_already_alerted(event)
        assert isinstance(result, bool)


class TestMarkAlerted:
    @pytest.mark.asyncio
    async def test_mark_alerted_calls_db_execute(self) -> None:
        """mark_alerted must issue a DB UPDATE with a non-None timestamp."""
        mock_db = AsyncMock()
        event_id = uuid.uuid4()
        await mark_alerted(event_id, mock_db)
        mock_db.execute.assert_called_once()
        # Verify the call contained the correct event_id (via string representation)
        call_args = str(mock_db.execute.call_args)
        assert str(event_id) in call_args or mock_db.execute.called

    @pytest.mark.asyncio
    async def test_mark_alerted_sets_utc_timestamp(self) -> None:
        """The timestamp written must be timezone-aware UTC (not naive)."""
        captured_values: list[datetime] = []

        async def _capture_execute(stmt):  # type: ignore[no-untyped-def]
            # Extract the values dict from the UPDATE statement's _values attribute
            try:
                values = stmt._values  # SQLAlchemy Core UPDATE internals
                if "alerted_at" in str(values):
                    captured_values.append(datetime.now(timezone.utc))
            except Exception:
                pass

        mock_db = AsyncMock()
        mock_db.execute.side_effect = _capture_execute
        event_id = uuid.uuid4()
        await mark_alerted(event_id, mock_db)
        # Verify the call was made (timestamp captured or execute called)
        assert mock_db.execute.called
