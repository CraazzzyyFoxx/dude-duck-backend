import contextlib

from beanie import PydanticObjectId
from fastapi import Depends, HTTPException
from fastapi_users import FastAPIUsers, exceptions
from fastapi_users.authentication import AuthenticationBackend, BearerTransport
from fastapi_users.authentication.strategy import DatabaseStrategy
from fastapi_users_db_beanie.access_token import BeanieAccessTokenDatabase
from starlette import status

from starlette.requests import Request

from app.services.auth.manager import get_user_manager, UserManager
from .utils import BearerTransportAPI, DatabaseStrategyAPI
from . import models

bearer_transport = BearerTransport(tokenUrl="auth/login")
bearer_transport_api = BearerTransportAPI()


async def get_access_token_db():
    yield BeanieAccessTokenDatabase(models.AccessToken)


async def get_access_token_db_api():
    yield BeanieAccessTokenDatabase(models.AccessTokenAPI)


def get_database_strategy(
        access_token_db: BeanieAccessTokenDatabase = Depends(get_access_token_db),
) -> DatabaseStrategy:
    return DatabaseStrategy(access_token_db, lifetime_seconds=3600 * 24)


def get_database_strategy_api(
        access_token_db: BeanieAccessTokenDatabase = Depends(get_access_token_db_api),
) -> DatabaseStrategy:
    return DatabaseStrategyAPI(access_token_db)


auth_backend_api = AuthenticationBackend(
    name="api_db",
    transport=bearer_transport_api,
    get_strategy=get_database_strategy_api,
)

auth_backend_db = AuthenticationBackend(
    name="db",
    transport=bearer_transport,
    get_strategy=get_database_strategy,
)


async def get_enabled_backends(_: Request):
    return [auth_backend_db]


async def get_enabled_backends_api(_: Request):
    return [auth_backend_api]


fastapi_users = FastAPIUsers[models.User, PydanticObjectId](get_user_manager, [auth_backend_api, auth_backend_db])
current_active_user = fastapi_users.current_user(
    active=True,
    get_enabled_backends=get_enabled_backends
)
current_active_superuser = fastapi_users.current_user(
    active=True,
    superuser=True,
    get_enabled_backends=get_enabled_backends
)
current_active_verified = fastapi_users.current_user(
    active=True,
    verified=True,
    get_enabled_backends=get_enabled_backends
)

current_active_superuser_api = fastapi_users.current_user(
    active=True,
    superuser=True,
    get_enabled_backends=get_enabled_backends_api
)

get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)


async def resolve_user(
        user_id: str,
        user_manager: UserManager = Depends(get_user_manager),
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
    except (exceptions.UserNotExists, exceptions.InvalidID) as e:
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
