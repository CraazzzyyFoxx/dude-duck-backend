from datetime import datetime, timedelta

from beanie import PydanticObjectId, init_beanie
from loguru import logger
from starlette import status

from app import db
from app.core import config, errors
from app.services.auth import service as auth_service
from app.services.currency import flows as currency_flows
from app.services.settings import service as settings_service
from app.services.sheets import service as sheets_service
from app.services.tasks import service as tasks_service
from app.services.telegram.message import service as message_service

from . import models, service


async def get(order_id: PydanticObjectId) -> models.PreOrder:
    order = await service.get(order_id)
    if not order:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A preorder with this id does not exist.", code="not_exist")],
        )
    return order


async def get_by_order_id(order_id: str) -> models.PreOrder:
    order = await service.get_order_id(order_id)
    if not order:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A preorder with this id does not exist.", code="not_exist")],
        )
    return order


async def create(order_in: models.PreOrderCreate) -> models.PreOrder:
    order = await service.create(order_in)
    settings = await settings_service.get()
    tasks_service.delete_expired_preorder.apply_async((str(order.id),), countdown=settings.preorder_time_alive)
    return order


async def delete(order_id: PydanticObjectId) -> None:
    order = await get(order_id)
    if order:
        await service.delete(order.id)


async def format_preorder_system(order: models.PreOrder):
    data = dict(order)
    booster_price = order.price.price_booster_dollar
    if booster_price:
        price = models.PreOrderPriceSystem(
            price_dollar=order.price.price_dollar,
            price_booster_dollar_without_fee=booster_price,
            price_booster_dollar=await currency_flows.usd_to_currency(booster_price, order.date, with_fee=True),
            price_booster_rub=await currency_flows.usd_to_currency(booster_price, order.date, "RUB", with_fee=True),
            price_booster_gold=order.price.price_booster_gold,
        )
    else:
        price = models.PreOrderPriceSystem(price_dollar=order.price.price_dollar)
    data["price"] = price
    return models.PreOrderReadSystem.model_validate(data)


async def format_preorder_perms(order: models.PreOrder):
    data = dict(order)
    booster_price = order.price.price_booster_dollar
    if booster_price:
        price = models.PreOrderPriceUser(
            price_booster_dollar=await currency_flows.usd_to_currency(booster_price, order.date, with_fee=True),
            price_booster_rub=await currency_flows.usd_to_currency(booster_price, order.date, "RUB", with_fee=True),
            price_booster_gold=order.price.price_booster_gold,
        )
    else:
        price = models.PreOrderPriceUser()
    data["price"] = price
    return models.PreOrderReadUser.model_validate(data)


async def manage_preorders():
    await init_beanie(connection_string=config.app.mongo_dsn, document_models=db.get_beanie_models())
    superuser = await auth_service.get_first_superuser()
    settings = await settings_service.get()
    if superuser.google is None:
        logger.warning("Manage preorders skipped, google token for first superuser missing")
        return

    preorders = await service.get_all()
    for preorder in preorders:
        if preorder.created_at < datetime.utcnow() - timedelta(seconds=settings.preorder_time_alive):
            await preorder.delete()
            payload = await message_service.order_delete(await format_preorder_system(preorder), pre=True)
            if payload.deleted:
                message_service.send_deleted_order_notify(preorder.order_id, payload)
            if preorder.has_response is False:
                parser = await sheets_service.get_by_spreadsheet_sheet_read(preorder.spreadsheet, preorder.sheet_id)
                sheets_service.clear_row(superuser.google, parser, preorder.row_id)
