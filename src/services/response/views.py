from fastapi import APIRouter, Depends

from src.core import db, enums
from src.services.auth import flows as auth_flows
from src.services.orders import flows as order_flows
from src.services.preorders import flows as preorder_flows
from src.services.search import models as search_models
from src.services.search import service as search_service

from . import flows, models, service

router = APIRouter(prefix="/response", tags=[enums.RouteTag.RESPONSES])


@router.get("/{order_id}", response_model=search_models.Paginated[models.ResponseRead])
async def get_responses(
    order_id: int,
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.SortingParams = Depends(),
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await order_flows.get(session, order_id)
    return await search_service.paginate(models.Response.filter(order_id=order.id), paging, sorting)


@router.post("/{order_id}", status_code=201, response_model=models.ResponseRead)
async def create_response(
    order_id: int,
    data: models.ResponseExtra,
    user=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    order = await order_flows.get(session, order_id)
    return await flows.create_order_response(session, user, order, data)


@router.post("/preorder/{order_id}", status_code=201, response_model=models.ResponseRead)
async def create_preorder_response(
    order_id: int,
    data: models.ResponseExtra,
    user=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    order = await preorder_flows.get(session, order_id)
    return await flows.create_preorder_response(session, user, order, data)


@router.get("/{order_id}/{user_id}", response_model=models.ResponseRead)
async def get_response(order_id: int, user=Depends(auth_flows.resolve_user), session=Depends(db.get_async_session)):
    user = await auth_flows.get(session, user.id)
    return await flows.get_by_order_id_user_id(session, order_id, user.id)


@router.delete("/{order_id}/{user_id}", response_model=models.ResponseRead)
async def delete_response(
    order_id: int,
    user_id: int,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    user = await auth_flows.get(session, user_id)
    resp = await flows.get_by_order_id_user_id(session, order_id, user.id)
    await service.delete(session, resp.id)
    return resp


@router.patch("/order/{order_id}/{user_id}", response_model=models.ResponseRead)
async def approve_response(
    order_id: int,
    user_id: int,
    approve: bool,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await order_flows.get(session, order_id)
    user = await auth_flows.get(session, user_id)
    if approve:
        return await flows.approve_response(session, user, order)
    else:
        return await flows.decline_response(session, user, order)


@router.patch("/preorder/{order_id}/{user_id}", response_model=models.ResponseRead)
async def approve_preorder_response(
    order_id: int,
    user_id: int,
    approve: bool,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    order = await preorder_flows.get(session, order_id)
    user = await auth_flows.get(session, user_id)
    if approve:
        return await flows.approve_preorder_response(session, user, order)
    else:
        return await flows.decline_preorder_response(session, user, order)
