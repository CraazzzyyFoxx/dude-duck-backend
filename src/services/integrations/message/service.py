from datetime import datetime

import httpx
import pytz
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src import models, schemas
from src.core import enums, pagination
from src.services.integrations.channel import service as channel_service
from src.services.integrations.discord import service as discord_service
from src.services.integrations.render import flows as render_flows
from src.services.integrations.telegram import service as telegram_service
from src.services.response import flows as response_flows


async def get_user_message_by_message_id(session: AsyncSession, message_id: int) -> models.UserMessage:
    query = sa.select(models.UserMessage).where(models.UserMessage.message_id == message_id)
    result = await session.execute(query)
    return result.scalars().first()  # type: ignore


async def get_messages_by_order_id(
    session: AsyncSession,
    integration: enums.Integration,
    order_id: int,
    is_preorder: bool = False,
) -> list[models.OrderMessage]:
    query = sa.select(models.OrderMessage).where(
        models.OrderMessage.order_id == order_id,
        models.OrderMessage.integration == integration,
        models.OrderMessage.is_preorder == is_preorder,
    )
    result = await session.execute(query)
    return result.scalars().all()  # type: ignore


async def get_message_by_order_id_user_id(
    session: AsyncSession, integration: enums.Integration, order_id: int, user_id: int
) -> models.ResponseMessage | None:
    query = (
        sa.select(models.ResponseMessage)
        .where(models.ResponseMessage.user_id == user_id, models.ResponseMessage.order_id == order_id)
        .where(models.Message.integration == integration)
    )
    result = await session.execute(query)
    return result.scalars().first()


async def request(integration: enums.Integration, path: str, method: str, data: dict | None = None) -> httpx.Response:
    if integration == enums.Integration.discord:
        return await discord_service.request(path, method, data)
    elif integration == enums.Integration.telegram:
        return await telegram_service.request(path, method, data)
    else:
        raise ValueError("Invalid integration")


async def create_order_message(
    session: AsyncSession,
    order: schemas.OrderReadSystem | models.PreOrderReadSystem,
    data: models.CreateOrderMessage,
) -> models.MessageCallback:
    messages = await get_messages_by_order_id(session, data.integration, data.order_id, data.is_preorder)
    chs = await channel_service.get_by_game_categories(session, data.integration, order.info.game, data.categories)
    if not chs:
        return models.MessageCallback(error=True, error_msg="A channels with this game do not exist")
    status, text = await render_flows.generate_body(
        session, data.integration, order, data.configs, data.is_preorder, data.is_gold
    )
    if not status:
        return models.MessageCallback(error=True, error_msg=text)
    created, skipped = [], []
    existing_channels = [msg.channel_id for msg in messages]
    for channel_id in [ch.channel_id for ch in chs]:
        if channel_id in existing_channels:
            skipped.append(models.SkippedCallback(channel_id=channel_id, status=models.CallbackStatus.EXISTS))
            continue
        payload = {
            "channel_id": channel_id,
            "order_id": data.order_id,
            "text": text,
            "is_preorder": data.is_preorder,
        }
        response = await request(data.integration, "message/order", "POST", data=payload)
        response_data = models.MessageCallback.model_validate(response.json())
        for created_msg in response_data.created:
            message_db = models.OrderMessage(
                order_id=data.order_id,
                channel_id=created_msg.channel_id,
                message_id=created_msg.message_id,
                integration=data.integration,
                is_preorder=data.is_preorder,
            )
            session.add(message_db)
            created.append(created_msg)
        for skipped_msg in response_data.skipped:
            skipped.append(skipped_msg)
    await session.commit()
    return models.MessageCallback(created=created, skipped=skipped)


async def update_order_message(
    session: AsyncSession,
    order: schemas.OrderReadSystem | models.PreOrderReadSystem,
    data: models.UpdateOrderMessage,
) -> models.MessageCallback:
    messages = await get_messages_by_order_id(session, data.integration, data.order_id, data.is_preorder)
    updated, skipped = [], []
    for message in messages:
        status, text = await render_flows.generate_body(
            session, data.integration, order, data.configs, data.is_preorder, data.is_gold
        )
        if not status:
            return models.MessageCallback(error=True, error_msg=text)
        payload = {
            "message": models.OrderMessageRead.model_validate(message, from_attributes=True),
            "text": text,
        }
        response = await request(message.integration, "message/order", "PATCH", data=payload)
        response_data = models.MessageCallback.model_validate(response.json())
        if response_data.updated:
            message.updated_at = datetime.now(pytz.utc)
            session.add(message)
        for updated_msg in response_data.updated:
            updated.append(updated_msg)
        for skipped_msg in response_data.skipped:
            skipped.append(skipped_msg)
    await session.commit()
    return models.MessageCallback(updated=updated, skipped=skipped)


async def delete_order_message(
    session: AsyncSession,
    data: models.DeleteOrderMessage,
) -> models.MessageCallback:
    messages = await get_messages_by_order_id(session, data.integration, data.order_id, data.is_preorder)
    deleted, skipped = [], []
    for message in messages:
        payload = {
            "message": models.OrderMessageRead.model_validate(message, from_attributes=True),
        }
        response = await request(message.integration, "message/order", "DELETE", data=payload)
        response_data = models.MessageCallback.model_validate(response.json())
        for deleted_msg in response_data.deleted:
            await channel_service.delete(session, message.channel_id)
            await session.delete(message)
            deleted.append(deleted_msg)
        for skipped_msg in response_data.skipped:
            skipped.append(skipped_msg)
            await session.delete(message)
    await session.commit()
    return models.MessageCallback(deleted=deleted, skipped=skipped)


