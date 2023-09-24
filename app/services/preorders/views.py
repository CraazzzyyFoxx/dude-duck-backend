from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.search import models as search_models
from app.services.search import service as search_service

from . import flows, models

router = APIRouter(prefix="/preorders", tags=[enums.RouteTag.PREORDERS])


@router.get(path="/{preorder_id}", response_model=models.PreOrderReadUser)
async def get_preorder(preorder_id: PydanticObjectId, _=Depends(auth_flows.current_active_verified)):
    order = await flows.get(preorder_id)
    return order


@router.get(path="", response_model=search_models.Paginated[models.PreOrderReadUser])
async def get_preorders(
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.OrderSortingParams = Depends(),
    _=Depends(auth_flows.current_active_verified),
):
    data = await search_service.paginate(models.PreOrder.find_all(), paging, sorting)
    return data
