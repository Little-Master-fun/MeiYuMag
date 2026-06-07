import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.key import KeyResource
from app.models.user import User
from app.models.venue import Venue


VENUE_SEEDS = [
    {
        "name": "山东大学美育文化馆",
        "venue_type": "meiyu_venue",
        "description": "美育场地申请使用",
    },
    {
        "name": "悦园三楼",
        "venue_type": "yueyuan_third_floor",
        "description": "悦园三楼活动申请使用",
    },
]

KEY_SEEDS = [
    {"name": "美育文化馆钥匙", "room_name": "山东大学美育文化馆", "status": "available"},
    {"name": "悦园三楼钥匙", "room_name": "悦园三楼", "status": "available"},
]


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

        for item in KEY_SEEDS:
            result = await db.execute(select(KeyResource).where(KeyResource.name == item["name"]))
            key = result.scalar_one_or_none()
            if key is None:
                db.add(KeyResource(**item))
            else:
                key.room_name = item["room_name"]
                key.status = item["status"]

        if settings.initial_admin_email and settings.initial_admin_password:
            email = settings.initial_admin_email.lower()
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
