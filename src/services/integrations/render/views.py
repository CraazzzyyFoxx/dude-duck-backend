from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from starlette import status

from src.core import db, enums, errors, pagination
from src.services.accounting import flows as accounting_flows
from src.services.auth import flows as auth_flows
from src.services.order import flows as order_flows
from src.services.preorder import flows as preorder_flows
from src.services.response import flows as response_flows

from . import flows, models, service

router = APIRouter(
    prefix="/integrations/render",
    tags=[enums.RouteTag.ORDER_RENDERS],
    dependencies=[Depends(auth_flows.current_active_superuser)],
)


@router.post("/filter", response_model=pagination.Paginated[models.RenderConfigRead])
async def reads_render_config(
    params: models.RenderConfigParams = Depends(),
    session=Depends(db.get_async_session),
    _=Depends(auth_flows.current_active_superuser),
):
    return await service.get_by_filter(session, params)


@router.post("", response_model=models.RenderConfigRead)
async def create_render_config(
    render_in: models.RenderConfigCreate,
    session=Depends(db.get_async_session),
    _=Depends(auth_flows.current_active_superuser),
):
    data = await service.get_by_name(session, render_in.integration, render_in.name)
    if data:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[
                errors.ApiException(
                    msg=f"A Render Config with this name={render_in.name} already exists.", code="already_exists"
                )
            ],
        )
    return await service.create(session, render_in)


@router.patch("", response_model=models.RenderConfigRead)
async def update_render_config(
    id: int,
    render_in: models.RenderConfigUpdate,
    session=Depends(db.get_async_session),
    _=Depends(auth_flows.current_active_superuser),
):
    data = await flows.get(session, id)
    return await service.update(session, data, render_in)


@router.delete("")
async def delete_render_config(
    id: int, session=Depends(db.get_async_session), _=Depends(auth_flows.current_active_superuser)
):
    parser = await flows.get(session, id)
    return await service.delete(session, parser.id)


@router.get("/order")
async def render_order(
    order_id: int,
    integration: enums.Integration,
    is_preorder: bool = False,
    is_gold: bool = False,
    with_credentials: bool = False,
    with_response: bool = False,
    response_checked: bool = False,
    user_id: int | None = None,
    session=Depends(db.get_async_session),
    user=Depends(auth_flows.current_active_verified),
):
    if with_response and with_credentials:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.ApiException(
                    msg="You can't use with_credentials and with_response at the same time.", code="bad_request"
                )
            ],
        )
    if is_preorder:
        preorder = await preorder_flows.get(session, order_id)
        preorder_read = await preorder_flows.format_preorder_perms(session, preorder)
        if preorder_read.price.booster_gold is None and is_gold:
            raise errors.ApiHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=[errors.ApiException(msg="This order doesn't have a gold price.", code="bad_request")],
            )
        configs = flows.get_order_configs(preorder_read, is_preorder=is_preorder, is_gold=is_gold)
        data = await flows.generate_body(session, integration, preorder_read, configs, is_preorder, is_gold)
        text = data[1]

    else:
        order = await order_flows.get(session, order_id)
        order_read = await order_flows.format_order_system(session, order)
        if order_read.price.booster_gold is None and is_gold:
            raise errors.ApiHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=[errors.ApiException(msg="This order doesn't have a gold price.", code="bad_request")],
            )
        if with_response:
            if not user_id:
                raise errors.ApiHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=[
                        errors.ApiException(
                            msg="You must specify the user_id parameter to use with_response.",
                            code="bad_request",
                        )
                    ],
                )
            specified_user = await auth_flows.get(session, user_id)
            response = await response_flows.get_by_order_id_user_id(session, order.id, specified_user.id)
            configs = flows.get_order_configs(
                order_read,
                is_preorder=is_preorder,
                is_gold=is_gold,
                with_response=True,
                response_checked=response_checked,
            )
            text = await flows.get_order_text(
                session, integration, configs, data={"order": order_read, "response": response, "user": specified_user}
            )
        else:
            if with_credentials:
                user_order = await accounting_flows.get_by_order_id_user_id(session, order, user)
                configs = flows.get_order_configs(
                    order_read, is_preorder=is_preorder, is_gold=is_gold, creds=user_order or user.is_superuser
                )
            else:
                configs = flows.get_order_configs(order_read, is_preorder=is_preorder, is_gold=is_gold)
            data = await flows.generate_body(session, integration, order_read, configs, is_preorder, is_gold)
            text = data[1]

    return ORJSONResponse({"text": text})
