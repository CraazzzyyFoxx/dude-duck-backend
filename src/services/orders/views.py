from fastapi import APIRouter, Depends

from src.core import enums, db
from src.services.auth import flows as auth_flows
from src.services.search import models as search_models

from . import flows, models, schemas, service

router = APIRouter(prefix="/orders", tags=[enums.RouteTag.ORDERS])


@router.get(path="/{order_id}", response_model=schemas.OrderReadNoPerms)
async def get_order(
    order_id: int, _=Depends(auth_flows.current_active_verified), session=Depends(db.get_async_session)
):
    order = await flows.get(session, order_id)
    return await flows.format_order_perms(session, order)


@router.get(path="", response_model=search_models.Paginated[schemas.OrderReadNoPerms])
async def get_orders(
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.OrderSortingParams = Depends(),
    _=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    data = await flows.get_filter(paging, sorting)
    data["results"] = [await flows.format_order_perms(session, order) for order in data["results"]]
    return data


@router.put("/{order_id}", response_model=schemas.OrderReadSystem)
async def update_order(
    order_id: int,
    data: models.OrderUpdate,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await flows.get(session, order_id)
    updated_order = await service.update(session, order, data)
    return await flows.format_order_system(session, updated_order)


@router.patch("/{order_id}", response_model=schemas.OrderReadSystem)
async def patch_order(
    order_id: int,
    data: models.OrderUpdate,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await flows.get(session, order_id)
    patched_order = await service.patch(session, order, data)
    return await flows.format_order_system(session, patched_order)


@router.delete("/{order_id}", response_model=schemas.OrderReadSystem)
async def delete_order(
    order_id: int, _=Depends(auth_flows.current_active_superuser), session=Depends(db.get_async_session)
):
    order = await flows.get(session, order_id)
    await service.delete(session, order_id)
    return await flows.format_order_system(session, order)
