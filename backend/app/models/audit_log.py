"""
EventAuditLog ORM model — maps to `event_audit_log` table.
Append-only. Written by PostgreSQL triggers — application code never inserts here directly.
ADR-015: Immutable audit trail for disaster response traceability.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# PostgreSQL uses JSONB; SQLite (used in tests) has no JSONB type and would raise
# 'SQLiteTypeCompiler has no attribute visit_JSONB' during create_all().
# with_variant keeps JSONB in production and falls back to generic JSON on SQLite.
_JSONType = JSONB().with_variant(JSON(), "sqlite")


class EventAuditLog(Base):
    __tablename__ = "event_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    table_name: Mapped[str] = mapped_column(String(50), nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    row_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    old_values: Mapped[dict | None] = mapped_column(_JSONType, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(_JSONType, nullable=True)
    changed_by: Mapped[str] = mapped_column(
        String(50), nullable=False, default="system"
    )
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
