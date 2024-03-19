import asyncio

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src import models, schemas
from src.core import db, enums, errors
from src.services.integrations.discord import service as discord_service
from src.services.integrations.telegram import service as telegram_service

from . import utils


async def get_user_notification(
    session: AsyncSession, user_id: int, notification_type: enums.Integration
) -> models.UserNotification | None:
    query = sa.select(models.UserNotification).where(
        models.UserNotification.user_id == user_id, models.UserNotification.type == notification_type
    )
    result = await session.execute(query)
    return result.scalars().first()


async def create_user_notification(
    session: AsyncSession,
    user: models.User,
    notification: schemas.UserNotificationCreate,
) -> models.UserNotification:
    query = sa.insert(models.UserNotification).values(user_id=user.id, **notification.model_dump())
    try:
        result = await session.execute(query)
        await session.commit()
    except IntegrityError as e:
        raise errors.ApiHTTPException(
            status_code=400,
            detail=[errors.ApiException(code="already_exists", msg="Notification already exists")],
        ) from e
    return result.scalars().first()


async def delete_user_notification(
    session: AsyncSession, user: models.User, notification_type: enums.Integration
) -> models.UserNotification:
    notification = await get_user_notification(session, user.id, notification_type)
    if notification is None:
        raise errors.ApiHTTPException(
            status_code=400,
            detail=[errors.ApiException(code="not_found", msg="Notification not found")],
        )
    await session.delete(notification)
    await session.commit()
    return notification


async def get_user_notification_by_user_id(session: AsyncSession, user_id: int) -> list[models.UserNotification]:
    query = sa.select(models.UserNotification).where(models.UserNotification.user_id == user_id)
    result = await session.execute(query)
    return result.scalars().all()  # type: ignore


def send_user_notification(payload: schemas.NotificationSendUser):
    asyncio.create_task(_send_user(payload))


def send_system_notification(payload: schemas.NotificationSendSystem):
    asyncio.create_task(_send_system(payload))


async def get_user_accounts(session: AsyncSession, user: schemas.UserRead) -> schemas.UserReadWithAccounts:
    telegram_account = await telegram_service.get_tg_account(session, user.id)
    return schemas.UserReadWithAccounts(
        telegram=schemas.TelegramAccountRead.model_validate(telegram_account, from_attributes=True),
        **user.model_dump(),
    )


async def _send_user(payload: schemas.NotificationSendUser):
    async with db.async_session_maker() as session:
        entities = await get_user_notification_by_user_id(session, payload.user.id)
        url = utils.path_resolver[payload.type]
        data = payload.data
        if data is None:
            data = {"user": payload.user}
        else:
            data["user"] = payload.user
        for source in entities:
            if source.type == enums.Integration.telegram:
                await telegram_service.request(url, "POST", data=data)
            elif source.type == enums.Integration.discord:
                await discord_service.request(url, "POST", data=data)
            else:
                raise NotImplementedError(f"Notification type {source.type} not implemented")


async def _send_system(payload: schemas.NotificationSendSystem):
    url = utils.path_resolver[payload.type]
    await telegram_service.request(url, "POST", data=payload.data)
