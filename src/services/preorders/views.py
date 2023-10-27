from fastapi import APIRouter, Depends

from src.core import enums
from src.services.auth import flows as auth_flows
from src.services.search import models as search_models
from src.services.search import service as search_service

from src.core import db
from . import flows, models, service

router = APIRouter(prefix="/preorders", tags=[enums.RouteTag.PREORDERS])


@router.get(path="/{order_id}", response_model=models.PreOrderReadUser)
async def get_preorder(
        order_id: int, _=Depends(auth_flows.current_active_verified), session=Depends(db.get_async_session)
):
    order = await flows.get(session, order_id)
    return order


@router.get(path="", response_model=search_models.Paginated[models.PreOrderReadUser])
async def get_preorders(
    paging: search_models.PaginationParams = Depends(),
    sorting: search_models.OrderSortingParams = Depends(),
    _=Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    data = await search_service.paginate(models.PreOrder.filter(), paging, sorting)
    return data


@router.put("/{order_id}", response_model=models.PreOrderReadSystem)
async def update_preorder(
        order_id: int,
        data: models.PreOrderUpdate,
        _=Depends(auth_flows.current_active_superuser),
        session=Depends(db.get_async_session)
):
    order = await flows.get(session, order_id)
    return await service.update(session, order, data)


@router.patch("/{order_id}", response_model=models.PreOrderReadSystem)
async def patch_preorder(
        order_id: int,
        data: models.PreOrderUpdate,
        _=Depends(auth_flows.current_active_superuser),
        session=Depends(db.get_async_session)
):
    order = await flows.get(session, order_id)
    return await service.patch(session, order, data)


@router.delete("/{order_id}", response_model=models.PreOrderReadSystem)
async def delete_preorder(
        order_id: int,
        _=Depends(auth_flows.current_active_superuser),
        session=Depends(db.get_async_session)
):
    order = await flows.get(session, order_id)
    await service.delete(session, order_id)
    return order
