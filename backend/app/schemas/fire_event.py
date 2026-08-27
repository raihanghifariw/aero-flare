"""Pydantic schemas for FireEvent."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FireEventCreate(BaseModel):
    """Input schema for creating a fire event (internal use by ingestion service)."""
    firms_id: str | None = None
    detected_at: datetime
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    frp: float | None = Field(None, ge=0.0)
    brightness: float | None = None
    satellite: str | None = None
    tile_url: str | None = None


class FireEventSchema(BaseModel):
    """Output schema for a single fire event."""
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: uuid.UUID
    firms_id: str | None
    detected_at: datetime
    lat: float
    lon: float
    frp: float | None
    brightness: float | None
    satellite: str | None
    tile_url: str | None
    status: str
    alerted_at: datetime | None  # NULL = not yet alerted (replaces Redis dedup)
    created_at: datetime


# Valid status values
FireEventStatus = Literal[
    "PENDING", "TRIAGED", "PREDICTED", "ALERTED", "ALERTED_FAILED"
]


class FireEventsResponse(BaseModel):
    """Paginated response for event list."""
    model_config = ConfigDict(frozen=True)

    data: list[FireEventSchema]
    total: int
    page: int
    page_size: int
    has_next: bool
