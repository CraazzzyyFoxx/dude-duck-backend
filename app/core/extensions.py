import logging

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration
from sentry_sdk.integrations.excepthook import ExcepthookIntegration
from sentry_sdk.integrations.dedupe import DedupeIntegration
from sentry_sdk.integrations.atexit import AtexitIntegration
from sentry_sdk.integrations.modules import ModulesIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.pymongo import PyMongoIntegration

from app.core import config

log = logging.getLogger(__file__)

sentry_logging = LoggingIntegration(
    level=logging.INFO,  # Capture info and above as breadcrumbs
    event_level=logging.ERROR,  # Send errors as events
)


def configure_extensions():
    log.debug("Configuring extensions...")
    if config.app.sentry_dsn:
        sentry_sdk.init(
            dsn=str(config.app.sentry_dsn),
            integrations=[
                AtexitIntegration(),
                DedupeIntegration(),
                ExcepthookIntegration(),
                ModulesIntegration(),
                StdlibIntegration(),
                FastApiIntegration(),
                HttpxIntegration(),
                PyMongoIntegration(),
                sentry_logging,
            ],
            environment="development",
            auto_enabling_integrations=False,
        )
