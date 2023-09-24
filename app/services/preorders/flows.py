from beanie import PydanticObjectId, init_beanie
from fastapi import HTTPException
from starlette import status

from app import db
from app.core import config
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A preorder with this id does not exist."}],
        )
    return order


async def get_order_id(order_id: str) -> models.PreOrder:
    order = await service.get_order_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A preorder with this id does not exist."}],
        )
    return order


async def create(order_in: models.PreOrderCreate) -> models.PreOrder:
    order = await service.create(order_in)
    settings = await settings_service.get()
    tasks_service.delete_expired_preorder.apply_async((str(order.id),), countdown=settings.preorder_time_alive)
    return order


async def delete(order_id: PydanticObjectId):
    await init_beanie(connection_string=config.app.mongo_dsn, document_models=db.get_beanie_models())
    order = await service.get(order_id)
    if not order:
        return
    if not order.has_response:
        parser = await sheets_service.get_by_spreadsheet_sheet_read(order.spreadsheet, order.sheet_id)
        creds = await auth_service.get_first_superuser()
        sheets_service.clear_row(creds.google, parser, order.row_id)

    await service.delete(order.id)
    payload = await message_service.pull_order_delete(await format_preorder_system(order), pre=True)
    message_service.send_deleted_order_notify(order.order_id, payload)


async def format_preorder_system(order: models.PreOrder):
    data = dict(order)
    booster_price = order.price.price_booster_dollar
    if booster_price:
        price = models.PreOrderPriceSystem(
            price_dollar=order.price.price_dollar,
            price_booster_dollar_without_fee=booster_price,
            price_booster_dollar=await currency_flows.usd_to_currency(booster_price, order.date, with_fee=True),
            price_booster_rub=await currency_flows.usd_to_currency(booster_price, order.date, "RUB", with_fee=True),
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
        )
    else:
        price = models.PreOrderPriceUser()
    data["price"] = price
    return models.PreOrderReadUser.model_validate(data)
