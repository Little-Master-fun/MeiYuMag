from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.notification import NotificationLog
from app.models.user import User
from app.models.venue import ReservationCalendar
from app.services.notification import notification_service


class ExpirationService:
    async def process_yueyuan_pending_signed_files(
        self,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> dict[str, int]:
        current_time = now or datetime.now()
        reminder_count = 0
        cancelled_count = 0

        result = await db.execute(
            select(Application)
            .where(
                and_(
                    Application.application_type == "yueyuan_third_floor",
                    Application.status == "pending_signed_files",
                    Application.start_at.is_not(None),
                )
            )
            .order_by(Application.start_at)
        )
        applications = result.scalars().all()

        for application in applications:
            if application.start_at is None:
                continue
            cancel_threshold = application.start_at - timedelta(days=2)
            reminder_threshold = application.start_at - timedelta(days=3)

            if current_time >= cancel_threshold:
                application.status = "cancelled"
                await self.cancel_reservations(db, application.id)
                user = await db.get(User, application.user_id)
                if user is not None:
                    await notification_service.send_and_log(
                        db=db,
                        application_id=application.id,
                        recipients=[user.email],
                        notification_type="pre_reservation_cancelled",
                        subject="悦园三楼申请预占用已取消",
                        body=(
                            "您的悦园三楼申请在最早使用时间前两天仍未提交正式材料，"
                            "系统已取消预占用。\n\n"
                            f"申请编号：{application.id}\n"
                            f"最早使用时间：{application.start_at}"
                        ),
                    )
                cancelled_count += 1
                continue

            if current_time >= reminder_threshold:
                already_reminded = await self.has_notification(
                    db,
                    application.id,
                    "signed_files_deadline_reminder",
                )
                if already_reminded:
                    continue
                user = await db.get(User, application.user_id)
                if user is not None:
                    await notification_service.send_and_log(
                        db=db,
                        application_id=application.id,
                        recipients=[user.email],
                        notification_type="signed_files_deadline_reminder",
                        subject="悦园三楼申请即将到期，请提交正式材料",
                        body=(
                            "您的悦园三楼申请距离最早使用时间不足三天，请尽快上传签字盖章材料。"
                            "若最早使用时间前两天仍未提交，系统将取消预占用。\n\n"
                            f"申请编号：{application.id}\n"
                            f"最早使用时间：{application.start_at}"
                        ),
                    )
                    reminder_count += 1

        await db.commit()
        return {"reminded": reminder_count, "cancelled": cancelled_count}

    async def has_notification(
        self,
        db: AsyncSession,
        application_id: int,
        notification_type: str,
    ) -> bool:
        result = await db.execute(
            select(NotificationLog).where(
                and_(
                    NotificationLog.application_id == application_id,
                    NotificationLog.notification_type == notification_type,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def cancel_reservations(self, db: AsyncSession, application_id: int) -> None:
        result = await db.execute(
            select(ReservationCalendar).where(ReservationCalendar.application_id == application_id)
        )
        for reservation in result.scalars():
            reservation.status = "cancelled"


expiration_service = ExpirationService()
