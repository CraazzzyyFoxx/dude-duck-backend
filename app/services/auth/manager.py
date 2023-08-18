import asyncio

from typing import Optional

import jwt
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.jwt import generate_jwt, decode_jwt
from loguru import logger
from beanie import PydanticObjectId
from fastapi import Depends, Request, BackgroundTasks
from fastapi_users import BaseUserManager, exceptions
from fastapi_users_db_beanie import ObjectIDIDMixin, BeanieUserDatabase
from starlette.responses import Response

from app.core import config
from app.services.sheets.flows import GoogleSheetsServiceManager
from app.services.messages.service import MessageService


from . import models


def get_tasks(background_tasks: BackgroundTasks):
    yield background_tasks


class UserManager(ObjectIDIDMixin, BaseUserManager[models.User, PydanticObjectId]):
    reset_password_token_secret = config.app.secret
    verification_token_secret = config.app.secret

    async def create(
            self,
            user_create: models.UserCreate,
            safe: bool = False,
            request: Optional[Request] = None,
    ) -> models.User:
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()
        existing_user = await models.User.find_one(models.User.name == user_create.name)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()

        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)

        parser = await models.OrderSheetParse.get_default_booster()
        created_user = await self.user_db.create(user_dict)
        asyncio.create_task(
            GoogleSheetsServiceManager.get().create_row_data(
                models.UserRead, parser.spreadsheet, parser.sheet_id, created_user)
        )
        await self.on_after_register(created_user, request)
        return created_user

    async def request_verify(
            self, user: models.User, request: Optional[Request] = None
    ) -> None:
        if not user.is_active:
            raise exceptions.UserInactive()
        if user.is_verified:
            raise exceptions.UserAlreadyVerified()

        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "aud": self.verification_token_audience,
            "telegram_username": user.telegram
        }
        token = generate_jwt(
            token_data,
            self.verification_token_secret,
            self.verification_token_lifetime_seconds,
        )
        await self.on_after_request_verify(user, token, request)
        await MessageService.send_request_verify(user, token)

    async def verify(self, token: str, request: Optional[Request] = None) -> models.User:
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

        parser = await models.OrderSheetParse.get_default_booster()
        booster = await GoogleSheetsServiceManager.get().find_by(
            models.UserReadSheets, parser.spreadsheet, parser.sheet_id, user.id
        )
        if not booster:
            asyncio.create_task(GoogleSheetsServiceManager.get().create_row_data(models.UserRead,
                                                                                 parser.spreadsheet, parser.sheet_id,
                                                                                 user))
        user.update_from(booster)
        user.id = parsed_id
        user.is_verified = True
        await user.save()

        await self.on_after_verify(user, request)
        return user

    async def on_after_request_verify(
            self, user: models.User, token: str, request: Optional[Request] = None
    ):
        logger.info(f"Verification requested for user {user.id}. Verification token: {token}")

    async def on_after_verify(
            self, user: models.User, request: Optional[Request] = None
    ) -> None:
        pass

    async def on_after_login(
            self, user: models.User, request: Optional[Request] = None, response: Optional[Response] = None,
    ) -> None:
        pass

    async def authenticate(self, credentials: OAuth2PasswordRequestForm) -> Optional[models.User]:
        user: models.User = await super().authenticate(credentials)
        return user

    async def on_after_register(self, user: models.User, request: Optional[Request] = None):
        logger.info(f"User {user.id} has registered.")

    async def on_after_forgot_password(
            self, user: models.User, token: str, request: Optional[Request] = None
    ):
        logger.info(f"User {user.id} has forgot their password. Reset token: {token}")


async def get_user_db():
    yield BeanieUserDatabase(models.User)


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
