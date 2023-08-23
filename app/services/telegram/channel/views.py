from fastapi import APIRouter, Depends, HTTPException
from beanie import PydanticObjectId
from starlette import status

from app.core import enums
from app.services.auth import service as auth_service
from app.services.search import service as search_service

from . import models, service


router = APIRouter(prefix='/channels', tags=[enums.RouteTag.CHANNELS],
                   dependencies=[Depends(auth_service.current_active_superuser)])


@router.get(path="",
            response_model=search_service.models.Paginated[models.ChannelRead])
async def get_channels(
        paging: search_service.models.PaginationParams = Depends(),
        sorting: search_service.models.OrderSortingParams = Depends()
):
    response = await service.request(
        f'channel?page={paging.page}&per_page={paging.per_page}&sort={sorting.sort}&order={sorting.order.value}',
        'GET',
    )
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=[
            {"msg": "Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable"}
        ])
    return response.json()


@router.get('/{channel_id}', response_model=models.ChannelRead)
async def read_order_channel(channel_id: PydanticObjectId):
    response = await service.request(f'channel/{channel_id}','GET')
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=[
            {"msg": "Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable"}
        ])
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A channel with this id does not exist."}],
        )
    return response.json()


@router.post('/', response_model=models.ChannelRead)
async def create_order_channel(channel: models.ChannelCreate):
    response = await service.request(f'channel', 'POST', data=channel.model_dump())
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=[
            {"msg": "Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable"}
        ])
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A channel with this game already exist."}],
        )
    return response.json()


@router.delete('/{channel_id}', response_model=models.ChannelRead)
async def delete_order_channel(channel_id: PydanticObjectId):
    response = await service.request(f'channel/{channel_id}', 'DELETE')
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=[
            {"msg": "Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable"}
        ])
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A channel with this id does not exist."}],
        )
    return response.json()


@router.patch('/{channel_id}', response_model=models.ChannelRead)
async def update_order_channel(channel_id: PydanticObjectId, data: models.ChannelUpdate):
    response = await service.request(f'channel/{channel_id}', 'PATCH', data=data.model_dump())
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=[
            {"msg": "Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable"}
        ])
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A channel with this id does not exist."}],
        )
    return response.json()
