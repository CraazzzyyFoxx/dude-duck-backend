from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.search import service as search_service

from . import flows, models, schemas

router = APIRouter(prefix="/orders", tags=[enums.RouteTag.ORDERS])


@router.get(path="/{order_id}", response_model=schemas.OrderReadNoPerms)
async def get_order(order_id: PydanticObjectId, _=Depends(auth_flows.current_active_verified)):
    order = await flows.get(order_id)
    return await flows.format_order_perms(order)


# @router.get(path="/{order_id}/all", response_model=schemas.OrderReadNoPerms)
# async def get_order_all(order_id: PydanticObjectId, user=Depends(auth_flows.current_active_verified)):
#     order = await flows.get(order_id)
#     await permissions_flows.has_access_to_order(order, user)
#     return await flows.format_order_perms(order, has=True)


@router.get(path="", response_model=search_service.models.Paginated[schemas.OrderReadNoPerms])
async def get_orders(
        paging: search_service.models.PaginationParams = Depends(),
        sorting: search_service.models.OrderSortingParams = Depends(),
        _=Depends(auth_flows.current_active_verified)
):
    query = {}
    if sorting.completed != search_service.models.OrderSelection.ALL:
        if sorting.completed == search_service.models.OrderSelection.Completed:
            query = models.Order.status == sorting.completed
        else:
            query = models.Order.status == sorting.completed
    data = await search_service.paginate(models.Order.find(query), paging, sorting)
    data["results"] = [await flows.format_order_perms(order) for order in data["results"]]
    return data
