from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from app.core.enums import RouteTag
from app.services.auth import flows as auth_flows
from app.services.auth import service as auth_service
from app.services.orders import flows as order_flows
from app.services.preorders import flows as preorder_flows
from app.services.search import models as search_models
from app.services.search import service as search_service

from . import flows, models, service

router = APIRouter(prefix='/response', tags=[RouteTag.RESPONSES])


@router.get('/{order_id}', response_model=search_models.Paginated[models.ResponseRead])
async def get_responses(
        order_id: PydanticObjectId,
        paging: search_models.PaginationParams = Depends(),
        sorting: search_models.SortingParams = Depends(),
        _=Depends(auth_flows.current_active_superuser)
):
    order = await order_flows.get(order_id)
    return await search_service.paginate(models.Response.find({"order_id": order.id}), paging, sorting)


@router.post('/{order_id}', status_code=201, response_model=models.ResponseRead)
async def create_response(
        order_id: PydanticObjectId,
        data: models.ResponseExtra,
        user=Depends(auth_flows.current_active_verified)
):
    order = await order_flows.get(order_id)
    resp = await flows.create_response(user, order, data)
    return resp


@router.post('/preorder/{order_id}', status_code=201, response_model=models.ResponseRead)
async def create_preorder_response(
        order_id: PydanticObjectId,
        data: models.ResponseExtra,
        user=Depends(auth_flows.current_active_verified)
):
    order = await preorder_flows.get(order_id)
    resp = await flows.create_preorder_response(user, order, data)
    return resp


@router.get('/{order_id}/{user_id}', response_model=models.ResponseRead)
async def get_response(
        order_id: PydanticObjectId,
        user=Depends(auth_flows.resolve_user)
):
    user = await auth_service.get(user.id)
    return await flows.get_by_order_id_user_id(order_id, user.id)


@router.delete('/{order_id}/{user_id}', response_model=models.ResponseRead)
async def remove_response(
        order_id: PydanticObjectId,
        user_id: PydanticObjectId,
        _=Depends(auth_flows.current_active_superuser)
):
    user = await auth_service.get(user_id)
    resp = await flows.get_by_order_id_user_id(order_id, user.id)
    await service.delete(resp.id)
    return resp


@router.get('/{order_id}/{user_id}/approve', response_model=models.ResponseRead)
async def approve_response(
        order_id: PydanticObjectId,
        user_id: PydanticObjectId,
        _=Depends(auth_flows.current_active_superuser)
):
    order = await order_flows.get(order_id)
    user = await auth_service.get(user_id)

    response = await flows.approve_response(user, order)
    return response


@router.get('/preorder/{order_id}/{user_id}/approve', response_model=models.ResponseRead)
async def approve_preorder_response(
        order_id: PydanticObjectId,
        user_id: PydanticObjectId,
        _=Depends(auth_flows.current_active_superuser)
):
    order = await preorder_flows.get(order_id)
    user = await auth_service.get(user_id)

    response = await flows.approve_preorder_response(user, order)
    return response
