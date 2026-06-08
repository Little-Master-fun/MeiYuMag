"""add borrow organization fields

Revision ID: 5c2d9dd829e9
Revises: 5a554f707a15
Create Date: 2026-06-08 11:16:23.840836
"""
from typing import Sequence, Union

from alembic import op



revision: str = '5c2d9dd829e9'
down_revision: Union[str, Sequence[str], None] = '5a554f707a15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE applications "
        "ADD COLUMN IF NOT EXISTS borrow_organization VARCHAR(255)"
    )
    op.execute(
        "ALTER TABLE key_borrow_records "
        "ADD COLUMN IF NOT EXISTS borrow_organization VARCHAR(255)"
    )
    op.execute("UPDATE applications SET borrow_organization = organization")


def downgrade() -> None:
    op.execute("ALTER TABLE key_borrow_records DROP COLUMN IF EXISTS borrow_organization")
    op.execute("ALTER TABLE applications DROP COLUMN IF EXISTS borrow_organization")
