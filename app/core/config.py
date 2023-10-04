from pathlib import Path

from pydantic import EmailStr, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

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
    log_level: str = "info"
    logs_root_path: str = f"{Path.cwd()}/logs"
    sentry_dsn: str | None = None

    # Telegram Bot
    telegram_token: str
    telegram_url: str
    telegram_integration: bool

    # Postgres
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: str

    # JWT
    secret: str
    algorithm: str = "HS256"
    expires_s: int = 3600
    verification_token_audience: str = "dude_duck:verify"
    reset_password_token_audience: str = "dude_duck:reset"

    # super user
    super_user_username: str
    super_user_email: EmailStr
    super_user_password: str

    username_regex: str = r"([a-zA-Z0-9_-]+)"

    # Celery
    celery_broker_url: RedisDsn
    celery_result_backend: RedisDsn
    celery_sheets_sync_time: int = 300
    celery_preorders_manage: int = 300

    sync_boosters: bool = False


app = AppConfig(_env_file=".env", _env_file_encoding="utf-8")


tortoise = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "database": app.postgres_db,
                "host": app.postgres_host,
                "password": app.postgres_password,
                "port": app.postgres_port,
                "user": app.postgres_user,
            },
        }
    },
    "apps": {
        "main": {
            "models": [
                "aerich.models",
                "app.services.auth.models",
                "app.services.accounting.models",
                "app.services.auth.models",
                "app.services.currency.models",
                "app.services.orders.models",
                "app.services.preorders.models",
                "app.services.response.models",
                "app.services.settings.models",
                "app.services.sheets.models",
            ],
        }
    },
}
