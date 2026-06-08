"""add borrow organization fields

Revision ID: 5c2d9dd829e9
Revises: 5a554f707a15
Create Date: 2026-06-08 11:16:23.840836
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = '5c2d9dd829e9'
down_revision: Union[str, Sequence[str], None] = '5a554f707a15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("borrow_organization", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "key_borrow_records",
        sa.Column("borrow_organization", sa.String(length=255), nullable=True),
    )
    op.execute("UPDATE applications SET borrow_organization = organization")


def downgrade() -> None:
    op.drop_column("key_borrow_records", "borrow_organization")
    op.drop_column("applications", "borrow_organization")