async def create_response_message(
    session: AsyncSession,
    order: schemas.OrderReadSystem | models.PreOrderReadSystem,
    user: models.UserRead,
    data: models.CreateResponseMessage,
) -> models.MessageCallback:
    message = await get_message_by_order_id_user_id(session, data.integration, data.order_id, data.user_id)
    response = await response_flows.get_by_order_id_user_id(session, order.id, user.id)
    configs = render_flows.get_order_configs(
        order,
        is_preorder=data.is_preorder,
        is_gold=data.is_gold,
        with_response=True,
        response_checked=False,
    )
    text = await render_flows.get_order_text(
        session,
        data.integration,
        configs,
        data={
            "order": order,
            "response": response,
            "user": user,
        },
    )
    if message:
        return models.MessageCallback(error=True, error_msg="Response message already exists")
    payload = {
        "user": user,
        "text": text,
        "is_preorder": data.is_preorder,
    }
    if data.is_preorder:
        payload["preorder"] = order
    else:
        payload["order"] = order
    response = await request(data.integration, "message/response_admins", "POST", data=payload)
    response_data = models.MessageCallback.model_validate(response.json())
    for created_msg in response_data.created:
        message_db = models.ResponseMessage(
            order_id=data.order_id,
            user_id=data.user_id,
            channel_id=created_msg.channel_id,
            message_id=created_msg.message_id,
            integration=data.integration,
            is_preorder=data.is_preorder,
        )
        session.add(message_db)
    await session.commit()
    return response_data


async def create_user_message(session: AsyncSession, data: models.CreateUserMessage):
    payload = {
        "user_id": data.user_id,
        "text": data.text,
    }
    response = await request(data.integration, "message/user", "POST", data=payload)
    response_data = models.MessageCallback.model_validate(response.json())
    created, skipped = [], []
    for created_msg in response_data.created:
        message_db = models.UserMessage(
            user_id=data.user_id,
            channel_id=created_msg.channel_id,
            message_id=created_msg.message_id,
            integration=data.integration,
        )
        session.add(message_db)
        created.append(created_msg)
    for skipped_msg in response_data.skipped:
        skipped.append(skipped_msg)
    await session.commit()
    return models.MessageCallback(created=created, skipped=skipped)


async def update_user_message(session: AsyncSession, data: models.UpdateUserMessage):
    message = await get_user_message_by_message_id(session, data.message_id)
    payload = {
        "message": models.UserMessageRead.model_validate(message, from_attributes=True),
        "text": data.text,
    }
    response = await request(data.integration, "message/user", "PATCH", data=payload)
    response_data = models.MessageCallback.model_validate(response.json())
    updated, skipped = [], []
    for updated_msg in response_data.updated:
        message.updated_at = datetime.now(pytz.utc)
        session.add(message)
        updated.append(updated_msg)
    for skipped_msg in response_data.skipped:
        skipped.append(skipped_msg)
    await session.commit()
    return models.MessageCallback(updated=updated, skipped=skipped)


async def delete_user_message(session: AsyncSession, data: models.DeleteUserMessage):
    message = await get_user_message_by_message_id(session, data.message_id)
    payload = {
        "message": models.UserMessageRead.model_validate(message, from_attributes=True),
    }
    response = await request(data.integration, "message/user", "DELETE", data=payload)
    response_data = models.MessageCallback.model_validate(response.json())
    deleted, skipped = [], []
    for deleted_msg in response_data.deleted:
        deleted.append(deleted_msg)
    for skipped_msg in response_data.skipped:
        skipped.append(skipped_msg)
    message.is_deleted = True
    session.add(message)
    await session.commit()
    return models.MessageCallback(deleted=deleted, skipped=skipped)


async def get_order_messages_by_filter(
    session: AsyncSession, params: models.OrderMessagePaginationParams
) -> pagination.Paginated[models.OrderMessageRead]:
    query = sa.select(models.OrderMessage)
    query = params.apply_filter(query)
    query = params.apply_pagination(query)
    result = await session.execute(query)
    results = [models.OrderMessageRead.model_validate(row, from_attributes=True) for row in result.scalars()]
    total = await session.scalars(params.apply_filter(sa.select(sa.func.count(models.Message.id))))
    return pagination.Paginated(results=results, total=total.one(), page=params.page, per_page=params.per_page)


async def get_user_messages_by_filter(
    session: AsyncSession, params: models.UserMessagePaginationParams
) -> pagination.Paginated[models.UserMessageRead]:
    query = sa.select(models.OrderMessage)
    query = params.apply_filter(query)
    query = params.apply_pagination(query)
    result = await session.execute(query)
    results = [models.UserMessageRead.model_validate(row, from_attributes=True) for row in result.scalars()]
    total = await session.scalars(params.apply_filter(sa.select(sa.func.count(models.Message.id))))
    return pagination.Paginated(results=results, total=total.one(), page=params.page, per_page=params.per_page)


async def get_response_messages_by_filter(
    session: AsyncSession, params: models.ResponseMessagePaginationParams
) -> pagination.Paginated[models.ResponseMessageRead]:
    query = sa.select(models.OrderMessage)
    query = params.apply_filter(query)
    query = params.apply_pagination(query)
    result = await session.execute(query)
    results = [models.ResponseMessageRead.model_validate(row, from_attributes=True) for row in result.scalars()]
    total = await session.scalars(params.apply_filter(sa.select(sa.func.count(models.Message.id))))
    return pagination.Paginated(results=results, total=total.one(), page=params.page, per_page=params.per_page)
