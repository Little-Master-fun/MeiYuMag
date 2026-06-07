import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailService:
    def is_configured(self) -> bool:
        return bool(settings.smtp_host and settings.smtp_from)

    def send_text_email(self, recipient: str, subject: str, body: str) -> str:
        if not self.is_configured():
            return "skipped"

        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp_security = settings.smtp_security.lower()
            if smtp_security == "starttls":
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        return "sent"


email_service = EmailService()
