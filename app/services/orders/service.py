import asyncio
from datetime import datetime

from beanie import PydanticObjectId

from app.services.auth.models import User
from app.services.sheets.flows import GoogleSheetsServiceManager
from app.services.accounting import service as accounting_service


from . import models
from . import schemas


def format_by_perms(user: User, order: models.Order) -> schemas.OrderReadMeta:
    if user.is_superuser:
        return schemas.OrderRead.model_construct(**dict(order))
    else:
        return schemas.OrderReadUser.model_construct(**dict(order))


def format_many_by_perms(user: User, orders: list[models.Order]) -> list[schemas.OrderReadMeta]:
    schema = schemas.OrderRead if user.is_superuser else schemas.OrderReadUser
    return [schema.model_construct(**dict(order)) for order in orders]


async def get(order_id: PydanticObjectId) -> models.Order | None:
    return await models.Order.find_one({"_id": order_id, "archive": False})


async def get_order_id(order_id: str) -> models.Order | None:
    return await models.Order.find_one({"order_id": order_id, "archive": False})


async def get_all() -> list[models.Order]:
    return await models.Order.find({}).to_list()


async def get_all_by_sheet(spreadsheet: str, sheet: int) -> list[models.Order]:
    return await models.Order.find({"spreadsheet": spreadsheet, "sheet_id": sheet, "archive": False}).to_list()


async def get_all_from_datetime_range(start: datetime, end: datetime) -> list[models.Order]:
    return await models.Order.find({"$gte": {"date": start}, "$lte": {"date": end}, "archive": False}).to_list()


async def get_all_from_datetime_range_by_sheet(
        spreadsheet: str,
        sheet: int,
        start: datetime,
        end: datetime
) -> list[models.Order]:
    return await models.Order.find(
        {"spreadsheet": spreadsheet, "sheet": sheet, "$gte": {"date": start}, "$lte": {"date": end}, "archive": False}
    ).to_list()


async def update_with_sync(order: models.Order, user_order_in: models.OrderUpdate):
    order = await update(order, user_order_in)
    asyncio.create_task(GoogleSheetsServiceManager
                        .get()
                        .update_row_data(models.Order, order.spreadsheet, order.sheet_id, order.row_id, user_order_in))

    return order


async def update(order: models.Order, user_order_in: models.OrderUpdate):
    old = order.model_copy(deep=True)
    update_price = False
    order_data = dict(order)
    update_data = user_order_in.model_dump(exclude_none=True)

    for field in order_data:
        if field in update_data:
            if isinstance(update_data[field], dict):
                sub_order_data = order_data[field]
                sub_update_data = update_data[field]
                for sub_field in sub_update_data:

                    setattr(sub_order_data, sub_field, sub_update_data[sub_field])
            else:
                setattr(order, field, update_data[field])
            if field.startswith("price"):
                update_price = True

    await order.save_changes()

    if update_price:
        await accounting_service.update_booster_price(old, order)

    return order


async def to_archive(order_id: PydanticObjectId):
    order = await get(order_id)
    await update(order, models.OrderUpdate(archive=True))


async def create(order_in: models.OrderCreate) -> models.Order:
    order = models.Order(**order_in.model_dump())
    return await order.create()
