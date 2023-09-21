from datetime import datetime

from beanie import PydanticObjectId

from . import models


async def get(response_id: PydanticObjectId) -> models.Response | None:
    return await models.Response.find_one({"_id": response_id})


async def create(response_in: models.ResponseCreate) -> models.Response:
    response = models.Response(order_id=response_in.order_id, user_id=response_in.user_id, extra=response_in.extra)
    response.created_at = datetime.utcnow()
    return await response.create()


async def delete(response_id: PydanticObjectId) -> None:
    user_order = await models.Response.get(response_id)
    await user_order.delete()


async def get_by_order_id(order_id: PydanticObjectId) -> list[models.Response]:
    return await models.Response.find({"order_id": order_id}).to_list()


async def get_by_user_id(user_id: PydanticObjectId) -> list[models.Response]:
    return await models.Response.find({"user_id": user_id}).to_list()


async def get_by_order_id_user_id(order_id: PydanticObjectId, user_id: PydanticObjectId) -> models.Response | None:
    return await models.Response.find_one({"order_id": order_id, "user_id": user_id})


async def get_all() -> list[models.Response]:
    return await models.Response.find({}, fetch_links=True).to_list()


async def update(response: models.Response, response_in: models.ResponseUpdate) -> models.Response:
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
