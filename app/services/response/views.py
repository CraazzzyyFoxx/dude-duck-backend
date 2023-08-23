from fastapi import APIRouter, Depends
from beanie import PydanticObjectId
from loguru import logger

from app.core.enums import RouteTag
from app.services.orders import flows as order_flows
from app.services.auth import flows as auth_flows
from app.services.auth import service as auth_service
from app.services.search import service as search_service

from . import models, flows, service

router = APIRouter(prefix='/response', tags=[RouteTag.RESPONSES])


@router.get('/{order_id}', response_model=search_service.models.Paginated[models.ResponseRead])
async def get_responses(
        order_id: PydanticObjectId,
        paging: search_service.models.PaginationParams = Depends(),
        sorting: search_service.models.SortingParams = Depends(),
        _=Depends(auth_service.current_active_superuser)
):
    order = await order_flows.get(order_id)
    return await search_service.paginate(
        models.Response.find(models.Response.order.id == order.id, fetch_links=True), paging, sorting)


@router.post('/{order_id}', status_code=201, response_model=models.ResponseRead)
async def create_responses(
        order_id: PydanticObjectId,
        data: models.ResponseExtra,
        user=Depends(auth_service.current_active_verified)
):
    order = await order_flows.get(order_id)
    resp = await flows.create_response(user, order, data)
    return await flows.get(resp.id)


@router.get('/{order_id}/{user_id}', response_model=models.ResponseRead)
async def get_response(
        order_id: PydanticObjectId,
        user=Depends(auth_flows.resolve_user)
):
    order = await order_flows.get(order_id)
    user = await auth_flows.get(user.id)
    return await flows.get_by_order_id_user_id(order.id, user.id)


@router.get('/{order_id}/{user_id}/approve', response_model=models.ResponseRead)
async def approve_response(
        order_id: PydanticObjectId,
        user_id: PydanticObjectId,
        _=Depends(auth_service.current_active_superuser)
):
    order = await order_flows.get(order_id)
    user = await auth_flows.get(user_id)

    response = await flows.approve_response(user, order)
    return response
