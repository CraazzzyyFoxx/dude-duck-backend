import contextlib

from beanie import PydanticObjectId
from fastapi import Depends, HTTPException
from fastapi_users import FastAPIUsers, exceptions
from starlette import status

from app.services.auth.manager import get_user_manager

from . import models, service, utils

fastapi_users = (FastAPIUsers[models.User, PydanticObjectId]
                 (get_user_manager, [utils.auth_backend_api, utils.auth_backend_db]))
current_active_user = fastapi_users.current_user(
    active=True,
    get_enabled_backends=utils.get_enabled_backends
)
current_active_superuser = fastapi_users.current_user(
    active=True,
    superuser=True,
    get_enabled_backends=utils.get_enabled_backends
)
current_active_verified = fastapi_users.current_user(
    active=True,
    verified=True,
    get_enabled_backends=utils.get_enabled_backends
)

current_active_superuser_api = fastapi_users.current_user(
    active=True,
    superuser=True,
    get_enabled_backends=utils.get_enabled_backends_api
)

get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)


async def resolve_user(
        user_id: str,
        user_manager=Depends(get_user_manager),
        user: models.User = Depends(current_active_user)
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
    user = await service.get(user_id)
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
