"""init schema

Revision ID: 11e30151d404
Revises: 
Create Date: 2026-06-07 14:22:57.189270
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = '11e30151d404'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("is_sdu_verified", sa.Boolean(), nullable=False),
        sa.Column("is_application_allowed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "venues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("venue_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "key_resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("room_name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("application_type", sa.String(length=64), nullable=False),
        sa.Column("organization", sa.String(length=255), nullable=True),
        sa.Column("borrow_organization", sa.String(length=255), nullable=True),
        sa.Column("applicant_name", sa.String(length=128), nullable=True),
        sa.Column("applicant_sduid", sa.String(length=64), nullable=True),
        sa.Column("applicant_department", sa.String(length=255), nullable=True),
        sa.Column("venue_id", sa.Integer(), sa.ForeignKey("venues.id"), nullable=True),
        sa.Column("key_id", sa.Integer(), sa.ForeignKey("key_resources.id"), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_application_type", "applications", ["application_type"])
    op.create_index("ix_applications_venue_id", "applications", ["venue_id"])
    op.create_index("ix_applications_key_id", "applications", ["key_id"])
    op.create_index("ix_applications_status", "applications", ["status"])
    op.create_index("ix_applications_start_at", "applications", ["start_at"])
    op.create_index("ix_applications_end_at", "applications", ["end_at"])

    op.create_table(
        "auth_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sduid", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("sex", sa.String(length=32), nullable=True),
        sa.Column("person_type", sa.String(length=64), nullable=True),
        sa.Column("school", sa.String(length=255), nullable=True),
        sa.Column("sdu_email", sa.String(length=255), nullable=True),
        sa.Column("mobile", sa.String(length=32), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("sduid"),
    )
    op.create_index("ix_auth_profiles_user_id", "auth_profiles", ["user_id"])
    op.create_index("ix_auth_profiles_sduid", "auth_profiles", ["sduid"])

    op.create_table(
        "application_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("file_type", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("review_status", sa.String(length=64), nullable=False),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_application_files_application_id", "application_files", ["application_id"])
    op.create_index("ix_application_files_file_type", "application_files", ["file_type"])

    op.create_table(
        "reservation_calendar",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("venue_id", sa.Integer(), sa.ForeignKey("venues.id"), nullable=False),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_reservation_calendar_venue_id", "reservation_calendar", ["venue_id"])
    op.create_index("ix_reservation_calendar_application_id", "reservation_calendar", ["application_id"])
    op.create_index("ix_reservation_calendar_start_at", "reservation_calendar", ["start_at"])
    op.create_index("ix_reservation_calendar_end_at", "reservation_calendar", ["end_at"])

    op.create_table(
        "key_borrow_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_id", sa.Integer(), sa.ForeignKey("key_resources.id"), nullable=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("borrowed_key_name", sa.String(length=255), nullable=True),
        sa.Column("borrow_organization", sa.String(length=255), nullable=True),
        sa.Column("borrowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_return_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_key_borrow_records_key_id", "key_borrow_records", ["key_id"])
    op.create_index("ix_key_borrow_records_application_id", "key_borrow_records", ["application_id"])

    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notification_logs_application_id", "notification_logs", ["application_id"])
    op.create_index("ix_notification_logs_recipient", "notification_logs", ["recipient"])
    op.create_index("ix_notification_logs_notification_type", "notification_logs", ["notification_type"])


def downgrade() -> None:
    op.drop_index("ix_notification_logs_notification_type", table_name="notification_logs")
    op.drop_index("ix_notification_logs_recipient", table_name="notification_logs")
    op.drop_index("ix_notification_logs_application_id", table_name="notification_logs")
    op.drop_table("notification_logs")

    op.drop_index("ix_key_borrow_records_application_id", table_name="key_borrow_records")
    op.drop_index("ix_key_borrow_records_key_id", table_name="key_borrow_records")
    op.drop_table("key_borrow_records")

    op.drop_index("ix_reservation_calendar_end_at", table_name="reservation_calendar")
    op.drop_index("ix_reservation_calendar_start_at", table_name="reservation_calendar")
    op.drop_index("ix_reservation_calendar_application_id", table_name="reservation_calendar")
    op.drop_index("ix_reservation_calendar_venue_id", table_name="reservation_calendar")
    op.drop_table("reservation_calendar")

    op.drop_index("ix_application_files_file_type", table_name="application_files")
    op.drop_index("ix_application_files_application_id", table_name="application_files")
    op.drop_table("application_files")

    op.drop_index("ix_auth_profiles_sduid", table_name="auth_profiles")
    op.drop_index("ix_auth_profiles_user_id", table_name="auth_profiles")
    op.drop_table("auth_profiles")

    op.drop_index("ix_applications_end_at", table_name="applications")
    op.drop_index("ix_applications_start_at", table_name="applications")
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_key_id", table_name="applications")
    op.drop_index("ix_applications_venue_id", table_name="applications")
    op.drop_index("ix_applications_application_type", table_name="applications")
    op.drop_index("ix_applications_user_id", table_name="applications")
    op.drop_table("applications")

    op.drop_table("key_resources")
    op.drop_table("venues")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
