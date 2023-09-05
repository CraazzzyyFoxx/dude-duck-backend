from fastapi import APIRouter, Depends
from beanie import PydanticObjectId

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.search import service as search_service

from . import flows, models, service

router = APIRouter(prefix="/preorders", tags=[enums.RouteTag.PREORDERS],
                   dependencies=[Depends(auth_flows.current_active_superuser)])


@router.get(path="/{preorder_id}", response_model=models.PreOrderRead)
async def get_order(preorder_id: PydanticObjectId):
    order = await flows.get(preorder_id)
    return order


@router.patch(path="/{preorder_id}", response_model=models.PreOrderRead)
async def update_order(preorder_id: PydanticObjectId, data: models.PreOrderUpdate, ):
    order = await flows.get(preorder_id)
    order = await service.update(order, data)
    return order


@router.get(path="", response_model=search_service.models.Paginated[models.PreOrderRead])
async def get_orders(
        paging: search_service.models.PaginationParams = Depends(),
        sorting: search_service.models.OrderSortingParams = Depends()
):
    query = {}
    data = await search_service.paginate(models.PreOrder.find(query), paging, sorting)
    data["results"] = [order for order in data["results"]]
    return data
