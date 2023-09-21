import typing

from beanie import PydanticObjectId
from fastapi import HTTPException
from starlette import status

from ...core import config
from . import models


async def get(order_id: PydanticObjectId) -> models.User:
    user = await models.User.get(order_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "An user with this id does not exist."}],
        )
    return user


async def get_all() -> list[models.User]:
    return await models.User.find_all().to_list()


async def update(user: models.User, user_in: models.UserUpdate):
    user_order_data = user.model_dump()
    update_data = user_in.model_dump(exclude_none=True)

    for field in user_order_data:
        if field in update_data:
            setattr(user, field, update_data[field])

    await user.save_changes()
    return user


async def get_first_superuser() -> models.User:
    return await models.User.find_one({"name": config.app.super_user_username})


async def get_superusers_with_google():
    return await models.User.find({"is_superuser": True, "google": {"$ne": None}}).to_list()


async def get_by_ids(users_id: typing.Iterable[PydanticObjectId]) -> list[models.User]:
    return await models.User.find({"_id": {"$in": users_id}}).to_list()
