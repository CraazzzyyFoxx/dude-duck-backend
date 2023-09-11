from pathlib import Path

from pydantic import EmailStr, RedisDsn
from pydantic_settings import SettingsConfigDict, BaseSettings


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    # Application
    project_name: str = "Dude Duck CRM"
    project_version: str = "1.0.0"
    debug: bool = True

    # CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000"]'
    cors_origins: list[str] = []
    use_correlation_id: bool = False

    port: int

    # Logging
    log_level: int = 20
    logs_root_path: str = f"{Path.cwd()}/logs"
    sentry_dsn: str | None = None

    # Telegram Bot
    frontend_token: str
    frontend_url: str

    # MongoDB
    mongo_dsn: str

    # JWT
    secret: str
    algorithm: str = 'HS256'
    expires_s: int = 3600

    # super user
    super_user_username: str
    super_user_email: EmailStr
    super_user_password: str

    username_regex: str = r"([\w{L}]+)"

    # Celery
    celery_broker_url: RedisDsn
    celery_result_backend: RedisDsn
    celery_sheets_sync_time: int = 300


app = AppConfig(_env_file='.env', _env_file_encoding='utf-8')
