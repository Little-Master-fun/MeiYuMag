"""Persist submission checklists and normalize legacy statuses."""
from alembic import op
import sqlalchemy as sa

revision = "72c6cdea9012"
down_revision = "5c2d9dd829e9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("applications", sa.Column("requested_file_types", sa.JSON(), nullable=True))
    op.add_column("applications", sa.Column("decision_reason", sa.Text(), nullable=True))
    op.execute("UPDATE applications SET status='submitted' WHERE status='admin_submitted'")
    op.execute("""UPDATE applications SET status='ai_rejected'
        WHERE status='pending_admin_pre_review' AND EXISTS (
          SELECT 1 FROM application_files f WHERE f.application_id=applications.id
          AND f.file_type='pre_review_word' AND (f.review_status IN ('failed', 'rejected') OR f.reject_reason IS NOT NULL)
          AND f.version=(SELECT MAX(g.version) FROM application_files g
                         WHERE g.application_id=f.application_id AND g.file_type=f.file_type))""")


def downgrade():
    op.drop_column("applications", "decision_reason")
    op.drop_column("applications", "requested_file_types")
