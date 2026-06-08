from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import NotificationLog
from app.models.user import User
from app.services.email import email_service


class NotificationService:
    async def get_admin_recipients(self, db: AsyncSession) -> list[str]:
        recipients = list(settings.admin_notification_emails)
        result = await db.execute(select(User.email).where(User.role == "admin"))
        recipients.extend(email for email in result.scalars().all() if "@" in email)
        return self.dedupe_recipients(recipients)

    def dedupe_recipients(self, recipients: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for recipient in recipients:
            normalized = recipient.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    async def send_and_log(
        self,
        db: AsyncSession,
        application_id: int | None,
        recipients: list[str],
        notification_type: str,
        subject: str,
        body: str,
    ) -> None:
        deduped = self.dedupe_recipients(recipients)
        if not deduped:
            db.add(
                NotificationLog(
                    application_id=application_id,
                    recipient="",
                    notification_type=notification_type,
                    status="skipped",
                    error_message="No notification recipients configured",
                )
            )
            return

        for recipient in deduped:
            status = "skipped"
            error_message = None
            try:
                status = email_service.send_text_email(
                    recipient=recipient,
                    subject=subject,
                    body=body,
                )
            except Exception as exc:
                status = "failed"
                error_message = str(exc)

            db.add(
                NotificationLog(
                    application_id=application_id,
                    recipient=recipient,
                    notification_type=notification_type,
                    status=status,
                    error_message=error_message,
                    sent_at=datetime.now(timezone.utc) if status == "sent" else None,
                )
            )

    async def notify_admins(
        self,
        db: AsyncSession,
        application: object,
        notification_type: str,
        subject: str,
        body: str,
    ) -> None:
        recipients = await self.get_admin_recipients(db)
        await self.send_and_log(
            db=db,
            application_id=getattr(application, "id", None),
            recipients=recipients,
            notification_type=notification_type,
            subject=subject,
            body=body,
        )


notification_service = NotificationService()
