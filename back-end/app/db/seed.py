import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.venue import Venue


VENUE_SEEDS = [
    {
        "name": "大学生研讨室1",
        "venue_type": "meiyu_venue",
        "description": "美育场地申请使用",
    },
    {
        "name": "大学生研讨室2",
        "venue_type": "meiyu_venue",
        "description": "美育场地申请使用",
    },
    {
        "name": "兴隆山艺术走廊",
        "venue_type": "meiyu_venue",
        "description": "美育场地申请使用",
    },
    {
        "name": "会议室",
        "venue_type": "meiyu_venue",
        "description": "美育场地申请使用",
    },
    {
        "name": "美育小舞台",
        "venue_type": "meiyu_venue",
        "description": "美育场地申请使用",
    },
    {
        "name": "多功能厅（大）",
        "venue_type": "meiyu_venue",
        "description": "美育场地申请使用",
    },
    {
        "name": "多功能厅（中）",
        "venue_type": "meiyu_venue",
        "description": "美育场地申请使用",
    },
    {
        "name": "多功能厅（小）",
        "venue_type": "meiyu_venue",
        "description": "美育场地申请使用",
    },
    {
        "name": "悦园三楼",
        "venue_type": "yueyuan_third_floor",
        "description": "悦园三楼活动申请使用",
    },
]

DEFAULT_INITIAL_ADMIN_ACCOUNT = "202300450146"
DEFAULT_INITIAL_ADMIN_PASSWORD = "genius"


async def upsert_venues() -> None:
    async with AsyncSessionLocal() as db:
        for item in VENUE_SEEDS:
            result = await db.execute(select(Venue).where(Venue.name == item["name"]))
            venue = result.scalar_one_or_none()
            if venue is None:
                db.add(Venue(**item))
            else:
                venue.venue_type = item["venue_type"]
                venue.description = item["description"]

        initial_admin_account = settings.initial_admin_account or DEFAULT_INITIAL_ADMIN_ACCOUNT
        initial_admin_password = settings.initial_admin_password or DEFAULT_INITIAL_ADMIN_PASSWORD
        if initial_admin_account and initial_admin_password:
            email = initial_admin_account.lower()
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user is None:
                db.add(
                    User(
                        email=email,
                        password_hash=hash_password(settings.initial_admin_password),
                        role="admin",
                        is_application_allowed=True,
                    )
                )
            else:
                user.role = "admin"
                user.is_application_allowed = True

        await db.commit()


if __name__ == "__main__":
    asyncio.run(upsert_venues())
