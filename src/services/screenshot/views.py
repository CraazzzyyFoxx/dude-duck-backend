from fastapi import APIRouter, Depends

from src.core import db, enums, errors, pagination
from src.services.accounting import service as accounting_flows
from src.services.auth import flows as auth_flows
from src.services.auth import models as auth_models
from src.services.order import flows as order_flows
from src.services.order import models as order_models
from src.services.order import schemas as order_schemas

from . import service

router = APIRouter(prefix="/screenshot", tags=[enums.RouteTag.SCREENSHOTS])


@router.post("/", response_model=order_models.ScreenshotRead)
async def create_screenshot(
    screenshot_in: order_models.ScreenshotCreate,
    user: auth_models.User = Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    order = await order_flows.get(session, screenshot_in.order_id)
    return await service.create(session, user, order, screenshot_in.url.unicode_string())


@router.delete("/{screenshot_id}", response_model=order_models.ScreenshotRead)
async def delete_screenshot(
    screenshot_id: int,
    user: auth_models.User = Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    return await service.delete(session, user, screenshot_id)


@router.get("/filter", response_model=pagination.Paginated[order_models.ScreenshotRead])
async def filter_screenshot(
    params: order_schemas.ScreenshotParams = Depends(),
    user: auth_models.User = Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    if params.order_id and not user.is_superuser:
        user_order = await accounting_flows.get_by_order_id_user_id(session, params.order_id, user.id)
        if not user_order:
            raise errors.ApiHTTPException(
                status_code=403,
                detail=[
                    errors.ApiException(
                        msg=f"User does not have access to this order. [user_id={user.id}, order_id={params.order_id}]",
                        code="not_access",
                    )
                ],
            )
    if not params.order_id and not user.is_superuser:
        raise errors.ApiHTTPException(
            status_code=403,
            detail=[
                errors.ApiException(
                    msg=f"User does not have access to this order. [user_id={user.id}, order_id={params.order_id}]",
                    code="not_access",
                )
            ],
        )
    return await service.get_by_filter(session, params)
