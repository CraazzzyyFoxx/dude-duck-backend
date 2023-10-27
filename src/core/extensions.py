import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.atexit import AtexitIntegration
from sentry_sdk.integrations.dedupe import DedupeIntegration
from sentry_sdk.integrations.excepthook import ExcepthookIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration
from sentry_sdk.integrations.modules import ModulesIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration

from src.core import config

sentry_logging = LoguruIntegration(level=20, event_level=40)


def configure_extensions() -> None:
    logger.info("Configuring extensions...")
    if config.app.sentry_dsn:
        sentry_sdk.init(
            dsn=config.app.sentry_dsn,
            integrations=[
                AtexitIntegration(),
                DedupeIntegration(),
                ExcepthookIntegration(),
                ModulesIntegration(),
                StdlibIntegration(),
                FastApiIntegration(),
                HttpxIntegration(),
                sentry_logging,
            ],
            environment="development" if config.app.debug else "production",
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
