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
    op.execute(
        "ALTER TABLE key_borrow_records "
        "ADD COLUMN IF NOT EXISTS borrowed_key_name VARCHAR(255)"
    )
    op.alter_column("key_borrow_records", "key_id", existing_type=sa.Integer(), nullable=True)
    op.execute("ALTER TABLE key_borrow_records DROP COLUMN IF EXISTS returned_at")


def downgrade() -> None:
    op.execute(
        "ALTER TABLE key_borrow_records "
        "ADD COLUMN IF NOT EXISTS returned_at TIMESTAMP WITH TIME ZONE"
    )
    op.alter_column("key_borrow_records", "key_id", existing_type=sa.Integer(), nullable=False)
    op.execute("ALTER TABLE key_borrow_records DROP COLUMN IF EXISTS borrowed_key_name")
