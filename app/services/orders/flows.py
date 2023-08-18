from fastapi import HTTPException
from starlette import status
from beanie import PydanticObjectId

from . import service, models


async def get(order_id: PydanticObjectId) -> models.Order:
    order = await service.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A order with this id does not exist."}],
        )
    return order


async def get_by_order_id(order_id: str) -> models.Order:
    order = await service.get_order_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A order with this id does not exist."}],
        )
    return order


async def create(order_in: models.OrderCreate) -> models.Order:
    order = await service.get_order_id(order_in.order_id)
    if order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[{"msg": "A order with this order_id already exists."}],
        )
    order = await service.create(order_in)
    return order
