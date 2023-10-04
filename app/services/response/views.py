from fastapi import APIRouter, Depends

from app.core.enums import RouteTag
from app.services.auth import flows as auth_flows
from app.services.orders import flows as order_flows
from app.services.preorders import flows as preorder_flows
from app.services.search import models as search_models
from app.services.search import service as search_service

from . import flows, models, service

router = APIRouter(prefix="/response", tags=[RouteTag.RESPONSES])


@router.get("/{order_id}", response_model=search_models.Paginated[models.ResponseRead])
async def get_responses(
    order_id: int,
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.SortingParams = Depends(),
    _=Depends(auth_flows.current_active_superuser),
):
    order = await order_flows.get(order_id)
    return await search_service.paginate(models.Response.filter(order_id=order.id), paging, sorting)


@router.post("/{order_id}", status_code=201, response_model=models.ResponseRead)
async def create_response(
    order_id: int,
    data: models.ResponseExtra,
    user=Depends(auth_flows.current_active_verified),
):
    order = await order_flows.get(order_id, prefetch=True)
    return await flows.create_order_response(user, order, data)


@router.post("/preorder/{order_id}", status_code=201, response_model=models.ResponseRead)
async def create_preorder_response(
    order_id: int,
    data: models.ResponseExtra,
    user=Depends(auth_flows.current_active_verified),
):
    order = await order_flows.get(order_id, prefetch=True)
    return await flows.create_preorder_response(user, order, data)


@router.get("/{order_id}/{user_id}", response_model=models.ResponseRead)
async def get_response(order_id: int, user=Depends(auth_flows.resolve_user)):
    user = await auth_flows.get(user.id)
    return await flows.get_by_order_id_user_id(order_id, user.id)


@router.delete("/{order_id}/{user_id}", response_model=models.ResponseRead)
async def delete_response(
    order_id: int,
    user_id: int,
    _=Depends(auth_flows.current_active_superuser),
):
    user = await auth_flows.get(user_id)
    resp = await flows.get_by_order_id_user_id(order_id, user.id)
    await service.delete(resp.id)
    return resp


@router.patch("/order/{order_id}/{user_id}", response_model=models.ResponseRead)
async def approve_response(
    order_id: int,
    user_id: int,
    approve: bool,
    _=Depends(auth_flows.current_active_superuser),
):
    order = await order_flows.get(order_id, prefetch=True)
    user = await auth_flows.get(user_id)
    if approve:
        return await flows.approve_response(user, order)
    else:
        return await flows.decline_response(user, order)


@router.patch("/preorder/{order_id}/{user_id}", response_model=models.ResponseRead)
async def approve_preorder_response(
    order_id: int,
    user_id: int,
    approve: bool,
    _=Depends(auth_flows.current_active_superuser),
):
    order = await preorder_flows.get(order_id)
    user = await auth_flows.get(user_id)
    if approve:
        return await flows.approve_preorder_response(user, order)
    else:
        return await flows.decline_preorder_response(user, order)
