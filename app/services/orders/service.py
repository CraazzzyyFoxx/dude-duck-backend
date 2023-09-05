from datetime import datetime

from beanie import PydanticObjectId
from loguru import logger

from app.services.auth import service as auth_service
from app.services.sheets import flows as sheets_flows
from app.services.accounting import service as accounting_service
from app.services.tasks import service as tasks_service

from . import models


async def get(order_id: PydanticObjectId) -> models.Order | None:
    return await models.Order.find_one({"_id": order_id, "archive": False})


async def get_order_id(order_id: str) -> models.Order | None:
    return await models.Order.find_one({"order_id": order_id, "archive": False})


async def get_all() -> list[models.Order]:
    return await models.Order.find({}).to_list()


async def get_all_by_sheet(spreadsheet: str, sheet: int) -> list[models.Order]:
    return await models.Order.find({"spreadsheet": spreadsheet, "sheet_id": sheet, "archive": False}).to_list()


async def get_all_by_sheet_entity(spreadsheet: str, sheet: int, row_id: int) -> list[models.Order]:
    return await models.Order.find(
        {"spreadsheet": spreadsheet, "sheet_id": sheet, "row_id": row_id, "archive": False}).to_list()


async def get_all_from_datetime_range(start: datetime, end: datetime) -> list[models.Order]:
    return await models.Order.find({"$gte": {"date": start}, "$lte": {"date": end}, "archive": False}).to_list()


async def get_by_ids(ids: list[PydanticObjectId]):
    return await models.Order.find({"_id": {"$in": ids}}).to_list()


async def get_all_from_datetime_range_by_sheet(
        spreadsheet: str,
        sheet: int,
        start: datetime,
        end: datetime
) -> list[models.Order]:
    return await models.Order.find(
        {"spreadsheet": spreadsheet, "sheet": sheet, "$gte": {"date": start}, "$lte": {"date": end}, "archive": False}
    ).to_list()


async def update_with_sync(order: models.Order, order_in: models.OrderUpdate):
    order = await update(order, order_in)
    parser = await sheets_flows.service.get_by_spreadsheet_sheet(order.spreadsheet, order.sheet_id)
    user = await auth_service.get_first_superuser()
    tasks_service.update_order.delay(
        user.google.model_dump_json(),
        parser.model_dump_json(),
        order.row_id,
        order_in.model_dump()
    )

    return order


async def update(order: models.Order, user_order_in: models.OrderUpdate):
    old = order.model_copy(deep=True)
    update_price = False
    order_data = dict(order)
    update_data = user_order_in.model_dump()
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
    await order.delete()
    # await update(order, models.OrderUpdate(archive=True))


async def create(order_in: models.OrderCreate) -> models.Order:
    order = models.Order(**order_in.model_dump())
    return await order.create()
