from calendar import monthrange
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.application import Application
from app.models.venue import ReservationCalendar, Venue
from app.schemas.venue import (
    CalendarDaySegment,
    CalendarEvent,
    CalendarStatusLegendItem,
    VenueMonthCalendarResponse,
    VenueRead,
)

router = APIRouter(prefix="/venues", tags=["venues"])


def calendar_color(status: str) -> str:
    return {
        "pre_reserved": "#f59e0b",
        "confirmed": "#2563eb",
        "reserved": "#2563eb",
        "supplement_required": "#dc2626",
        "pending_admin_pre_review": "#9333ea",
    }.get(status, "#64748b")


def occupancy_type(status: str) -> str:
    return "pre_reserved" if status == "pre_reserved" else "confirmed"


@router.get("", response_model=list[VenueRead])
async def list_venues(db: AsyncSession = Depends(get_db)) -> list[VenueRead]:
    result = await db.execute(select(Venue).order_by(Venue.name))
    return [VenueRead.model_validate(venue) for venue in result.scalars()]


@router.get("/{venue_id}/calendar", response_model=VenueMonthCalendarResponse)
async def get_venue_calendar(
    venue_id: int,
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    db: AsyncSession = Depends(get_db),
) -> VenueMonthCalendarResponse:
    venue = await db.get(Venue, venue_id)
    if venue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")

    last_day = monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)
    days = {
        date(year, month, day).isoformat(): {
            "date": date(year, month, day),
            "event_count": 0,
            "segments": [],
        }
        for day in range(1, last_day + 1)
    }
    month_start_dt = datetime.combine(month_start, time.min)
    next_month = date(year + int(month == 12), 1 if month == 12 else month + 1, 1)
    next_month_dt = datetime.combine(next_month, time.min)

    result = await db.execute(
        select(ReservationCalendar, Application)
        .join(Application, Application.id == ReservationCalendar.application_id, isouter=True)
        .where(
            and_(
                ReservationCalendar.venue_id == venue_id,
                ReservationCalendar.start_at < next_month_dt,
                ReservationCalendar.end_at >= month_start_dt,
                ReservationCalendar.status != "cancelled",
            )
        )
        .order_by(ReservationCalendar.start_at)
    )

    events: list[CalendarEvent] = []
    for reservation, application in result.all():
        event_id = f"reservation-{reservation.id}"
        title = (
            application.borrow_organization
            if application and application.borrow_organization
            else application.organization
            if application and application.organization
            else "场地预约"
        )
        app_type = application.application_type if application else "unknown"
        event = CalendarEvent(
            id=event_id,
            application_id=reservation.application_id or 0,
            venue_id=venue_id,
            venue_name=venue.name,
            application_type=app_type,
            title=title,
            organization=application.organization if application else None,
            applicant_name=application.applicant_name if application else None,
            start_at=reservation.start_at,
            end_at=reservation.end_at,
            status=reservation.status,
            occupancy_type=occupancy_type(reservation.status),
            color=calendar_color(reservation.status),
            borrow_organization=application.borrow_organization if application else None,
        )
        events.append(event)

        day_key = reservation.start_at.date().isoformat()
        if day_key in days:
            days[day_key]["event_count"] += 1
            days[day_key]["segments"].append(
                CalendarDaySegment(
                    event_id=event_id,
                    start_time=reservation.start_at.strftime("%H:%M"),
                    end_time=reservation.end_at.strftime("%H:%M"),
                    status=reservation.status,
                    occupancy_type=occupancy_type(reservation.status),
                    title=title,
                )
            )

    return VenueMonthCalendarResponse(
        year=year,
        month=month,
        month_start=month_start,
        month_end=month_end,
        venue=VenueRead.model_validate(venue),
        events=events,
        days=days,
        legend=[
            CalendarStatusLegendItem(status="available", label="空闲", color="#16a34a"),
            CalendarStatusLegendItem(status="pre_reserved", label="预占用", color="#f59e0b"),
            CalendarStatusLegendItem(status="confirmed", label="已预约", color="#2563eb"),
            CalendarStatusLegendItem(status="supplement_required", label="待补交", color="#dc2626"),
            CalendarStatusLegendItem(status="pending_admin_pre_review", label="待管理员初审", color="#9333ea"),
        ],
    )
