from datetime import datetime

from . import models


async def get(response_id: int, pre: bool = False) -> models.BaseResponse | None:
    model = models.Response if not pre else models.PreResponse
    return await model.filter(id=response_id).first()


async def create(response_in: models.ResponseCreate, pre: bool = False) -> models.BaseResponse:
    model = models.Response if not pre else models.PreResponse
    response = model(**response_in.model_dump())
    response.created_at = datetime.utcnow()
    await response.save()
    return response


async def delete(response_id: int, pre: bool = False) -> None:
    response = await get(response_id, pre=pre)
    if response:
        await response.delete()


async def get_by_order_id(order_id: int, prefetch: bool = False, pre: bool = False) -> list[models.BaseResponse]:
    model = models.Response if not pre else models.PreResponse
    query = model.filter(order_id=order_id)
    if prefetch:
        query = query.prefetch_related("user")
    return await query


async def get_by_user_id(user_id: int, pre: bool = False) -> list[models.BaseResponse]:
    model = models.Response if not pre else models.PreResponse
    return await model.filter(user_id=user_id)


async def get_by_order_id_user_id(order_id: int, user_id: int, pre: bool = False) -> models.BaseResponse | None:
    model = models.Response if not pre else models.PreResponse
    return await model.filter(order_id=order_id, user_id=user_id).first()


async def get_all(pre: bool = False) -> list[models.BaseResponse]:
    model = models.Response if not pre else models.PreResponse
    return await model.filter().all()


async def update(
    response: models.BaseResponse,
    response_in: models.ResponseUpdate,
) -> models.BaseResponse:
    update_data = response_in.model_dump()
    response = response.update_from_dict(update_data)
    if "approved" in update_data:
        response.approved_at = datetime.utcnow()
    await response.save()
    return response


async def patch(
    response: models.BaseResponse,
    response_in: models.ResponseUpdate,
) -> models.BaseResponse:
    update_data = response_in.model_dump(exclude_none=True, exclude_defaults=True)
    response = response.update_from_dict(update_data)
    if "approved" in update_data:
        response.approved_at = datetime.utcnow()
    await response.save(update_fields=update_data.keys())
    return response
