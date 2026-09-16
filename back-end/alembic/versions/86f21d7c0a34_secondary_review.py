"""Assign scoped secondary signature reviewers to applications."""
from alembic import op
import sqlalchemy as sa

revision = "86f21d7c0a34"
down_revision = "72c6cdea9012"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("applications") as batch:
        batch.add_column(sa.Column("secondary_reviewer_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_application_secondary_reviewer", "users", ["secondary_reviewer_id"], ["id"])
        batch.create_index("ix_applications_secondary_reviewer_id", ["secondary_reviewer_id"])


def downgrade():
    # Preserve pending work when rolling back the role-aware application code.
    op.execute("UPDATE applications SET status='pending_admin_submit' WHERE status IN ('pending_secondary_review', 'pending_secondary_signature')")
    op.execute("UPDATE users SET role='user' WHERE role='secondary_admin'")
    with op.batch_alter_table("applications") as batch:
        batch.drop_index("ix_applications_secondary_reviewer_id")
        batch.drop_constraint("fk_application_secondary_reviewer", type_="foreignkey")
        batch.drop_column("secondary_reviewer_id")
