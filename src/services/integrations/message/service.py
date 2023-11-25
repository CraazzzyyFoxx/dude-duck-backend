import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import enums
from src.services.integrations.bots import service as bots_service

from . import models


async def get(session: AsyncSession, integration: enums.Integration, message_id: int) -> models.Message | None:
    query = sa.select(models.Message).where(models.Message.id == message_id, models.Message.integration == integration)
    result = await session.execute(query)
    return result.scalars().first()


async def get_by_type(
    session: AsyncSession, integration: enums.Integration, message_id: int, message_type: models.MessageType
) -> list[models.Message]:
    query = (
        sa.select(models.Message)
        .where(models.Message.id == message_id, models.Message.type == message_type)
        .where(models.Message.integration == integration)
    )
    result = await session.execute(query)
    return result.scalars().all()  # type: ignore


async def get_by_order_id(
    session: AsyncSession, integration: enums.Integration, order_id: int, preorder: bool
) -> list[models.Message]:
    message_type = models.MessageType.PRE_ORDER if preorder else models.MessageType.ORDER
    query = (
        sa.select(models.Message)
        .where(models.Message.order_id == order_id, models.Message.type == message_type)
        .where(models.Message.integration == integration)
    )
    result = await session.execute(query)
    return result.scalars().all()  # type: ignore


async def get_by_order_id_user_id(
    session: AsyncSession, integration: enums.Integration, order_id: int, user_id: int
) -> models.Message | None:
    query = (
        sa.select(models.Message)
        .where(models.Message.user_id == user_id, models.Message.order_id == order_id)
        .where(models.Message.integration == integration)
    )
    result = await session.execute(query)
    return result.scalars().first()


async def get_by_order_id_type(
    session: AsyncSession, integration: enums.Integration, order_id: int, message_type: models.MessageType
) -> list[models.Message]:
    query = (
        sa.select(models.Message)
        .where(models.Message.order_id == order_id, models.Message.type == message_type)
        .where(models.Message.integration == integration)
    )
    result = await session.execute(query)
    return result.scalars().all()  # type: ignore


async def _create_message(
    session: AsyncSession, message_in: models.MessageCreate
) -> tuple[models.Message | None, models.MessageStatus]:
    data = await bots_service.create_message(session, message_in.integration, [message_in])
    return data[0]
    # return None, models.MessageStatus.INTEGRATION_NOT_FOUND


async def create_message_order(
    session: AsyncSession, message_in: models.MessageCreate
) -> tuple[models.Message | None, models.MessageStatus]:
    messages = await get_by_order_id_type(session, message_in.integration, message_in.order_id, message_in.type)
    channels_id = [msg.channel_id for msg in messages]
    if message_in.channel_id not in channels_id:
        return await _create_message(session, message_in)
    return None, models.MessageStatus.EXISTS


async def create_message_response(
    session: AsyncSession, message_in: models.MessageCreate
) -> tuple[models.Message | None, models.MessageStatus]:
    message = await get_by_order_id_user_id(session, message_in.integration, message_in.order_id, message_in.user_id)
    if message is None:
        return await _create_message(session, message_in)
    return None, models.MessageStatus.EXISTS


async def create(
    session: AsyncSession, message_in: models.MessageCreate
) -> tuple[models.Message | None, models.MessageStatus]:
    if message_in.type == models.MessageType.ORDER:
        return await create_message_order(session, message_in)
    elif message_in.type == models.MessageType.PRE_ORDER:
        return await create_message_order(session, message_in)
    elif message_in.type == models.MessageType.RESPONSE:
        return await create_message_response(session, message_in)

    return await _create_message(session, message_in)


async def update(
    session: AsyncSession, message: models.Message, message_in: models.MessageUpdate
) -> tuple[models.Message | None, models.MessageStatus]:
    data = await bots_service.update_message(session, message_in.integration, [(message, message_in)])
    return data[0]
    # return None, models.MessageStatus.INTEGRATION_NOT_FOUND


async def delete(session: AsyncSession, message: models.Message) -> tuple[models.Message | None, models.MessageStatus]:
    data = await bots_service.delete_message(session, message.integration, [message])
    return data[0]
    # return None, models.MessageStatus.INTEGRATION_NOT_FOUND
