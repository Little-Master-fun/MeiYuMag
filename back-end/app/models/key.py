from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KeyResource(Base):
    __tablename__ = "key_resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    room_name: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="available")


class KeyBorrowRecord(Base):
    __tablename__ = "key_borrow_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_id: Mapped[int | None] = mapped_column(ForeignKey("key_resources.id"), index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    borrowed_key_name: Mapped[str | None] = mapped_column(String(255))
    borrowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_return_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
