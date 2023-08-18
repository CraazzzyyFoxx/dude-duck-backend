from fastapi import HTTPException
from starlette import status
from beanie import PydanticObjectId

from . import service, models


async def get(order_id: PydanticObjectId) -> models.User:
    user = await models.User.get(order_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "An user with this id does not exist."}],
        )
    return user


async def get_by_username(username: str) -> models.User:
    user = await service.get_booster_by_name(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "An user with this id does not exist."}],
        )
    return user
