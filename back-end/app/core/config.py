from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "MeiyuSystem API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://meiyu:meiyu_password@localhost:5432/meiyu_system"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    refresh_token_expire_days: int = 30

    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 30

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_security: str = "starttls"
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    admin_notification_email_csv: str = ""

    initial_admin_account: str | None = None
    initial_admin_password: str | None = None

    ai_api_base_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str = "Ali-dashscope/MiniMax-M2.5"
    ai_timeout_seconds: float = 60

    sdu_auth_base_url: str = "https://pass.sdu.edu.cn"
    sdu_service_url: str = "https://service.sdu.edu.cn/tp_up/view?m=up"

    cors_origin_csv: str = Field(default="http://localhost:5173,http://127.0.0.1:5173,http://tauri.localhost,https://tauri.localhost,tauri://localhost")

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origin_csv.split(",") if origin.strip()]

    @cached_property
    def admin_notification_emails(self) -> list[str]:
        return [
            email.strip()
            for email in self.admin_notification_email_csv.split(",")
            if email.strip()
        ]

    def validate_production(self) -> None:
        if self.app_env != "production":
            return
        if len(self.jwt_secret_key) < 32 or self.jwt_secret_key == "change-me-in-production":
            raise RuntimeError("Production requires a unique JWT secret of at least 32 characters")
        if self.initial_admin_password and len(self.initial_admin_password) < 20:
            raise RuntimeError("Production bootstrap password must contain at least 20 characters")
        if self.ai_api_key and not (self.ai_api_base_url or "").startswith("https://"):
            raise RuntimeError("Production AI credentials require an HTTPS endpoint")
        if self.smtp_password and self.smtp_security.lower() not in {"starttls", "ssl"}:
            raise RuntimeError("Production SMTP credentials require TLS")


settings = Settings()
