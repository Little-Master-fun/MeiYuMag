"""adjust key borrow records

Revision ID: 5a554f707a15
Revises: 41a897fdc171
Create Date: 2026-06-08 11:12:20.165910
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = '5a554f707a15'
down_revision: Union[str, Sequence[str], None] = '41a897fdc171'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "key_borrow_records",
        sa.Column("borrowed_key_name", sa.String(length=255), nullable=True),
    )
    op.alter_column("key_borrow_records", "key_id", existing_type=sa.Integer(), nullable=True)
    op.drop_column("key_borrow_records", "returned_at")


def downgrade() -> None:
    op.add_column(
        "key_borrow_records",
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("key_borrow_records", "key_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("key_borrow_records", "borrowed_key_name")
