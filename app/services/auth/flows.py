from beanie import PydanticObjectId
from fastapi import HTTPException, Depends
from fastapi_users import exceptions
from starlette import status

from . import models, manager, service


async def get(order_id: PydanticObjectId) -> models.User:
    user = await models.User.get(order_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "An user with this id does not exist."}],
        )
    return user


async def resolve_user(
        user_id: str,
        user_manager: manager.UserManager = Depends(manager.get_user_manager),
        user: models.User = Depends(service.current_active_user)
) -> models.User:
    if user_id == "@me":
        return user
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A user with this id does not exist."}],
        )
    try:
        parsed_id = user_manager.parse_id(user_id)
        return await models.User.get(parsed_id)
    except (exceptions.UserNotExists, exceptions.InvalidID):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A user with this id does not exist."}],
        )


async def get_user(user_id: PydanticObjectId):
    user = await models.User.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A user with this id does not exist."}],
        )
    return user


async def get_booster_by_name(name: str) -> models.User:
    user = await models.User.find_one({"name": name})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A user with this username does not exist."}],
        )
    return user


async def get_superusers_with_google():
    return await models.User.find({"is_superuser": True, "google": {"$not": {"google": None}}}).to_list()
