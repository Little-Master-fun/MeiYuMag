from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_type: Mapped[str] = mapped_column(String(64), index=True)
    organization: Mapped[str | None] = mapped_column(String(255))
    borrow_organization: Mapped[str | None] = mapped_column(String(255))
    purpose_summary: Mapped[str | None] = mapped_column(Text)
    applicant_name: Mapped[str | None] = mapped_column(String(128))
    applicant_sduid: Mapped[str | None] = mapped_column(String(64))
    applicant_department: Mapped[str | None] = mapped_column(String(255))
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venues.id"), index=True)
    key_id: Mapped[int | None] = mapped_column(ForeignKey("key_resources.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), index=True, default="draft")
    requested_file_types: Mapped[list | None] = mapped_column(JSON)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ApplicationFile(Base):
    __tablename__ = "application_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    file_type: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(default=1)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    review_status: Mapped[str] = mapped_column(String(64), default="pending")
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
