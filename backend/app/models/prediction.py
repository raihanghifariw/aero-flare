"""Prediction ORM model — maps to `predictions` table."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fire_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    spread_direction_deg: Mapped[float | None] = mapped_column(Double, nullable=True)
    radius_6h_km: Mapped[float | None] = mapped_column(Double, nullable=True)
    radius_12h_km: Mapped[float | None] = mapped_column(Double, nullable=True)
    radius_24h_km: Mapped[float | None] = mapped_column(Double, nullable=True)
    wind_speed: Mapped[float | None] = mapped_column(Double, nullable=True)
    wind_direction: Mapped[float | None] = mapped_column(Double, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Double, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
