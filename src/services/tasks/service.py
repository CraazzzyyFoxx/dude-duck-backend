import asyncio

import sentry_sdk
from celery import Celery
from celery.signals import celeryd_init
from sentry_sdk.integrations.celery import CeleryIntegration

from src.core import config
from src.core.config import app
from src.services.auth import models as auth_models
from src.services.preorders import tasks as preorders_tasks
from src.services.sheets import models as sheets_models
from src.services.sheets import service as sheets_service
from src.services.sheets import tasks as sheets_tasks

from . import celery_config

celery = Celery(
    __name__,
    broker=app.celery_broker_url.unicode_string(),
    backend=app.celery_result_backend.unicode_string(),
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
}
celery.conf.timezone = "UTC"


@celery.task(name="sync_data")
def sync_data():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(sheets_tasks.sync_orders())


@celery.task(name="update_order")
def update_order(creds: dict, parser: str, row_id: int, data: dict):
    parser_model = sheets_models.OrderSheetParseRead.model_validate_json(parser)
    sheets_service.update_row_data(creds, parser_model, row_id, data)


@celery.task(name="create_booster")
def create_booster(creds: dict, parser: str, data: dict):
    parser_model = sheets_models.OrderSheetParseRead.model_validate_json(parser)
    sheets_service.create_row_data(auth_models.UserReadSheets, creds, parser_model, data)


@celery.task(name="create_or_update_booster")
def create_or_update_booster(creds: dict, parser: str, value: str, data: dict):
    parser_model = sheets_models.OrderSheetParseRead.model_validate_json(parser)
    sheets_service.create_or_update_booster(creds, parser_model, value, data)


@celery.task(name="delete_booster")
def delete_booster(creds: dict, parser: str, value: str):
    parser_model = sheets_models.OrderSheetParseRead.model_validate_json(parser)
    sheets_service.delete_booster(creds, parser_model, value)


@celery.task(name="manage_preorders")
def manage_preorders():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(preorders_tasks.manage_preorders())
