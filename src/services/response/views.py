from fastapi import APIRouter, Depends

from src import models, schemas
from src.core import db, enums, pagination
from src.services.auth import flows as auth_flows
from src.services.order import flows as order_flows
from src.services.preorder import flows as preorder_flows

from . import flows, service

router = APIRouter(prefix="/response", tags=[enums.RouteTag.RESPONSES])


@router.get("/filter", response_model=pagination.Paginated[schemas.ResponseRead])
async def get_responses(
    params: schemas.ResponsePagination = Depends(),
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await flows.get_by_filter(session, params)


@router.post("", status_code=201, response_model=schemas.ResponseRead)
async def create_response(
    order_id: int,
    data: schemas.ResponseExtra,
    is_preorder: bool = False,
    user=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    if is_preorder:
        preorder = await preorder_flows.get(session, order_id)
        return await flows.create_order_response(session, user, preorder, data, is_preorder=True)
    else:
        order = await order_flows.get(session, order_id)
        return await flows.create_order_response(session, user, order, data)


@router.get("/{order_id}/{user_id}", response_model=schemas.ResponseRead)
async def get_response(
    order_id: int,
    user=Depends(auth_flows.resolve_user),
    session=Depends(db.get_async_session),
):
    user = await auth_flows.get(session, user.id)
    return await flows.get_by_order_id_user_id(session, order_id, user.id)


@router.delete("", response_model=schemas.ResponseRead)
async def delete_response(
    response_id: int,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    resp = await flows.get(session, response_id)
    await service.delete(session, resp.id)
    return resp


@router.patch("/{order_id}/{user_id}", response_model=schemas.ResponseRead)
async def approve_response(
    order_id: int,
    user_id: int,
    approve: bool,
    is_preorder: bool = False,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    user = await auth_flows.get(session, user_id)
    if approve:
        if is_preorder:
            preorder = await preorder_flows.get(session, order_id)
            return await flows.approve_preorder_response(session, user, preorder)
        else:
            order = await order_flows.get(session, order_id)
            return await flows.approve_response(session, user, order)
    else:
        if is_preorder:
            preorder = await preorder_flows.get(session, order_id)
            return await flows.decline_preorder_response(session, user, preorder)
        else:
            order = await order_flows.get(session, order_id)
            return await flows.decline_response(session, user, order)
