from fastapi import APIRouter, Depends
from starlette import status

from app.core import enums, errors
from app.services.auth import flows as auth_flows
from app.services.search import models as search_models

from ..service import request as service_request
from . import models

router = APIRouter(
    prefix="/render",
    tags=[enums.RouteTag.RENDER],
    dependencies=[Depends(auth_flows.current_active_superuser)],
)


@router.get(path="", response_model=search_models.Paginated[models.RenderConfigRead])
async def get_renders(
    paging: search_models.PaginationParams = Depends(),
):
    response = await service_request(
        f"render?page={paging.page}&per_page={paging.per_page}",
        "GET",
    )
    return response.json()


@router.get("/{name}", response_model=models.RenderConfigRead)
async def read_order_render(name: str):
    response = await service_request(f"render/{name}", "GET")
    if response.status_code == 404:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A render with this id does not exist.", code="not_exist")],
        )
    return response.json()


@router.post("", response_model=models.RenderConfigRead)
async def create_order_render(render: models.RenderConfigCreate):
    response = await service_request("render", "POST", data=render.model_dump())
    if response.status_code == 404:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[errors.DudeDuckException(msg="A render with this game already exist.", code="already_exist")],
        )
    return response.json()


@router.delete("/{name}", response_model=models.RenderConfigRead)
async def delete_order_render(name: str):
    response = await service_request(f"render/{name}", "DELETE")
    if response.status_code == 404:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A render with this id does not exist.", code="not_exist")],
        )
    return response.json()


@router.patch("/{name}", response_model=models.RenderConfigRead)
async def update_order_render(name: str, data: models.RenderConfigUpdate):
    response = await service_request(f"render/{name}", "PATCH", data=data.model_dump())
    if response.status_code == 404:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="A render with this id does not exist.", code="not_exist")],
        )
    return response.json()
