from fastapi import HTTPException

from app.services.orders import service as orders_service
from app.services.telegram.message import service as message_service

from . import service


async def create_order_message(
        order: orders_service.models.Order,
        categories: list[str],
        config_names: list[str]
):
    resp, messages = await service.pull_create(order, categories, config_names)
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail=resp.json())
    await message_service.send_sent_order_notify(order, len(messages.created))
    return messages


async def update_order_message(
        order: orders_service.models.Order,
        config_names: list[str]
):
    resp, messages = await service.pull_edit(order, config_names)
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail=resp.json())
    await message_service.send_edited_order_notify(order, len(messages.updated))
    return messages


async def delete_order_message(
        order: orders_service.models.Order
):
    resp, messages = await service.pull_delete(order)
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail=resp.json())
    await message_service.send_deleted_order_notify(order, len(messages.deleted))
    return messages
