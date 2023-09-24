import secrets
import typing
from datetime import datetime, timedelta, timezone

import jwt
from beanie import PydanticObjectId
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from starlette import status

from app.core import config, enums, errors
from app.services.sheets import service as sheets_service
from app.services.tasks import service as tasks_service
from app.services.telegram.message import service as message_service

from . import models, utils


async def get(user_id: PydanticObjectId) -> models.User | None:
    user = await models.User.find_one({"_id": user_id})
    return user


async def get_by_email(user_email: str) -> models.User | None:
    user = await models.User.find_one({"email": user_email})
    return user


async def get_by_name(username: str) -> models.User | None:
    user = await models.User.find_one({"name": username})
    return user


async def get_all() -> list[models.User]:
    return await models.User.find({}).to_list()


async def get_first_superuser() -> models.User:
    return await get_by_email(config.app.super_user_email)


async def get_superusers_with_google() -> list[models.User]:
    return await models.User.find({"is_superuser": True, "google": {"$ne": None}}).to_list()


async def get_by_ids(users_id: typing.Iterable[PydanticObjectId]) -> list[models.User]:
    return await models.User.find({"_id": {"$in": users_id}}).to_list()


async def create(user_create: models.UserCreate, safe: bool = False) -> models.User:
    existing_user = await get_by_email(user_create.email)
    if existing_user is not None:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=enums.ErrorCode.REGISTER_USER_ALREADY_EXISTS, code=enums.ErrorCode.REGISTER_USER_ALREADY_EXISTS
                )
            ],
        )

    user_dict = (
        user_create.model_dump(
            exclude={"id", "is_superuser", "is_active", "is_verified", "oauth_accounts"}, exclude_unset=True
        )
        if safe
        else user_create.model_dump(exclude={"id"}, exclude_unset=True)
    )
    password = user_dict.pop("password")
    user_dict["hashed_password"] = utils.hash_password(password)
    created_user = await models.User(**user_dict).create()
    parser = await sheets_service.get_default_booster_read()
    creds = await get_first_superuser()
    if creds.google is not None:
        tasks_service.create_booster.delay(
            creds.google.model_dump_json(),
            parser.model_dump_json(),
            models.UserRead.model_validate(created_user).model_dump(),
        )
    return created_user


async def update(user: models.User, user_in: models.BaseUserUpdate, safe: bool = False) -> models.User:
    update_data = (
        user_in.model_dump(
            exclude={"is_superuser", "is_active", "is_verified", "oauth_accounts", "password"},
            exclude_unset=True,
            mode="json",
        )
        if safe
        else user_in.model_dump(exclude={"password"}, mode="json", exclude_unset=True)
    )

    user_data = dict(user)
    for field in user_data:
        if field in update_data:
            setattr(user, field, update_data[field])

    if user_in.password:
        user.hashed_password = utils.hash_password(user_in.password)
    await user.save_changes()
    parser = await sheets_service.get_default_booster_read()
    creds = await get_first_superuser()
    if creds.google is not None:
        tasks_service.create_or_update_booster.delay(
            creds.google.model_dump_json(),
            parser.model_dump_json(),
            str(user.id),
            models.UserRead.model_validate(user).model_dump(),
        )
    return user


async def delete(user: models.User) -> None:
    await user.delete()
    parser = await sheets_service.get_default_booster_read()
    creds = await get_first_superuser()
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
        "sub": str(user.id),
        "email": user.email,
        "aud": config.app.verification_token_audience,
    }
    token = utils.generate_jwt(token_data, config.app.secret)
    message_service.send_request_verify(models.UserRead.model_validate(user), token)


async def verify(token: str) -> models.User:
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

    user = await get_by_email(email)
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

    verified_user = await update(user, models.UserUpdate(is_verified=True))
    message_service.send_verified_notify(models.UserRead.model_validate(user))
    return verified_user


async def authenticate(credentials: OAuth2PasswordRequestForm) -> models.User | None:
    user = await get_by_email(credentials.username)
    if user is None:
        utils.hash_password(credentials.password)
        return None

    verified, updated_password_hash = utils.verify_and_update_password(credentials.password, user.hashed_password)
    if not verified:
        return None
    if updated_password_hash is not None:
        user.hashed_password = updated_password_hash
        await user.save(update_fields=("hashed_password",))
    return user


async def forgot_password(user: models.User) -> None:
    if not user.is_active:
        return None

    token_data = {
        "sub": str(user.id),
        "password_fingerprint": utils.hash_password(user.hashed_password),
        "aud": config.app.reset_password_token_audience,
    }
    token = utils.generate_jwt(token_data, config.app.secret, 900)
    logger.warning(token)


async def reset_password(token: str, password: str) -> models.User:
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

    user = await get(user_id)
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
    if not valid_password_fingerprint:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=enums.ErrorCode.RESET_PASSWORD_INVALID_PASSWORD,
                    code=enums.ErrorCode.RESET_PASSWORD_INVALID_PASSWORD,
                )
            ],
        )

    if not user.is_active:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.DudeDuckException(
                    msg=enums.ErrorCode.RESET_PASSWORD_BAD_TOKEN, code=enums.ErrorCode.RESET_PASSWORD_BAD_TOKEN
                )
            ],
        )

    updated_user = await update(user, models.UserUpdate(password=password))
    return updated_user


async def read_token(token: str | None) -> models.User | None:
    if token is None:
        return None

    max_age = datetime.now(timezone.utc) - timedelta(seconds=24 * 3600)
    access_token = await models.AccessToken.find_one({"token": token, "created_at": {"$gte": max_age}})
    if access_token is None:
        return None
    return await get(access_token.user_id.ref.id)


async def write_token(user: models.User) -> str:
    access_token = models.AccessToken(user_id=user, token=secrets.token_urlsafe())
    access_token = await access_token.create()
    return access_token.token


async def destroy_token(token: str) -> None:
    max_age = datetime.now(timezone.utc) - timedelta(seconds=24 * 3600)
    access_token = await models.AccessToken.find_one({"token": token, "created_at": max_age})
    if access_token is not None:
        await access_token.delete()


async def read_token_api(token: str | None) -> models.User | None:
    if token is None:
        return None

    access_token = await models.AccessTokenAPI.find_one({"token": token})
    if access_token is None:
        return None
    return await get(access_token.user_id.ref.id)


async def write_token_api(user: models.User) -> str:
    access_token = await models.AccessTokenAPI.find_one({"user_id": user.id})
    if access_token:
        await access_token.delete()
    access_token = models.AccessTokenAPI(user_id=user.id, token=secrets.token_urlsafe())
    access_token = await access_token.create()
    return access_token.token


async def destroy_token_api(token: str) -> None:
    access_token = await models.AccessToken.find_one({"token": token})
    if access_token is not None:
        await access_token.delete()
