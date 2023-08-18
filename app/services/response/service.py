from datetime import datetime

from beanie import PydanticObjectId

from . import models


async def get(response_id: PydanticObjectId) -> models.OrderResponse:
    return await models.OrderResponse.find_one({"_id": response_id}, fetch_links=True)


async def create(response_in: models.OrderResponseCreate):
    response = models.OrderResponse(**response_in.model_dump())
    response.created_at = datetime.utcnow()
    return await response.create()


async def delete(response_id: PydanticObjectId):
    user_order = await models.OrderResponse.get(response_id)
    await user_order.delete()


async def get_by_order_id(order_id: PydanticObjectId) -> list[models.OrderResponse]:
    return await models.OrderResponse.find(models.OrderResponse.order.id == order_id, fetch_links=True).to_list()


async def get_by_user_id(user_id: PydanticObjectId) -> list[models.OrderResponse]:
    return await models.OrderResponse.find(models.OrderResponse.user.id == user_id, fetch_links=True).to_list()


async def get_by_order_id_user_id(order_id: PydanticObjectId, user_id: PydanticObjectId) -> models.OrderResponse:
    return await models.OrderResponse.find_one(models.OrderResponse.order.id == order_id,
                                               models.OrderResponse.user.id == user_id, fetch_links=True)


async def get_all() -> list[models.OrderResponse]:
    return await models.OrderResponse.find({}, fetch_links=True).to_list()


async def update(response: models.OrderResponse, response_in: models.OrderResponseUpdate):
    report_data = response.model_dump()
    update_data = response_in.model_dump(exclude_none=True)

    for field in report_data:
        if field in update_data:
            setattr(response, field, update_data[field])

    await response.save_changes()
    return response
