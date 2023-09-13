from fastapi import APIRouter, Depends, HTTPException
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
):
    response = await service_request(
        f'render?page={paging.page}&per_page={paging.per_page}',
        'GET',
    )
    return response.json()


@router.get('/{name}', response_model=models.RenderConfigRead)
async def read_order_render(name: str):
    response = await service_request(f'render/{name}', 'GET')
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A render with this id does not exist."}],
        )
    return response.json()


@router.post('', response_model=models.RenderConfigRead)
async def create_order_render(render: models.RenderConfigCreate):
    response = await service_request('render', 'POST', data=render.model_dump())
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A render with this game already exist."}],
        )
    return response.json()


@router.delete('/{name}', response_model=models.RenderConfigRead)
async def delete_order_render(name: str):
    response = await service_request(f'render/{name}', 'DELETE')
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A render with this id does not exist."}],
        )
    return response.json()


@router.patch('/{name}', response_model=models.RenderConfigRead)
async def update_order_render(name: str, data: models.RenderConfigUpdate):
    response = await service_request(f'render/{name}', 'PATCH', data=data.model_dump())
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"msg": "A render with this id does not exist."}],
        )
    return response.json()
