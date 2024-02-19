from fastapi import APIRouter, Depends

from src import models, schemas
from src.core import db, enums, pagination
from src.services.auth import flows as auth_flows

from . import flows, service

router = APIRouter(prefix="/preorders", tags=[enums.RouteTag.PREORDERS])


@router.get(path="/filter", response_model=pagination.Paginated[schemas.PreOrderReadUser])
async def get_preorders(
    paging: pagination.PaginationParams = Depends(),
    _=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    return flows.get_by_filter(session, paging)


@router.get(path="", response_model=schemas.PreOrderReadUser)
async def get_preorder(
    order_id: int,
    _=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    order = await flows.get(session, order_id)
    return order


@router.put("", response_model=schemas.PreOrderReadSystem)
async def update_preorder(
    order_id: int,
    data: schemas.PreOrderUpdate,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await flows.get(session, order_id)
    return await service.update(session, order, data)


@router.patch("", response_model=schemas.PreOrderReadSystem)
async def patch_preorder(
    order_id: int,
    data: schemas.PreOrderUpdate,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await flows.get(session, order_id)
    return await service.update(session, order, data, patch=True)


@router.delete("", response_model=schemas.PreOrderReadSystem)
async def delete_preorder(
    order_id: int,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await flows.get(session, order_id)
    await service.delete(session, order_id)
    return order
