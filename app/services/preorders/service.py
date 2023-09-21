from beanie import PydanticObjectId

from . import models


async def get(order_id: PydanticObjectId) -> models.PreOrder | None:
    return await models.PreOrder.find_one({"_id": order_id})


async def get_all() -> list[models.PreOrder]:
    return await models.PreOrder.find({}).to_list()


async def get_all_by_sheet(spreadsheet: str, sheet: int) -> list[models.PreOrder]:
    return await models.PreOrder.find({"spreadsheet": spreadsheet, "sheet_id": sheet}).to_list()


async def get_all_by_sheet_entity(spreadsheet: str, sheet: int, row_id: int) -> list[models.PreOrder]:
    return await models.PreOrder.find({"spreadsheet": spreadsheet, "sheet_id": sheet, "row_id": row_id}).to_list()


async def get_order_id(order_id: str) -> models.PreOrder | None:
    return await models.PreOrder.find_one({"order_id": order_id})


async def update(order: models.PreOrder, user_order_in: models.PreOrderUpdate):
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

    await order.save_changes()
    return order


async def create(order_in: models.PreOrderCreate) -> models.PreOrder:
    data = models.PreOrder(**order_in.model_dump())
    order = await data.create()
    return order


async def delete(order_id: PydanticObjectId):
    order = await get(order_id)
    if order:
        await order.delete()
