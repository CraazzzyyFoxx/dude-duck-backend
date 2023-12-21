from fastapi import APIRouter, Depends

from src import models, schemas
from src.core import db, enums, pagination
from src.services.auth import flows as auth_flows

from . import flows, service

router = APIRouter(prefix="/orders", tags=[enums.RouteTag.ORDERS])


@router.post(path="/filter", response_model=pagination.Paginated[schemas.OrderReadNoPerms])
async def get_orders(
    params: schemas.OrderFilterParams,
    _=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    return await flows.get_by_filter(session, params)


@router.get(path="", response_model=schemas.OrderReadNoPerms)
async def get_order(
    order_id: int,
    _=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    order = await flows.get(session, order_id)
    return await flows.format_order_perms(session, order)


@router.put("", response_model=schemas.OrderReadSystem)
async def update_order(
    order_id: int,
    data: models.OrderUpdate,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await flows.get(session, order_id)
    updated_order = await service.update(session, order, data)
    return await flows.format_order_system(session, updated_order)


@router.patch("", response_model=schemas.OrderReadSystem)
async def patch_order(
    order_id: int,
    data: models.OrderUpdate,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await flows.get(session, order_id)
    patched_order = await service.update(session, order, data, patch=True)
    return await flows.format_order_system(session, patched_order)


@router.delete("", response_model=schemas.OrderReadSystem)
async def delete_order(
    order_id: int,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await flows.get(session, order_id)
    await service.delete(session, order_id)
    return await flows.format_order_system(session, order)
