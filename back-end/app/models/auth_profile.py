from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthProfile(Base):
    __tablename__ = "auth_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    sduid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    sex: Mapped[str | None] = mapped_column(String(32))
    person_type: Mapped[str | None] = mapped_column(String(64))
    school: Mapped[str | None] = mapped_column(String(255))
    sdu_email: Mapped[str | None] = mapped_column(String(255))
    mobile: Mapped[str | None] = mapped_column(String(32))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

