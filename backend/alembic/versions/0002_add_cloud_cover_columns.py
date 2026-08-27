"""add cloud cover columns to triage_reports

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('triage_reports', sa.Column('cloud_cover_percent', sa.Float(), nullable=True))
    op.add_column('triage_reports', sa.Column('visually_obscured', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('triage_reports', 'visually_obscured')
    op.drop_column('triage_reports', 'cloud_cover_percent')
