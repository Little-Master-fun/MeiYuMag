from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.key import KeyBorrowRecord
from app.models.venue import ReservationCalendar, Venue
from app.schemas.application import AdminPreReviewDecision, ManualKeyDetails
from app.services.business_time import BUSINESS_TZ, local_time


async def approve_manual_venue(db: AsyncSession, application: Application, payload: AdminPreReviewDecision) -> None:
    venue_id = payload.venue_id or application.venue_id
    venue = (await db.execute(select(Venue).where(Venue.id == venue_id).with_for_update())).scalar_one_or_none()
    organization = (payload.borrow_organization or "").strip()
    if venue is None or not organization or not payload.time_slots:
        raise HTTPException(400, "请根据原件填写场地、借用组织和完整借用时段后通过初审")
    slots = sorted([(local_time(s.start_at), local_time(s.end_at)) for s in payload.time_slots])
    now = datetime.now(BUSINESS_TZ)
    for index, (start, end) in enumerate(slots):
        if start <= now or end <= start:
            raise HTTPException(400, "借用时间必须在未来，结束时间须晚于开始时间")
        if index and start < slots[index-1][1]:
            raise HTTPException(400, "本次申请的时段不能相互重叠")
    kind = "yueyuan_third_floor" if "悦园三楼" in venue.name else "meiyu_venue"
    if kind == "yueyuan_third_floor":
        days = sorted({start.date() for start, _ in slots})
        if len(days) > 3 or any(b-a == timedelta(days=1) for a,b in zip(days,days[1:])) or any(start.date() != end.date() for start,end in slots):
            raise HTTPException(400, "悦园一次最多申请三天，不得连续自然日，每个时段须在同一天内")
    for start, end in slots:
        conflict = (await db.execute(select(ReservationCalendar.id).where(
            ReservationCalendar.venue_id == venue.id,
            ReservationCalendar.application_id != application.id,
            ReservationCalendar.status.in_(["pre_reserved", "confirmed", "reserved"]),
            ReservationCalendar.start_at < end, ReservationCalendar.end_at > start,
        ).limit(1))).scalar_one_or_none()
        if conflict is not None:
            raise HTTPException(409, "申请时段与已有预约冲突，请核对原件并退回修改，不能直接通过")
    old = (await db.execute(select(ReservationCalendar).where(ReservationCalendar.application_id == application.id))).scalars()
    for reservation in old:
        reservation.status = "cancelled"
    application.venue_id, application.application_type = venue.id, kind
    application.borrow_organization = application.organization = organization
    application.start_at, application.end_at = slots[0][0], slots[-1][1]
    for start, end in slots:
        db.add(ReservationCalendar(application_id=application.id, venue_id=venue.id, start_at=start, end_at=end, status="pre_reserved"))


async def confirm_key_details(db: AsyncSession, application: Application, details: ManualKeyDetails | None, *, completing: bool = False) -> None:
    record = (await db.execute(select(KeyBorrowRecord).where(KeyBorrowRecord.application_id == application.id).with_for_update())).scalars().first()
    if record is None:
        raise HTTPException(409, "钥匙借用记录缺失，请联系管理员核查")
    name = (details.borrowed_key_name if details else record.borrowed_key_name) or ""
    organization = (details.borrow_organization if details else record.borrow_organization) or ""
    start = details.start_at if details else record.borrowed_at
    end = details.end_at if details else record.expected_return_at
    if not name.strip() or not organization.strip() or start is None or end is None:
        raise HTTPException(400, "请人工核对并填写钥匙名称、借用组织、借用及归还时间")
    start, end = local_time(start), local_time(end)
    if end <= start or (not completing and start <= datetime.now(BUSINESS_TZ)):
        raise HTTPException(400, "借用时间须在未来，归还时间须晚于借用时间")
    record.borrowed_key_name, record.borrow_organization = name.strip(), organization.strip()
    record.borrowed_at, record.expected_return_at = start, end
    application.borrow_organization = application.organization = organization.strip()
    application.start_at, application.end_at = start, end
