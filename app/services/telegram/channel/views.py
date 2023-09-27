from beanie import PydanticObjectId
from fastapi import APIRouter, Depends
from starlette import status

from app.core import enums, errors
from app.services.auth import flows as auth_flows
from app.services.search import models as search_models

from ..service import request as service_request
from . import models

router = APIRouter(
    prefix="/channels",
    tags=[enums.RouteTag.CHANNELS],
    dependencies=[Depends(auth_flows.current_active_superuser)],
)


@router.get(path="", response_model=search_models.Paginated[models.ChannelRead])
async def get_channels(
    paging: search_models.PaginationParams = Depends(),
):
    response = await service_request(
        f"channel?page={paging.page}&per_page={paging.per_page}",
        "GET",
    )
    return response.json()


@router.get("/{channel_id}", response_model=models.ChannelRead)
async def read_order_channel(channel_id: PydanticObjectId):
    response = await service_request(f"channel/{channel_id}", "GET")
    if response.status_code == 404:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A channel with this id does not exist.", code="not_exist")],
        )
    return response.json()


@router.post("", response_model=models.ChannelRead)
async def create_order_channel(channel: models.ChannelCreate):
    response = await service_request("channel", "POST", data=channel.model_dump())
    if response.status_code == 404:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[errors.DudeDuckException(msg="A channel with this game already exist.", code="already_exist")],
        )
    return response.json()


@router.delete("/{channel_id}", response_model=models.ChannelRead)
async def delete_order_channel(channel_id: PydanticObjectId):
    response = await service_request(f"channel/{channel_id}", "DELETE")
    if response.status_code == 404:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A channel with this id does not exist.", code="not_exist")],
        )
    return response.json()


@router.patch("/{channel_id}", response_model=models.ChannelRead)
async def update_order_channel(channel_id: PydanticObjectId, data: models.ChannelUpdate):
    response = await service_request(f"channel/{channel_id}", "PATCH", data=data.model_dump())
    if response.status_code == 404:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A channel with this id does not exist.", code="not_exist")],
        )
    return response.json()
