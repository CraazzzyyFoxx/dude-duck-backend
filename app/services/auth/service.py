import secrets
import typing
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
import sqlalchemy as so
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core import config, enums, errors
from app.services.sheets import service as sheets_service
from app.services.tasks import service as tasks_service
from app.services.telegram.message import service as message_service

from . import models, utils


async def get(session: AsyncSession, user_id: int) -> models.User | None:
    query = so.select(models.User).where(models.User.id == user_id).limit(1)
    user = await session.execute(query)
    return user.first()


async def get_by_email(session: AsyncSession, user_email: str) -> models.User | None:
    query = so.select(models.User).where(models.User.email == user_email).limit(1)
    user = await session.execute(query)
    return user.first()


async def get_by_name(session: AsyncSession, username: str) -> models.User | None:
    query = so.select(models.User).where(models.User.name == username).limit(1)
    user = await session.execute(query)
    return user.first()


async def get_all(session: AsyncSession) -> list[models.User]:
    query = so.select(models.User)
    users = await session.execute(query)
    return [user[0] for user in users]


async def get_first_superuser(session: AsyncSession) -> models.User:
    return await get_by_email(session, config.app.super_user_email)  # type: ignore


async def get_superusers_with_google(session: AsyncSession) -> list[models.User]:
    query = so.select(models.User).where(models.User.is_superuser is True, models.User.google is None)
    users = await session.execute(query)
    return [user[0] for user in users]


async def get_by_ids(session: AsyncSession, users_id: typing.Iterable[int]) -> list[models.User]:
    query = so.select(models.User).where(models.User.id.in_(users_id))
    users = await session.execute(query)
    return [user[0] for user in users]


async def create(session: AsyncSession, user_create: models.UserCreate, safe: bool = False) -> models.User:
    if await get_by_email(session, user_create.email) is not None or await get_by_name(session, user_create.name):
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=enums.ErrorCode.REGISTER_USER_ALREADY_EXISTS, code=enums.ErrorCode.REGISTER_USER_ALREADY_EXISTS
                )
            ],
        )
    exclude_fields = {
        "id",
    }
    if safe:
        exclude_fields.update({"is_superuser", "is_active", "is_verified"})
    user_dict = user_create.model_dump(exclude=exclude_fields, exclude_unset=True)
    email: str = user_dict.pop("email")
    password = user_dict.pop("password")
    user_dict["hashed_password"] = utils.hash_password(password)
    user_dict["email"] = email.lower()
    query = so.insert(models.User).returning(models.User)
    result = await session.scalars(query, [user_dict])
    created_user = result.first()
    # parser = await sheets_service.get_default_booster_read()
    # creds = await get_first_superuser(session)
    # if creds.google is not None:
    #     tasks_service.create_booster.delay(
    #         creds.google.model_dump_json(),
    #         parser.model_dump_json(),
    #         models.UserRead.model_validate(created_user).model_dump(),
    #     )
    await session.commit()
    return created_user


async def update(
    session: AsyncSession, user: models.User, user_in: models.BaseUserUpdate, safe: bool = False, exclude=True
) -> models.User:
    exclude_fields = {
        "password",
    }
    if safe:
        exclude_fields.update({"is_superuser", "is_active", "is_verified"})
    update_data = user_in.model_dump(exclude=exclude_fields, exclude_unset=exclude, exclude_defaults=True, mode="json")

    if update_data.get("phone") is not None:
        user.phone = update_data["phone"].replace("tel:", "")
        update_data.pop("phone")

    if user_in.password:
        user.hashed_password = utils.hash_password(user_in.password)
    query = so.update(models.User).where(models.User.id == user.id).values(**update_data).returning()
    result = await session.scalars(query)
    user = result.first()
    await session.commit()
    parser = await sheets_service.get_default_booster_read()
    creds = await get_first_superuser(session)
    if creds.google is not None:
        tasks_service.create_or_update_booster.delay(
            creds.google.model_dump_json(),
            parser.model_dump_json(),
            user.id,
            models.UserRead.model_validate(user).model_dump(),
        )
    return user


async def delete(session: AsyncSession, user: models.User) -> None:
    query = so.delete(models.User).where(models.User.id == user.id)
    await session.execute(query)
    await session.commit()
    parser = await sheets_service.get_default_booster_read()
    creds = await get_first_superuser(session)
    if creds.google is not None and parser is not None:
        tasks_service.delete_booster.delay(
            creds.google.model_dump_json(),
            parser.model_dump_json(),
            str(user.id),
        )


async def request_verify(user: models.User) -> None:
    if user.is_verified:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=enums.ErrorCode.VERIFY_USER_ALREADY_VERIFIED, code=enums.ErrorCode.VERIFY_USER_ALREADY_VERIFIED
                )
            ],
        )

    token_data = {
        "sub": user.id,
        "email": user.email,
        "aud": config.app.verification_token_audience,
    }
    token = utils.generate_jwt(token_data, config.app.secret)
    message_service.send_request_verify(models.UserRead.model_validate(user), token)


