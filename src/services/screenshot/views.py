from fastapi import APIRouter, Depends

from src import models, schemas
from src.core import db, enums, errors, pagination
from src.services.accounting import service as accounting_flows
from src.services.auth import flows as auth_flows
from src.services.order import flows as order_flows

from . import flows, service

router = APIRouter(prefix="/screenshot", tags=[enums.RouteTag.SCREENSHOTS])


@router.post("/", response_model=models.ScreenshotRead)
async def create_screenshot(
    screenshot_in: models.ScreenshotCreate,
    user: models.User = Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    order = await order_flows.get(session, screenshot_in.order_id)
    return await flows.create(session, user, order, screenshot_in.url.unicode_string())


@router.delete("/{screenshot_id}", response_model=models.ScreenshotRead)
async def delete_screenshot(
    screenshot_id: int,
    user: models.User = Depends(auth_flows.current_active_verified),
    session=Depends(db.get_async_session),
):
    return await flows.delete(session, user, screenshot_id)


@router.get("/filter", response_model=pagination.Paginated[models.ScreenshotRead])
async def filter_screenshot(
    params: schemas.ScreenshotParams = Depends(),
    user: models.User = Depends(auth_flows.current_active_verified),
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
