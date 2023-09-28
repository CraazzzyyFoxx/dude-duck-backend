import asyncio

from celery import Celery

from app.core import config
from app.core.config import app
from app.services.auth import models as auth_models
from app.services.preorders import tasks as preorders_tasks
from app.services.sheets import models as sheets_models
from app.services.sheets import service as sheets_service
from app.services.sheets import tasks as sheets_tasks

from . import celery_config

celery = Celery(
    __name__,
    broker=app.celery_broker_url.unicode_string(),
    backend=app.celery_result_backend.unicode_string(),
    broker_connection_retry_on_startup=True,
)
celery.config_from_object(celery_config)

celery.conf.beat_schedule = {
    "sync-data-every-5-minutes": {
        "task": "sync_data",
        "schedule": config.app.celery_sheets_sync_time,
    },
}
celery.conf.timezone = "UTC"


@celery.task(name="sync_data")
def sync_data():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(sheets_tasks.sync_orders())


@celery.task(name="update_order")
def update_order(creds: str, parser: str, row_id: int, data: dict):
    parser_model = sheets_models.OrderSheetParseRead.model_validate_json(parser)
    creds_model = auth_models.AdminGoogleToken.model_validate_json(creds)
    sheets_service.update_row_data(creds_model, parser_model, row_id, data)


@celery.task(name="create_booster")
def create_booster(creds: str, parser: str, data: dict):
    parser_model = sheets_models.OrderSheetParseRead.model_validate_json(parser)
    creds_model = auth_models.AdminGoogleToken.model_validate_json(creds)
    sheets_service.create_row_data(auth_models.UserReadSheets, creds_model, parser_model, data)


@celery.task(name="create_or_update_booster")
def create_or_update_booster(creds: str, parser: str, value: str, data: dict):
    parser_model = sheets_models.OrderSheetParseRead.model_validate_json(parser)
    creds_model = auth_models.AdminGoogleToken.model_validate_json(creds)
    sheets_service.create_or_update_booster(creds_model, parser_model, value, data)


@celery.task(name="delete_booster")
def delete_booster(creds: str, parser: str, value: str):
    parser_model = sheets_models.OrderSheetParseRead.model_validate_json(parser)
    creds_model = auth_models.AdminGoogleToken.model_validate_json(creds)
    sheets_service.delete_booster(creds_model, parser_model, value)


@celery.task(name="delete_preorder")
def delete_preorder(creds: str, parser: str, row_id: int):
    parser_model = sheets_models.OrderSheetParseRead.model_validate_json(parser)
    creds_model = auth_models.AdminGoogleToken.model_validate_json(creds)
    sheets_service.clear_row(creds_model, parser_model, row_id)


@celery.task(name="delete_expired_preorder")
def delete_expired_preorder(order_id: str):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(preorders_tasks.delete(order_id))
