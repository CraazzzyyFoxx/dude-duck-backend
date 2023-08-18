from pathlib import Path

from pydantic import MongoDsn, EmailStr
from pydantic_settings import SettingsConfigDict, BaseSettings


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    # Application
    project_name: str = "Dude Duck CRM"
    project_version: str = "0.0.1"
    debug: bool = True

    # CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000"]'
    cors_origins: list[str] = []
    use_correlation_id: bool = False

    host: str
    port: int

    # Logging
    log_level: str = "info"
    logs_root_path: str = f"{Path.cwd()}/logs"
    sentry_dsn: str | None = None

    # Telegram Bot
    frontend_token: str
    frontend_url: str

    # MongoDB
    mongo_name: str
    mongo_dsn: MongoDsn

    # JWT
    secret: str
    algorithm: str = 'HS256'
    expires_s: int = 3600

    # super user
    super_user_username: str
    super_user_email: EmailStr
    super_user_password: str

    username_regex: str = r"([\w{L} ()]+)"

    accounting_precision_dollar: int = 2
    accounting_precision_rub: int = 0
    accounting_precision_gold: int = 0


app = AppConfig(_env_file='.env', _env_file_encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
GOOGLE_CONFIG_FILE = BASE_DIR / "google.json"
