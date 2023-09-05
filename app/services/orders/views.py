import typing

from fastapi import APIRouter, Depends
from beanie import PydanticObjectId

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.search import service as search_service
from app.services.permissions import service as permissions_service

from . import schemas, flows, models, service

router = APIRouter(prefix="/orders", tags=[enums.RouteTag.ORDERS])


@router.get(path="/{order_id}", response_model=schemas.OrderRead)
async def get_order(order_id: PydanticObjectId, user=Depends(auth_flows.current_active_superuser)):
    order = await flows.get(order_id)
    return await permissions_service.format_order(order, user)


@router.patch(path="/{order_id}", response_model=typing.Union[schemas.OrderRead])
async def update_order(
        order_id: PydanticObjectId,
        data: models.OrderUpdate,
        user=Depends(auth_flows.current_active_superuser)
):
    order = await flows.get(order_id)
    await service.update_with_sync(order, data)
    return await permissions_service.format_order(order, user)


@router.get(path="",
            response_model=search_service.models.Paginated[schemas.OrderRead])
async def get_orders(
        paging: search_service.models.PaginationParams = Depends(),
        sorting: search_service.models.OrderSortingParams = Depends(),
        user=Depends(auth_flows.current_active_superuser)):
    query = {}
    if sorting.completed != search_service.models.OrderSelection.ALL:
        if sorting.completed == search_service.models.OrderSelection.Completed:
            query = models.Order.status == sorting.completed
        else:
            query = models.Order.status == sorting.completed
    data = await search_service.paginate(models.Order.find(query), paging, sorting)
    data["results"] = [await permissions_service.format_order(order, user) for order in data["results"]]
    return data
