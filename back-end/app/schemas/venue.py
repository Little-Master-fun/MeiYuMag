from datetime import date, datetime

from pydantic import BaseModel, Field


class VenueRead(BaseModel):
    id: int
    name: str
    venue_type: str
    description: str | None = None

    model_config = {"from_attributes": True}


class CalendarEvent(BaseModel):
    id: str = Field(description="Frontend-stable event id")
    application_id: int
    venue_id: int
    venue_name: str
    application_type: str
    title: str
    organization: str | None = None
    applicant_name: str | None = None
    start_at: datetime
    end_at: datetime
    status: str
    occupancy_type: str = Field(description="pre_reserved or confirmed")
    is_mine: bool = False
    color: str


class CalendarDaySegment(BaseModel):
    event_id: str
    start_time: str
    end_time: str
    status: str
    occupancy_type: str
    title: str


class CalendarDay(BaseModel):
    date: date
    is_today: bool = False
    event_count: int = 0
    has_available_slots: bool = True
    segments: list[CalendarDaySegment] = Field(default_factory=list)


class CalendarStatusLegendItem(BaseModel):
    status: str
    label: str
    color: str


class VenueMonthCalendarResponse(BaseModel):
    year: int
    month: int
    timezone: str = "Asia/Shanghai"
    month_start: date
    month_end: date
    venue: VenueRead
    events: list[CalendarEvent]
    days: dict[str, CalendarDay]
    legend: list[CalendarStatusLegendItem]
