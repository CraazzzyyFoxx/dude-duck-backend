from fastapi import HTTPException
from starlette import status

from app.services.orders import service as orders_service
from app.services.response import service as response_service
from app.services.auth import service as auth_service

from . import service


async def create_order_message(
        order: orders_service.models.Order,
        categories: list[str],
        config_names: list[str]
):
    messages = await service.pull_create(order, categories, config_names)
    if not messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=[
                                {
                                    "msg": "The bot either does not have access to the channel "
                                           "with orders or there are already messages with information about the order"
                                }
                            ])
    return messages


async def update_order_message(
        order: orders_service.models.Order,
        config_names: list[str]
):
    messages = await service.pull_edit(order, config_names)
    if not messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=[
                                {
                                    "msg": "The bot either does not have access to the channel "
                                           "with orders or all messages contain up-to-date information about the order."
                                }
                            ])
    return messages


async def delete_order_message(order: orders_service.models.Order):
    messages = await service.pull_delete(order)
    if not messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=[
                                {
                                    "msg": "The bot either does not have access to the "
                                           "channel with orders or it has nothing to delete."
                                }
                            ])
    return messages


async def delete_all_responses(order: orders_service.models.Order):
    responses = await response_service.get_by_order_id(order.id)
    if responses:
        for response in responses:
            user = await auth_service.get_user(response.user.id)
            await service.pull_send_response_decline(user, order)
