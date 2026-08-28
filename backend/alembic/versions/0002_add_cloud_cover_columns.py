"""add cloud cover columns to triage_reports

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-27
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("triage_reports", sa.Column("cloud_cover_percent", sa.Float(), nullable=True))
    op.add_column("triage_reports", sa.Column("visually_obscured", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("triage_reports", "visually_obscured")
    op.drop_column("triage_reports", "cloud_cover_percent")
