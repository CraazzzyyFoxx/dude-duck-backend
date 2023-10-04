from fastapi import APIRouter, Depends

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.search import models as search_models
from app.services.search import service as search_service

from . import flows, models, schemas, service

router = APIRouter(prefix="/orders", tags=[enums.RouteTag.ORDERS])


@router.get(path="/{order_id}", response_model=schemas.OrderReadNoPerms)
async def get_order(order_id: int, _=Depends(auth_flows.current_active_verified)):
    order = await flows.get(order_id)
    return await flows.format_order_perms(order)


@router.get(path="", response_model=search_service.models.Paginated[schemas.OrderReadNoPerms])
async def get_orders(
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.OrderSortingParams = Depends(),
    _=Depends(auth_flows.current_active_verified),
):
    data = await flows.get_filter(paging, sorting)
    data["results"] = [await flows.format_order_perms(order) for order in data["results"]]
    return data


@router.put("/{order_id}", response_model=schemas.OrderReadSystem)
async def update_order(
    order_id: int,
    data: models.OrderUpdate,
    _=Depends(auth_flows.current_active_superuser),
):
    order = await flows.get(order_id)
    updated_order = await service.update(order, data)
    return await flows.format_order_system(updated_order)


@router.patch("/{order_id}", response_model=schemas.OrderReadSystem)
async def patch_order(
    order_id: int,
    data: models.OrderUpdate,
    _=Depends(auth_flows.current_active_superuser),
):
    order = await flows.get(order_id)
    patched_order = await service.patch(order, data)
    return await flows.format_order_system(patched_order)


@router.delete("/{order_id}", response_model=schemas.OrderReadSystem)
async def delete_order(
    order_id: int,
    _=Depends(auth_flows.current_active_superuser),
):
    order = await flows.get(order_id)
    await service.delete(order_id)
    return await flows.format_order_system(order)
