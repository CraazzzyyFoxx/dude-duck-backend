from fastapi import APIRouter, Depends, HTTPException
from beanie import PydanticObjectId
from starlette import status

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.search import service as search_service

from ..service import request as service_request
from . import models


router = APIRouter(prefix='/render', tags=[enums.RouteTag.RENDER],
                   dependencies=[Depends(auth_flows.current_active_superuser)])


@router.get(path="", response_model=search_service.models.Paginated[models.RenderConfigRead])
async def get_renders(
        paging: search_service.models.PaginationParams = Depends(),
        sorting: search_service.models.OrderSortingParams = Depends()
):
    response = await service_request(
        f'render?page={paging.page}&per_page={paging.per_page}&sort={sorting.sort}&order={sorting.order.value}',
        'GET',
    )
    return response.json()


@router.get('/{render_id}', response_model=models.RenderConfigRead)
async def read_order_render(render_id: PydanticObjectId):
    response = await service_request(f'render/{render_id}', 'GET')
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A render with this id does not exist."}],
        )
    return response.json()


@router.post('', response_model=models.RenderConfigRead)
async def create_order_render(render: models.RenderConfigCreate):
    response = await service_request(f'render', 'POST', data=render.model_dump())
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A render with this game already exist."}],
        )
    return response.json()


@router.delete('/{render_id}', response_model=models.RenderConfigRead)
async def delete_order_render(render_id: PydanticObjectId):
    response = await service_request(f'render/{render_id}', 'DELETE')
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A render with this id does not exist."}],
        )
    return response.json()


@router.patch('/{render_id}', response_model=models.RenderConfigRead)
async def update_order_render(render_id: PydanticObjectId, data: models.RenderConfigUpdate):
    response = await service_request(f'render/{render_id}', 'PATCH', data=data.model_dump())
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A render with this id does not exist."}],
        )
    return response.json()
