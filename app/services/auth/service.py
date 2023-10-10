import secrets
import typing
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from starlette import status
from tortoise.expressions import Q

from app.core import config, enums, errors
from app.services.sheets import service as sheets_service
from app.services.tasks import service as tasks_service
from app.services.telegram.message import service as message_service

from . import models, utils


async def get(user_id: int) -> models.User | None:
    user = await models.User.filter(id=user_id).first()
    return user


async def get_by_email(user_email: str) -> models.User | None:
    user = await models.User.filter(email=user_email).first()
    return user


async def get_by_name(username: str) -> models.User | None:
    user = await models.User.filter(name=username).first()
    return user


async def get_all() -> list[models.User]:
    return await models.User.filter().all()


async def get_first_superuser() -> models.User:
    return await get_by_email(config.app.super_user_email)  # type: ignore


async def get_superusers_with_google() -> list[models.User]:
    return await models.User.filter(Q(is_superuser=True) and ~Q(name=None))


async def get_by_ids(users_id: typing.Iterable[int]) -> list[models.User]:
    return await models.User.filter(id__in=users_id)


async def create(user_create: models.UserCreate, safe: bool = False) -> models.User:
    if await get_by_email(user_create.email) is not None or await get_by_name(user_create.name):
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
    email: str = user_dict.pop("email")
    password = user_dict.pop("password")
    user_dict["hashed_password"] = utils.hash_password(password)
    user_dict["email"] = email.lower()
    created_user = await models.User.create(**user_dict)
    parser = await sheets_service.get_default_booster_read()
    creds = await get_first_superuser()
    if creds.google is not None:
        tasks_service.create_booster.delay(
            creds.google.model_dump_json(),
            parser.model_dump_json(),
            models.UserRead.model_validate(created_user).model_dump(),
        )
    return created_user


async def update(user: models.User, user_in: models.BaseUserUpdate, safe: bool = False, exclude=True) -> models.User:
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
    user = user.update_from_dict(update_data)
    await user.save()
    parser = await sheets_service.get_default_booster_read()
    creds = await get_first_superuser()
    if creds.google is not None:
        tasks_service.create_or_update_booster.delay(
            creds.google.model_dump_json(),
            parser.model_dump_json(),
            user.id,
            models.UserRead.model_validate(user).model_dump(),
        )
    return user


async def delete(user: models.User) -> None:
    await user.delete()
    parser = await sheets_service.get_default_booster_read()
    creds = await get_first_superuser()
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
    user = await get_by_email(credentials.username.lower())
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
        "sub": user.id,
        "password_fingerprint": utils.hash_password(user.hashed_password),
        "aud": config.app.reset_password_token_audience,
    }
    token = utils.generate_jwt(token_data, config.app.secret, 900)
    logger.warning(token)
    return


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
    logger.warning(f"Try reset password for user {user_id}")
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
    logger.warning(f"Try reset password for user, password validation = {valid_password_fingerprint}")
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
    access_token = await (
        models.AccessToken.filter(token=token, created_at__gte=max_age).prefetch_related("user").first()
    )
    if access_token is None:
        return None
    return access_token.user


async def write_token(user: models.User) -> str:
    access_token = await models.AccessToken.create(user_id=user.id, token=secrets.token_urlsafe())
    return access_token.token


async def destroy_token(token: str) -> None:
    max_age = datetime.now(timezone.utc) - timedelta(seconds=24 * 3600)
    access_token = await models.AccessToken.filter(token=token, created_at__gte=max_age).first()
    if access_token is not None:
        await access_token.delete()


async def read_token_api(token: str | None) -> models.User | None:
    if token is None:
        return None
    access_token = await models.AccessTokenAPI.filter(token=token).prefetch_related("user").first()
    if access_token is None:
        return None
    return access_token.user


async def write_token_api(user: models.User) -> str:
    access_token = await models.AccessTokenAPI.filter(user_id=user.id).first()
    if access_token:
        await access_token.delete()
    access_token = await models.AccessTokenAPI.create(user_id=user.id, token=secrets.token_urlsafe())
    return access_token.token


async def destroy_token_api(token: str) -> None:
    access_token = await models.AccessTokenAPI.filter(token=token).first()
    if access_token is not None:
        await access_token.delete()
