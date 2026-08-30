import asyncio
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.application import Application
from app.models.user import User
from app.models.venue import ReservationCalendar, Venue


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

DEMO_USAGE_SEEDS = [
    {
        "key": "seminar-ink-painting",
        "venue": "大学生研讨室1",
        "start": (9, 0),
        "end": (11, 0),
        "status": "confirmed",
        "organization": "山大书画社",
        "purpose": "水墨体验工作坊",
    },
    {
        "key": "seminar-film-reading",
        "venue": "大学生研讨室2",
        "start": (14, 0),
        "end": (16, 30),
        "status": "pre_reserved",
        "organization": "学生电影协会",
        "purpose": "经典影片读解会",
    },
    {
        "key": "corridor-exhibition",
        "venue": "兴隆山艺术走廊",
        "start": (10, 0),
        "end": (17, 30),
        "status": "confirmed",
        "organization": "美术学院学生会",
        "purpose": "校园摄影作品展",
    },
    {
        "key": "meeting-volunteer",
        "venue": "会议室",
        "start": (15, 0),
        "end": (16, 0),
        "status": "pending_admin_pre_review",
        "organization": "美育志愿服务队",
        "purpose": "秋季活动筹备会",
    },
    {
        "key": "stage-acoustic",
        "venue": "美育小舞台",
        "start": (18, 30),
        "end": (21, 0),
        "status": "confirmed",
        "organization": "吉他协会",
        "purpose": "草地音乐会彩排",
    },
    {
        "key": "hall-large-dance",
        "venue": "多功能厅（大）",
        "start": (13, 30),
        "end": (16, 30),
        "status": "supplement_required",
        "organization": "舞蹈团",
        "purpose": "毕业专场联排",
    },
    {
        "key": "hall-medium-chorus",
        "venue": "多功能厅（中）",
        "start": (9, 30),
        "end": (11, 30),
        "status": "confirmed",
        "organization": "大学生合唱团",
        "purpose": "声部训练",
    },
    {
        "key": "yueyuan-poetry",
        "venue": "悦园三楼",
        "start": (19, 0),
        "end": (21, 30),
        "status": "pre_reserved",
        "organization": "文学社",
        "purpose": "秋夜诗歌分享会",
    },
    {
        "key": "past-watercolor",
        "venue": "大学生研讨室1",
        "day_offset": -14,
        "start": (14, 0),
        "end": (17, 0),
        "status": "confirmed",
        "organization": "绘画社",
        "purpose": "水彩基础课程",
    },
    {
        "key": "past-drama",
        "venue": "多功能厅（大）",
        "day_offset": -11,
        "start": (18, 0),
        "end": (21, 30),
        "status": "confirmed",
        "organization": "话剧社",
        "purpose": "校园戏剧展演",
    },
    {
        "key": "past-calligraphy",
        "venue": "悦园三楼",
        "day_offset": -8,
        "start": (9, 0),
        "end": (11, 30),
        "status": "confirmed",
        "organization": "书法协会",
        "purpose": "篆隶临摹交流",
    },
    {
        "key": "past-photography",
        "venue": "兴隆山艺术走廊",
        "day_offset": -5,
        "start": (10, 0),
        "end": (18, 0),
        "status": "confirmed",
        "organization": "摄影协会",
        "purpose": "光影校园主题展",
    },
    {
        "key": "past-choir",
        "venue": "多功能厅（中）",
        "day_offset": -2,
        "start": (15, 0),
        "end": (17, 30),
        "status": "confirmed",
        "organization": "大学生合唱团",
        "purpose": "合唱公开排练",
    },
    {
        "key": "future-reading",
        "venue": "大学生研讨室2",
        "day_offset": 2,
        "start": (19, 0),
        "end": (21, 0),
        "status": "pre_reserved",
        "organization": "读书会",
        "purpose": "艺术史共读",
    },
    {
        "key": "future-folk-music",
        "venue": "美育小舞台",
        "day_offset": 4,
        "start": (18, 30),
        "end": (21, 30),
        "status": "confirmed",
        "organization": "民乐团",
        "purpose": "传统器乐专场",
    },
    {
        "key": "future-ceramics",
        "venue": "多功能厅（小）",
        "day_offset": 6,
        "start": (9, 0),
        "end": (12, 0),
        "status": "pending_admin_pre_review",
        "organization": "手工艺协会",
        "purpose": "陶艺体验活动",
    },
    {
        "key": "future-dance",
        "venue": "多功能厅（大）",
        "day_offset": 8,
        "start": (13, 0),
        "end": (17, 30),
        "status": "pre_reserved",
        "organization": "舞蹈团",
        "purpose": "民族舞专场彩排",
    },
    {
        "key": "future-lecture",
        "venue": "会议室",
        "day_offset": 10,
        "start": (14, 30),
        "end": (16, 30),
        "status": "confirmed",
        "organization": "美育研究会",
        "purpose": "公共艺术专题讲座",
    },
    {
        "key": "future-film",
        "venue": "悦园三楼",
        "day_offset": 12,
        "start": (18, 30),
        "end": (21, 30),
        "status": "supplement_required",
        "organization": "学生电影协会",
        "purpose": "青年导演作品放映",
    },
    {
        "key": "future-exhibition",
        "venue": "兴隆山艺术走廊",
        "day_offset": 14,
        "start": (9, 0),
        "end": (18, 0),
        "status": "confirmed",
        "organization": "艺术设计协会",
        "purpose": "视觉设计课程展",
    },
]


