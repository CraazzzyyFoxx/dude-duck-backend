import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import enums, pagination
from src.services.integrations.channel import service as channel_service
from src.services.integrations.render import flows as render_flows
from src.services.order import schemas as order_schemas
from src.services.preorder import models as preorder_models

from . import models, service


async def pull_create(
    session: AsyncSession,
    integration: enums.Integration,
    order: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
    categories: list[str],
    configs: list[str],
    is_preorder: bool = False,
    is_gold: bool = False,
) -> models.OrderResponse:
    chs_id = [
        ch.channel_id
        for ch in await channel_service.get_by_game_categories(session, integration, order.info.game, categories)
    ]
    if not chs_id:
        return models.OrderResponse(error=True, error_msg="A channels with this game do not exist")
    created, skipped = [], []
    status, text = await render_flows.generate_body(session, integration, order, configs, is_preorder, is_gold)
    if not status:
        return models.OrderResponse(error=True, error_msg=text)
    message_type = models.MessageType.ORDER if not is_preorder else models.MessageType.PRE_ORDER
    for channel_id in chs_id:
        msg_in = models.MessageCreate(
            order_id=order.id, channel_id=channel_id, text=text, type=message_type, integration=integration
        )
        msg, msg_status = await service.create(session, msg_in)
        if not msg:
            skipped.append(models.SkippedPull(channel_id=channel_id, status=msg_status))
        else:
            created.append(models.SuccessPull(channel_id=channel_id, message_id=msg.message_id, status=msg_status))
    return models.OrderResponse(created=created, skipped=skipped)


async def pull_update(
    session: AsyncSession,
    integration: enums.Integration,
    order: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
    configs: list[str],
    is_preorder: bool = False,
    is_gold: bool = False,
) -> models.OrderResponse:
    msgs = await service.get_by_order_id(session, integration, order.id, is_preorder)
    status, text = await render_flows.generate_body(session, integration, order, configs, is_preorder, is_gold)
    if not status:
        return models.OrderResponse(error=True, error_msg=text)
    updated, skipped = [], []
    for msg in msgs:
        msg_in = models.MessageUpdate(
            text=text,
            integration=integration,
        )
        message, msg_status = await service.update(session, msg, msg_in)
        if not message:
            skipped.append(models.SkippedPull(status=msg_status, channel_id=msg.channel_id))
        else:
            updated.append(models.SuccessPull(channel_id=msg.channel_id, message_id=msg.message_id, status=msg_status))
    return models.OrderResponse(updated=updated, skipped=skipped)


async def pull_delete(
    session: AsyncSession,
    integration: enums.Integration,
    order: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
    is_preorder: bool = False,
) -> models.OrderResponse:
    msgs = await service.get_by_order_id(session, integration, order.id, is_preorder)
    deleted, skipped = [], []
    for msg in msgs:
        message, msg_status = await service.delete(session, msg)
        if not message:
            skipped.append(models.SkippedPull(status=msg_status, channel_id=msg.channel_id))
        else:
            deleted.append(models.SuccessPull(channel_id=msg.channel_id, message_id=msg.message_id, status=msg_status))
    return models.OrderResponse(deleted=deleted, skipped=skipped)


async def get_by_filter(
    session: AsyncSession, params: models.MessagePaginationParams
) -> pagination.Paginated[models.MessageRead]:
    query = sa.select(models.Message)
    query = params.apply_filter(query)
    query = params.apply_pagination(query)
    result = await session.execute(query)
    results = [models.MessageRead.model_validate(row, from_attributes=True) for row in result.scalars()]
    total = await session.scalars(params.apply_filter(sa.select(sa.func.count(models.Message.id))))
    return pagination.Paginated(results=results, total=total.one(), page=params.page, per_page=params.per_page)
