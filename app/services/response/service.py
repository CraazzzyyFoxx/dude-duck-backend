from datetime import datetime

from beanie import PydanticObjectId

from . import models


async def get(response_id: PydanticObjectId) -> models.Response | None:
    return await models.Response.find_one({"_id": response_id}, fetch_links=True)


async def create(response_in: models.ResponseCreate):
    response = models.Response(order=response_in.order_id,
                               user=response_in.user_id,
                               extra=response_in.extra)
    response.created_at = datetime.utcnow()
    return await response.create()


async def delete(response_id: PydanticObjectId):
    user_order = await models.Response.get(response_id)
    await user_order.delete()


async def get_by_order_id(order_id: PydanticObjectId) -> list[models.Response]:
    return await models.Response.find(models.Response.order.id == order_id, fetch_links=True).to_list()


async def get_by_user_id(user_id: PydanticObjectId) -> list[models.Response]:
    return await models.Response.find(models.Response.user.id == user_id, fetch_links=True).to_list()


async def get_by_order_id_user_id(order_id: PydanticObjectId, user_id: PydanticObjectId) -> models.Response | None:
    return await models.Response.find_one(models.Response.order.id == order_id,
                                          models.Response.user.id == user_id, fetch_links=True)


async def get_all() -> list[models.Response]:
    return await models.Response.find({}, fetch_links=True).to_list()


async def update(response: models.Response, response_in: models.ResponseUpdate):
    report_data = response.model_dump()
    update_data = response_in.model_dump(exclude_none=True)

    for field in report_data:
        if field in update_data:
            if field == "approved":
                if update_data[field] is True:
                    response.approved_at = datetime.utcnow()
            setattr(response, field, update_data[field])

    await response.save_changes()
    return response
