from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src import models
from src.core import config, db, errors

from . import service

oauth2_scheme = OAuth2PasswordBearer("auth/login", auto_error=False)
bearer_scheme_api = HTTPBearer(bearerFormat="Bearer")


async def get(session: AsyncSession, user_id: int):
    user = await service.get(session, user_id)
    if not user:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="A user with this id does not exist.", code="not_exist")],
        )
    return user


async def get_by_email(session: AsyncSession, email: str):
    user = await service.get_by_email(session, email)
    if not user:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="A user with this email does not exist.", code="not_exist")],
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
        raise errors.ApiHTTPException(
            status_code=status_code,
            detail=[errors.ApiException(msg="Missing Permissions", code="unauthorized")],
        )

    return True


async def get_current_user(
    session: AsyncSession,
    token: str,
    active: bool = False,
    verified: bool = False,
    superuser: bool = False,
    api: bool = False,
):
    user: models.User | None = None
    if token is not None:
        if api:
            user = await service.read_token_api(session, token)
        else:
            user = await service.verify_access_token(session, token)
    verify_user(user, active, verified, superuser)
    return user, token


def current_user(
    active: bool = False,
    verified: bool = False,
    superuser: bool = False,
):
    async def current_user_dependency(
        token: Annotated[str, Depends(oauth2_scheme)],
        session: Annotated[AsyncSession, Depends(db.get_async_session)],
    ):
        user, _ = await get_current_user(session, token, active=active, verified=verified, superuser=superuser)
        return user

    return current_user_dependency


def current_user_api(
    active: bool = False,
    verified: bool = False,
    superuser: bool = False,
):
    async def current_user_dependency(
        token: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme_api)],
        session: Annotated[AsyncSession, Depends(db.get_async_session)],
    ):
        user, _ = await get_current_user(
            session,
            token.credentials,
            active=active,
            verified=verified,
            superuser=superuser,
            api=True,
        )
        return user

    return current_user_dependency


current_active = current_user(active=True)
current_active_superuser = current_user(active=True, superuser=True)
current_active_verified = current_user(active=True, verified=True)
current_active_superuser_api = current_user_api(active=True, superuser=True)


async def resolve_user(
    user_id: int | str,
    user: models.User = Depends(current_active),
    session: AsyncSession = Depends(db.get_async_session),
) -> models.User:
    if user_id == "@me":
        return user
    if not user.is_superuser:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="A user with this id does not exist.", code="not_exist")],
        )
    user = await service.get(session, int(user_id))
    if not user:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="A user with this id does not exist.", code="not_exist")],
        )
    return user


async def create_first_superuser(session: AsyncSession):
    if not await service.get_first_superuser(session):
        await service.create(
            session,
            models.UserCreate(
                email=config.app.super_user_email,
                password=config.app.super_user_password,
                name=config.app.super_user_username,
            ),
        )
