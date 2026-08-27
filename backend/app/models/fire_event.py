"""FireEvent ORM model — maps to `fire_events` table."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Double, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FireEvent(Base):
    __tablename__ = "fire_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    firms_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    lat: Mapped[float] = mapped_column(Double, nullable=False)
    lon: Mapped[float] = mapped_column(Double, nullable=False)
    frp: Mapped[float | None] = mapped_column(Double, nullable=True)
    brightness: Mapped[float | None] = mapped_column(Double, nullable=True)
    satellite: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Status lifecycle: PENDING → TRIAGED → PREDICTED → ALERTED | ALERTED_FAILED
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    # alerted_at replaces Redis-based dedup (ADR-014). NULL = not yet alerted.
    alerted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
