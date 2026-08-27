"""TriageReport ORM model — maps to `triage_reports` table."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TriageReport(Base):
    __tablename__ = "triage_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fire_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Double, nullable=True)
    fire_area_ha: Mapped[float | None] = mapped_column(Double, nullable=True)
    smoke_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    danger_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 'VLM' | 'RULE_BASED_FALLBACK' — tracks which path produced this report
    triage_source: Mapped[str] = mapped_column(
        String(30), nullable=False, default="VLM"
    )
    # NOTE: raw_vlm_output is intentionally NOT stored (ADR-014).
    # Raw responses are written to structlog only, to conserve DB quota.
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
