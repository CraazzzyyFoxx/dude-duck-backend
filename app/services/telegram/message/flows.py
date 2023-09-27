from app.services.orders import schemas as order_schemas
from app.services.preorders import models as preorder_models

from . import models, service


async def create_order_message(
    order: order_schemas.OrderReadSystem, categories: list[str], config_names: list[str], is_gold: bool = False
) -> models.OrderResponse:
    messages = await service.order_create(order, categories, config_names, is_gold=is_gold)
    service.send_sent_order_notify(order.order_id, messages)
    return messages


async def update_order_message(
    order: order_schemas.OrderReadSystem, config_names: list[str], is_gold: bool = False
) -> models.OrderResponse:
    messages = await service.order_edit(order, config_names, is_gold=is_gold)
    service.send_edited_order_notify(order.order_id, messages)
    return messages


async def delete_order_message(
    order: order_schemas.OrderReadSystem,
) -> models.OrderResponse:
    messages = await service.order_delete(order)
    service.send_deleted_order_notify(order.order_id, messages)
    return messages


async def create_preorder_message(
    order: preorder_models.PreOrderReadSystem, categories: list[str], config_names: list[str], is_gold: bool = False
) -> models.OrderResponse:
    messages = await service.order_create(order, categories, config_names, is_pre=True, is_gold=is_gold)
    service.send_sent_order_notify(order.order_id, messages)
    return messages


async def update_preorder_message(
    order: preorder_models.PreOrderReadSystem, config_names: list[str], is_gold: bool = False
) -> models.OrderResponse:
    messages = await service.order_edit(order, config_names, is_pre=True, is_gold=is_gold)
    service.send_edited_order_notify(order.order_id, messages)
    return messages


async def delete_preorder_message(order: preorder_models.PreOrderReadSystem):
    messages = await service.order_delete(order, pre=True)
    service.send_deleted_order_notify(order.order_id, messages)
    return messages
