from datetime import datetime

from beanie import PydanticObjectId

from app.services.accounting import service as accounting_service
from app.services.auth import service as auth_service
from app.services.sheets import flows as sheets_flows
from app.services.tasks import service as tasks_service

from . import models


async def get(order_id: PydanticObjectId) -> models.Order | None:
    return await models.Order.find_one({"_id": order_id})


async def get_order_id(order_id: str) -> models.Order | None:
    return await models.Order.find_one({"order_id": order_id})


async def get_all() -> list[models.Order]:
    return await models.Order.find({}).to_list()


async def get_all_by_sheet(spreadsheet: str, sheet: int) -> list[models.Order]:
    return await models.Order.find({"spreadsheet": spreadsheet, "sheet_id": sheet}).to_list()


async def get_all_by_sheet_entity(spreadsheet: str, sheet: int, row_id: int) -> list[models.Order]:
    return await models.Order.find(
        {"spreadsheet": spreadsheet, "sheet_id": sheet, "row_id": row_id}).to_list()


async def get_all_from_datetime_range(start: datetime, end: datetime) -> list[models.Order]:
    return await models.Order.find({"date": {"$gte": start, "$lte": end}}).to_list()


async def get_by_ids(ids: list[PydanticObjectId]) -> list[models.Order]:
    return await models.Order.find({"_id": {"$in": ids}}).to_list()


async def get_by_ids_datetime_range(ids: list[PydanticObjectId], start: datetime, end: datetime) -> list[models.Order]:
    return await models.Order.find({"_id": {"$in": ids}, "date": {"$gte": start, "$lte": end}}).to_list()


async def get_by_ids_datetime_range_by_sheet(
        ids: list[PydanticObjectId],
        spreadsheet: str,
        sheet: int,
        start: datetime,
        end: datetime
) -> list[models.Order]:
    return await models.Order.find(
        {
            "spreadsheet": spreadsheet,
            "sheet": sheet,
            "_id": {"$in": ids},
            "date": {"$gte": start, "$lte": end}
        }
    ).to_list()


async def get_all_from_datetime_range_by_sheet(
        spreadsheet: str,
        sheet: int,
        start: datetime,
        end: datetime
) -> list[models.Order]:
    return await models.Order.find(
        {"spreadsheet": spreadsheet, "sheet": sheet, "date": {"$gte": start, "$lte": end}}
    ).to_list()


async def update_with_sync(order: models.Order, order_in: models.OrderUpdate) -> models.Order:
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


async def update(order: models.Order, order_in: models.OrderUpdate) -> models.Order:
    old = order.model_copy(deep=True)
    update_price = False
    order_data = dict(order)
    update_data = order_in.model_dump(exclude_none=True)
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


async def delete(order_id: PydanticObjectId) -> None:
    order = await get(order_id)
    await order.delete()


async def create(order_in: models.OrderCreate) -> models.Order:
    order = models.Order.model_validate(order_in)
    return await order.create()


async def bulk_create(orders_in: list[models.OrderCreate]) -> list[PydanticObjectId]:
    data = await models.Order.insert_many([models.Order.model_validate(order_in) for order_in in orders_in])
    return data.inserted_ids
