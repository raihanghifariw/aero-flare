"""create initial tables

Revision ID: 0001
Revises:
Create Date: 2025-07-23 00:00:00.000000 UTC

Tables created:
  - fire_events
  - triage_reports
  - predictions
  - webhook_registrations
  - event_audit_log

After running 'alembic upgrade head', apply the audit trigger SQL
from plan/system_design.md Section 3 in Supabase SQL Editor.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- fire_events ---
    op.create_table(
        "fire_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("firms_id", sa.Text(), nullable=True, unique=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lat", sa.Double(), nullable=False),
        sa.Column("lon", sa.Double(), nullable=False),
        sa.Column("frp", sa.Double(), nullable=True),
        sa.Column("brightness", sa.Double(), nullable=True),
        sa.Column("satellite", sa.String(50), nullable=True),
        sa.Column("tile_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fire_events_detected_at", "fire_events", ["detected_at"])
    op.create_index("ix_fire_events_status", "fire_events", ["status"])

    # --- triage_reports ---
    op.create_table(
        "triage_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fire_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("classification", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Double(), nullable=True),
        sa.Column("fire_area_ha", sa.Double(), nullable=True),
        sa.Column("smoke_direction", sa.String(10), nullable=True),
        sa.Column("danger_level", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.String(50), nullable=True),
        sa.Column("triage_source", sa.String(30), nullable=False, server_default="VLM"),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_triage_reports_event_id", "triage_reports", ["event_id"])

    # --- predictions ---
    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fire_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("spread_direction_deg", sa.Double(), nullable=True),
        sa.Column("radius_6h_km", sa.Double(), nullable=True),
        sa.Column("radius_12h_km", sa.Double(), nullable=True),
        sa.Column("radius_24h_km", sa.Double(), nullable=True),
        sa.Column("wind_speed", sa.Double(), nullable=True),
        sa.Column("wind_direction", sa.Double(), nullable=True),
        sa.Column("humidity", sa.Double(), nullable=True),
        sa.Column("model_version", sa.String(20), nullable=True),
        sa.Column("predicted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_predictions_event_id", "predictions", ["event_id"])

    # --- webhook_registrations ---
    op.create_table(
        "webhook_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- event_audit_log ---
    op.create_table(
        "event_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("table_name", sa.String(50), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column("changed_by", sa.String(50), nullable=False, server_default="system"),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_event_audit_log_row_id", "event_audit_log", ["row_id"])
    op.create_index("ix_event_audit_log_changed_at", "event_audit_log", ["changed_at"])


def downgrade() -> None:
    op.drop_table("event_audit_log")
    op.drop_table("webhook_registrations")
    op.drop_table("predictions")
    op.drop_table("triage_reports")
    op.drop_table("fire_events")
