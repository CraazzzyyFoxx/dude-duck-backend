from fastapi import APIRouter, Depends

from src import models, schemas
from src.core import db, enums, pagination
from src.services.auth import flows as auth_flows

from . import flows, service

router = APIRouter(
    prefix="/integrations/channel",
    tags=[enums.RouteTag.CHANNELS],
    dependencies=[Depends(auth_flows.current_active_superuser)],
)


@router.get("/filter", response_model=pagination.Paginated[schemas.ChannelRead])
async def reads_order_channel(
    params: schemas.ChannelPaginationParams = Depends(),
    session=Depends(db.get_async_session),
):
    return await flows.get_by_filter(session, params)


@router.get("", response_model=schemas.ChannelRead)
async def read_order_channel(channel_id: int, session=Depends(db.get_async_session)):
    return await flows.get(session, channel_id)


@router.post("", response_model=schemas.ChannelRead)
async def create_order_channel(channel: schemas.ChannelCreate, session=Depends(db.get_async_session)):
    return await flows.create(session, channel)


@router.delete("", response_model=schemas.ChannelRead)
async def delete_order_channel(channel_id: int, session=Depends(db.get_async_session)):
    return await flows.delete(session, channel_id)


@router.patch("", response_model=schemas.ChannelRead)
async def update_order_channel(channel_id: int, data: schemas.ChannelUpdate, session=Depends(db.get_async_session)):
    model = await flows.get(session, channel_id)
    return await service.update(session, model, data)