async def verify(session: AsyncSession, token: str) -> models.User:
    try:
        data = utils.decode_jwt(
            token,
            config.app.secret,
            [config.app.verification_token_audience],
        )
        _ = data["sub"]
        email = data["email"]
    except (jwt.PyJWTError, KeyError):
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=enums.ErrorCode.VERIFY_USER_BAD_TOKEN, code=enums.ErrorCode.VERIFY_USER_BAD_TOKEN
                )
            ],
        ) from None

    user = await get_by_email(session, email)
    if not user:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=enums.ErrorCode.VERIFY_USER_BAD_TOKEN, code=enums.ErrorCode.VERIFY_USER_BAD_TOKEN
                )
            ],
        )

    if user.is_verified:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=enums.ErrorCode.VERIFY_USER_ALREADY_VERIFIED, code=enums.ErrorCode.VERIFY_USER_ALREADY_VERIFIED
                )
            ],
        )

    verified_user = await update(session, user, models.UserUpdate(is_verified=True))
    message_service.send_verified_notify(models.UserRead.model_validate(user))
    return verified_user


async def authenticate(session: AsyncSession, credentials: OAuth2PasswordRequestForm) -> models.User | None:
    user = await get_by_email(session, credentials.username.lower())
    if user is None:
        utils.hash_password(credentials.password)
        return None

    verified, updated_password_hash = utils.verify_and_update_password(credentials.password, user.hashed_password)
    if not verified:
        return None
    if updated_password_hash is not None:
        query = so.update(models.User).where(models.User.id == user.id).values(hashed_password=updated_password_hash)
        await session.execute(query)
        await session.commit()
    return user


async def forgot_password(user: models.User) -> None:
    if not user.is_active:
        return None

    token_data = {
        "sub": user.id,
        "password_fingerprint": utils.hash_password(user.hashed_password),
        "aud": config.app.reset_password_token_audience,
    }
    token = utils.generate_jwt(token_data, config.app.secret, 900)
    logger.warning(token)
    return


async def reset_password(session: AsyncSession, token: str, password: str) -> models.User:
    try:
        data = utils.decode_jwt(
            token,
            config.app.secret,
            [config.app.reset_password_token_audience],
        )
        user_id = data["sub"]
        password_fingerprint = data["password_fingerprint"]
    except jwt.PyJWTError:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=enums.ErrorCode.RESET_PASSWORD_INVALID_PASSWORD,
                    code=enums.ErrorCode.RESET_PASSWORD_INVALID_PASSWORD,
                )
            ],
        ) from None
    logger.warning(f"Try reset password for user {user_id}")
    user = await get(session, user_id)
    if not user:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=enums.ErrorCode.RESET_PASSWORD_BAD_TOKEN, code=enums.ErrorCode.RESET_PASSWORD_BAD_TOKEN
                )
            ],
        )
    valid_password_fingerprint, _ = utils.verify_and_update_password(user.hashed_password, password_fingerprint)
    logger.warning(f"Try reset password for user, password validation = {valid_password_fingerprint}")
    if not valid_password_fingerprint:
        e = errors.DudeDuckException(
            msg=enums.ErrorCode.RESET_PASSWORD_INVALID_PASSWORD,
            code=enums.ErrorCode.RESET_PASSWORD_INVALID_PASSWORD,
        )
        raise errors.DudeDuckHTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=[e])

    if not user.is_active:
        e = errors.DudeDuckException(
            msg=enums.ErrorCode.RESET_PASSWORD_BAD_TOKEN, code=enums.ErrorCode.RESET_PASSWORD_BAD_TOKEN
        )
        raise errors.DudeDuckHTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=[e])

    updated_user = await update(session, user, models.UserUpdate(password=password))
    return updated_user


async def read_token(session: AsyncSession, token: str | None) -> models.User | None:
    if token is None:
        return None

    max_age = datetime.now(timezone.utc) - timedelta(seconds=24 * 3600)
    query = (
        so.select(models.AccessToken)
        .where(models.AccessToken.token == token, models.AccessToken.created_at < max_age)
        .join(models.User)
        .limit(1)
    )
    result = await session.scalars(query)
    access_token = result.first()
    if access_token is None:
        return None
    return access_token.user


async def write_token(session: AsyncSession, user: models.User) -> str:
    token = secrets.token_urlsafe()
    query = so.insert(models.AccessToken).values(token=token, user_id=user.id)
    await session.execute(query)
    await session.commit()
    return token


async def read_token_api(session: AsyncSession, token: str | None) -> models.User | None:
    if token is None:
        return None
    query = (
        so.select(models.AccessTokenAPI)
        .where(models.AccessTokenAPI.token == token)
        .join(models.User)
        .limit(1)
    )
    result = await session.scalars(query)
    access_token = result.first()
    if access_token is None:
        return None
    return access_token.user


async def write_token_api(session: AsyncSession, user: models.User) -> str:
    token = secrets.token_urlsafe()
    query = so.insert(models.AccessTokenAPI).values(token=token, user_id=user.id)
    await session.execute(query)
    await session.commit()
    return token
