import typing

import jwt
from beanie import PydanticObjectId
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, exceptions
from fastapi_users.jwt import decode_jwt, generate_jwt
from fastapi_users_db_beanie import BeanieUserDatabase, ObjectIDIDMixin
from loguru import logger
from starlette.responses import Response

from app.core import config
from app.services.sheets import service as sheets_service
from app.services.tasks import service as tasks_service
from app.services.telegram.message import service as message_service

from . import models, service


class UserManager(ObjectIDIDMixin, BaseUserManager[models.User, PydanticObjectId]):
    reset_password_token_secret = config.app.secret
    verification_token_secret = config.app.secret

    async def create(
        self, user_create: models.UserCreate, safe: bool = False, request: Request | None = None
    ) -> models.User:
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()
        existing_user = await models.User.find_one(models.User.name == user_create.name)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()

        user_dict = user_create.create_update_dict() if safe else user_create.create_update_dict_superuser()
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)

        parser = await sheets_service.get_default_booster()
        created_user = await self.user_db.create(user_dict)
        creds = await service.get_first_superuser()
        tasks_service.create_booster.delay(
            creds.google.model_dump_json(),
            parser.model_dump_json(),
            models.UserRead.model_validate(created_user).model_dump(),
        )
        await self.on_after_register(created_user, request)
        return created_user

    async def request_verify(self, user: models.User, request: Request | None = None) -> None:
        if not user.is_active:
            raise exceptions.UserInactive()
        if user.is_verified:
            raise exceptions.UserAlreadyVerified()

        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "aud": self.verification_token_audience,
            "telegram_username": user.telegram,
        }
        token = generate_jwt(
            token_data,
            self.verification_token_secret,
            self.verification_token_lifetime_seconds,
        )
        await self.on_after_request_verify(user, token, request)

    async def verify(self, token: str, request: Request | None = None) -> models.User:
        try:
            data = decode_jwt(
                token,
                self.verification_token_secret,
                [self.verification_token_audience],
            )
        except jwt.PyJWTError:
            raise exceptions.InvalidVerifyToken()

        try:
            user_id = data["sub"]
            email = data["email"]
        except KeyError:
            raise exceptions.InvalidVerifyToken()
        try:
            user = await self.get_by_email(email)
        except exceptions.UserNotExists:
            raise exceptions.InvalidVerifyToken()
        try:
            parsed_id = self.parse_id(user_id)
        except exceptions.InvalidID:
            raise exceptions.InvalidVerifyToken()
        if parsed_id != user.id:
            raise exceptions.InvalidVerifyToken()
        if user.is_verified:
            raise exceptions.UserAlreadyVerified()

        parser = await sheets_service.get_default_booster()
        user = await service.update(user, models.UserUpdate(is_verified=True))
        creds = await service.get_first_superuser()
        tasks_service.create_or_update_booster.delay(
            creds.google.model_dump_json(),
            parser.model_dump_json(),
            user.email,
            models.UserRead.model_validate(user).model_dump(),
        )
        await self.on_after_verify(user, request)
        return user

    async def on_after_request_verify(self, user: models.User, token: str, request: Request | None = None):
        user = models.UserRead.model_validate(user)
        message_service.send_request_verify(user, token)

    async def on_after_verify(self, user: models.User, request: Request | None = None) -> None:
        user = models.UserRead.model_validate(user)
        message_service.send_verified_notify(user)

    async def on_after_login(self, user: models.User, request: Request | None = None, response: Response | None = None):
        user = models.UserRead.model_validate(user)
        message_service.send_logged_notify(user)

    async def on_after_register(self, user: models.User, request: Request | None = None):
        logger.info(f"User {user.id} has registered.")
        user = models.UserRead.model_validate(user)
        message_service.send_registered_notify(user)

    async def on_after_forgot_password(self, user: models.User, token: str, request: Request | None = None) -> None:
        logger.warning(token)

    async def on_after_update(
        self,
        user: models.User,
        update_dict: str | typing.Any,
        request: Request | None = None,
    ) -> None:
        parser = await sheets_service.get_default_booster()
        creds = await service.get_first_superuser()
        tasks_service.create_or_update_booster.delay(
            creds.google.model_dump_json(),
            parser.model_dump_json(),
            str(user.id),
            models.UserRead.model_validate(user).model_dump(),
        )

    async def on_after_delete(
        self,
        user: models.User,
        request: Request | None = None,
    ) -> None:
        parser = await sheets_service.get_default_booster()
        creds = await service.get_first_superuser()
        tasks_service.delete_booster.delay(
            creds.google.model_dump_json(),
            parser.model_dump_json(),
            str(user.id),
        )


async def get_user_db():
    yield BeanieUserDatabase(models.User)


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