async def upsert_demo_usage(
    db,
    user: User,
    venues_by_name: dict[str, Venue],
) -> None:
    today = date.today()
    timezone = ZoneInfo("Asia/Shanghai")

    for item in DEMO_USAGE_SEEDS:
        venue = venues_by_name.get(item["venue"])
        if venue is None:
            continue

        marker = f"[DEMO_USAGE:{item['key']}]"
        application_result = await db.execute(
            select(Application).where(Application.purpose_summary.like(f"{marker}%"))
        )
        application = application_result.scalar_one_or_none()
        scheduled_date = today + timedelta(days=int(item.get("day_offset", 0)))
        start_at = datetime.combine(scheduled_date, time(*item["start"]), tzinfo=timezone)
        end_at = datetime.combine(scheduled_date, time(*item["end"]), tzinfo=timezone)
        purpose_summary = f"{marker} {item['purpose']}"

        if application is None:
            application = Application(
                user_id=user.id,
                application_type="venue",
                organization=item["organization"],
                borrow_organization=item["organization"],
                purpose_summary=purpose_summary,
                applicant_name="示例用户",
                applicant_department="美育中心",
                venue_id=venue.id,
                status=item["status"],
                start_at=start_at,
                end_at=end_at,
            )
            db.add(application)
            await db.flush()
        else:
            application.user_id = user.id
            application.organization = item["organization"]
            application.borrow_organization = item["organization"]
            application.purpose_summary = purpose_summary
            application.venue_id = venue.id
            application.status = item["status"]
            application.start_at = start_at
            application.end_at = end_at

        reservation_result = await db.execute(
            select(ReservationCalendar).where(
                ReservationCalendar.application_id == application.id
            )
        )
        reservation = reservation_result.scalar_one_or_none()
        if reservation is None:
            db.add(
                ReservationCalendar(
                    venue_id=venue.id,
                    application_id=application.id,
                    start_at=start_at,
                    end_at=end_at,
                    status=item["status"],
                )
            )
        else:
            reservation.venue_id = venue.id
            reservation.start_at = start_at
            reservation.end_at = end_at
            reservation.status = item["status"]


async def upsert_venues() -> None:
    async with AsyncSessionLocal() as db:
        venues_by_name: dict[str, Venue] = {}
        for item in VENUE_SEEDS:
            result = await db.execute(select(Venue).where(Venue.name == item["name"]))
            venue = result.scalar_one_or_none()
            if venue is None:
                venue = Venue(**item)
                db.add(venue)
            else:
                venue.venue_type = item["venue_type"]
                venue.description = item["description"]
            venues_by_name[item["name"]] = venue

        initial_admin_account = settings.initial_admin_account or DEFAULT_INITIAL_ADMIN_ACCOUNT
        initial_admin_password = settings.initial_admin_password or DEFAULT_INITIAL_ADMIN_PASSWORD
        if initial_admin_account and initial_admin_password:
            email = initial_admin_account.lower()
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    email=email,
                    password_hash=hash_password(initial_admin_password),
                    role="admin",
                    department="美育中心",
                    is_application_allowed=True,
                )
                db.add(user)
            else:
                user.role = "admin"
                user.is_application_allowed = True

            await db.flush()
            await upsert_demo_usage(db, user, venues_by_name)

        await db.commit()


if __name__ == "__main__":
    asyncio.run(upsert_venues())
