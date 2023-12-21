import asyncio

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src import models
from src.core import db, enums, errors
from src.services.integrations.discord import service as discord_service
from src.services.integrations.telegram import service as telegram_service

from . import utils


async def get_notification_config(session: AsyncSession, notification_id: int) -> models.UserNotification:
    query = sa.select(models.UserNotification).where(models.UserNotification.id == notification_id)
    result = await session.execute(query)
    return result.scalars().first()


async def create_notification_config(
    session: AsyncSession,
    user: models.User,
    notification: models.UserNotificationCreate,
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


async def delete_notification_config(
    session: AsyncSession, user: models.User, notification_id: int
) -> models.UserNotification:
    notification = await get_notification_config(session, notification_id)
    query = sa.delete(models.UserNotification).where(
        sa.and_(
            models.UserNotification.user_id == user.id,
            models.UserNotification.id == notification_id,
        )
    )
    await session.execute(query)
    await session.commit()
    return notification


async def update_notification_config(
    session: AsyncSession,
    user: models.User,
    notification_id: int,
    notification: models.UserNotificationUpdate,
) -> models.UserNotification:
    query = (
        sa.update(models.UserNotification)
        .where(
            sa.and_(
                models.UserNotification.user_id == user.id,
                models.UserNotification.id == notification_id,
            )
        )
        .values(**notification.model_dump())
    )
    result = await session.execute(query)
    await session.commit()
    return result.scalars().first()


async def get_notification_configs_by_user_id(session: AsyncSession, user_id: int) -> list[models.UserNotification]:
    query = sa.select(models.UserNotification).where(models.UserNotification.user_id == user_id)
    result = await session.execute(query)
    return result.scalars().all()  # type: ignore


def send_user_notification(payload: models.NotificationSendUser):
    asyncio.create_task(_send_user(payload))


def send_system_notification(payload: models.NotificationSendSystem):
    asyncio.create_task(_send_system(payload))


async def get_user_accounts(session: AsyncSession, user: models.UserRead) -> models.UserReadWithAccounts:
    telegram_account = await telegram_service.get_tg_account(session, user.id)
    return models.UserReadWithAccounts(
        telegram=models.TelegramAccountRead.model_validate(telegram_account, from_attributes=True),
        **user.model_dump(),
    )


async def _send_user(payload: models.NotificationSendUser):
    async with db.async_session_maker() as session:
        entities = await get_notification_configs_by_user_id(session, payload.user.id)
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


async def _send_system(payload: models.NotificationSendSystem):
    async with db.async_session_maker() as session:
        url = utils.path_resolver[payload.type]
        await telegram_service.request(url, "POST", data=payload.data)
