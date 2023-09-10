from app.services.orders import schemas as order_schemas
from app.services.preorders import models as preorder_models
from app.services.telegram.message import service as message_service

from . import service


async def create_order_message(
        order: order_schemas.OrderReadUser,
        categories: list[str],
        config_names: list[str]
):
    messages = await service.pull_order_create(order, categories, config_names)
    message_service.send_sent_order_notify(order, messages)
    return messages


async def update_order_message(
        order: order_schemas.OrderReadUser,
        config_names: list[str]
):
    messages = await service.pull_order_edit(order, config_names)
    message_service.send_edited_order_notify(order, messages)
    return messages


async def delete_order_message(
        order: order_schemas.OrderReadUser,
):
    messages = await service.pull_order_delete(order)
    message_service.send_deleted_order_notify(order, messages)
    return messages


async def create_preorder_message(
        order: preorder_models.PreOrderRead,
        categories: list[str],
        config_names: list[str]
):
    messages = await service.pull_preorder_create(order, categories, config_names)
    message_service.send_sent_preorder_notify(order, messages)
    return messages


async def update_preorder_message(
        order: preorder_models.PreOrderRead,
        config_names: list[str]
):
    messages = await service.pull_preorder_edit(order, config_names)
    message_service.send_edited_preorder_notify(order, messages)
    return messages


async def delete_preorder_message(
        order: preorder_models.PreOrderRead
):
    messages = await service.pull_preorder_delete(order)
    message_service.send_deleted_preorder_notify(order, messages)
    return messages
