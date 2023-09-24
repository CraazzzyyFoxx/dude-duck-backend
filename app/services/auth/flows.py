from typing import Annotated

from beanie import PydanticObjectId
from fastapi import Depends
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from starlette import status

from app.core import errors

from . import models, service

oauth2_scheme = OAuth2PasswordBearer("auth/login", auto_error=False)
bearer_scheme_api = HTTPBearer(bearerFormat="Bearer")


async def get(user_id: PydanticObjectId):
    user = await service.get(user_id)
    if not user:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A user with this id does not exist.", code="not_exist")],
        )
    return user


async def get_booster_by_name(name: str) -> models.User:
    user = await service.get_by_name(name)
    if not user:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A user with this username does not exist.", code="not_exist")],
        )
    return user


async def get_by_email(email: str):
    user = await service.get_by_email(email)
    if not user:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A user with this email does not exist.", code="not_exist")],
        )
    return user


def verify_user(
    user: models.User | None,
    active: bool = False,
    verified: bool = False,
    superuser: bool = False,
) -> bool:
    status_code = status.HTTP_401_UNAUTHORIZED
    if user:
        status_code = status.HTTP_403_FORBIDDEN
        if active and not user.is_active:
            status_code = status.HTTP_401_UNAUTHORIZED
            user = None
        elif verified and not user.is_verified or superuser and not user.is_superuser:
            user = None
    if not user:
        raise errors.DudeDuckHTTPException(
            status_code=status_code,
            detail=[],
        )

    return True


async def get_current_user(
    token: str,
    active: bool = False,
    verified: bool = False,
    superuser: bool = False,
):
    user: models.User | None = None
    if token is not None:
        user = await service.read_token(token)
    verify_user(user, active, verified, superuser)
    return user, token


async def get_current_user_api(
    token: str,
    active: bool = False,
    verified: bool = False,
    superuser: bool = False,
):
    user: models.User | None = None
    if token is not None:
        user = await service.read_token(token)
    verify_user(user, active, verified, superuser)
    return user, token


def current_user(
    active: bool = False,
    verified: bool = False,
    superuser: bool = False,
):
    async def current_user_dependency(token: Annotated[str, Depends(oauth2_scheme)]):
        user, _ = await get_current_user(
            token,
            active=active,
            verified=verified,
            superuser=superuser,
        )
        return user

    return current_user_dependency


def current_user_token(active: bool = True, verified: bool = False, superuser: bool = False):
    async def current_user_dependency(token: Annotated[str, Depends(oauth2_scheme)]):
        user, token = await get_current_user(
            token,
            active=active,
            verified=verified,
            superuser=superuser,
        )
        return user, token

    return current_user_dependency


def current_user_api(
    active: bool = False,
    verified: bool = False,
    superuser: bool = False,
):
    async def current_user_dependency(
        token: Annotated[str, Depends(bearer_scheme_api)],
    ):
        user, _ = await get_current_user(
            token,
            active=active,
            verified=verified,
            superuser=superuser,
        )
        return user

    return current_user_dependency


current_active = current_user(active=True)
current_active_superuser = current_user(active=True, superuser=True)
current_active_verified = current_user(active=True, verified=True)
current_active_superuser_api = current_user(active=True, superuser=True)


async def resolve_user(
    user_id: PydanticObjectId | str,
    user: models.User = Depends(current_active),
) -> models.User:
    if user_id == "@me":
        return user
    if not user.is_superuser:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A user with this id does not exist.", code="not_exist")],
        )
    user = await service.get(PydanticObjectId(user_id))
    if not user:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A user with this id does not exist.", code="not_exist")],
        )
    return user
