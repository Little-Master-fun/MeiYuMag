"""add application purpose summary

Revision ID: 41a897fdc171
Revises: 11e30151d404
Create Date: 2026-06-07 15:38:40.611083
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = '41a897fdc171'
down_revision: Union[str, Sequence[str], None] = '11e30151d404'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("purpose_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "purpose_summary")
