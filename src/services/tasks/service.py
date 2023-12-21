import asyncio

import sentry_sdk
from celery import Celery
from celery.signals import celeryd_init
from sentry_sdk.integrations.celery import CeleryIntegration

from src import models
from src.core import config, db
from src.services.auth import tasks as auth_tasks
from src.services.integrations.sheets import service as sheets_service
from src.services.integrations.sheets import tasks as sheets_tasks
from src.services.preorder import tasks as preorders_tasks

from . import celery_config

celery = Celery(
    __name__,
    broker=config.app.celery_broker_url.unicode_string(),
    backend=config.app.celery_result_backend.unicode_string(),
    broker_connection_retry_on_startup=True,
)
celery.config_from_object(celery_config)


@celeryd_init.connect
def init_sentry(**kwargs):
    sentry_sdk.init(
        dsn=config.app.sentry_dsn,
        integrations=[CeleryIntegration(monitor_beat_tasks=True)],
        environment="development" if config.app.debug else "production",
        release=config.app.project_version,
    )


celery.conf.beat_schedule = {
    "sync-data-every-5-minutes": {
        "task": "sync_data",
        "schedule": config.app.celery_sheets_sync_time,
    },
    "manage_preorders-every-5-minutes": {
        "task": "manage_preorders",
        "schedule": config.app.celery_preorders_manage,
    },
    "remove_expired_tokens-every-5-minutes": {
        "task": "remove_expired_tokens",
        "schedule": config.app.celery_remove_expired_tokens,
    },
}
celery.conf.timezone = "UTC"


@celery.task(name="sync_data")
def sync_data():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(sheets_tasks.sync_orders())


@celery.task(name="update_order")
def update_order(parser: dict, row_id: int, data: dict):
    with db.session_maker() as session:
        creds = sheets_service.get_first_superuser_token_sync(session)
    parser_model = models.OrderSheetParseRead.model_validate(parser)
    sheets_service.update_row_data(creds.token, parser_model, row_id, data)


@celery.task(name="create_booster")
def create_booster(parser: str, data: dict):
    with db.session_maker() as session:
        creds = sheets_service.get_first_superuser_token_sync(session)
    parser_model = models.OrderSheetParseRead.model_validate_json(parser)
    sheets_service.create_row_data(models.UserReadSheets, creds.token, parser_model, data)


@celery.task(name="create_or_update_booster")
def create_or_update_booster(parser: str, value: str, data: dict):
    with db.session_maker() as session:
        creds = sheets_service.get_first_superuser_token_sync(session)
    parser_model = models.OrderSheetParseRead.model_validate_json(parser)
    sheets_service.create_or_update_booster(creds.token, parser_model, value, data)


@celery.task(name="delete_booster")
def delete_booster(parser: str, value: str):
    with db.session_maker() as session:
        creds = sheets_service.get_first_superuser_token_sync(session)
    parser_model = models.OrderSheetParseRead.model_validate_json(parser)
    sheets_service.delete_booster(creds.token, parser_model, value)


@celery.task(name="manage_preorders")
def manage_preorders():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(preorders_tasks.manage_preorders())


@celery.task(name="remove_expired_tokens")
def remove_expired_tokens():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(auth_tasks.remove_expired_tokens())
