import datetime

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from lxml.builder import E, ElementMaker
from lxml.etree import tostring
from starlette.responses import Response

from src import models
from src.core import db, enums, errors, pagination
from src.services.auth import flows as auth_flows
from src.services.currency import flows as currency_flows

from . import service

router = APIRouter(prefix="/currency", tags=[enums.RouteTag.CURRENCY])


@router.get("")
async def get_currency(date: datetime.date, session=Depends(db.get_async_session)):
    e_maker = ElementMaker()
    wallet = await currency_flows.get(session, datetime.datetime(year=date.year, month=date.month, day=date.day))
    the_doc = e_maker.root()
    for key, value in wallet.quotes.items():
        the_doc.append(E(key, str(value).replace(".", ",")))  # noqa
    return Response(content=tostring(the_doc, pretty_print=True), media_type="text/xml")


@router.get("/filter", response_model=pagination.Paginated[models.CurrencyTokenRead])
async def get_currency_token_filter(
    params: pagination.PaginationParams = Depends(),
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    query = params.apply_pagination(sa.select(models.CurrencyToken))
    total = await session.execute(sa.select(sa.func.count(models.CurrencyToken.id)))
    result = await session.scalars(query)
    results = [models.CurrencyTokenRead.model_validate(x, from_attributes=True) for x in result]
    return pagination.Paginated(
        results=results,
        total=total.scalar(),
        page=params.page,
        per_page=params.per_page,
    )


@router.post("/api_layer_currency", response_model=models.CurrencyTokenRead)
async def add_api_layer_currency_token(
    token: str,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    tokens = await service.get_tokens(session)
    if token in [x.token for x in tokens]:
        raise errors.ApiHTTPException(
            status_code=400,
            detail=[errors.ApiException(msg="Token already exist", code="already_exist")],
        )
    status = await service.validate_token(token)
    if status:
        return await service.create_token(session, token)
    raise errors.ApiHTTPException(
        status_code=400,
        detail=[errors.ApiException(msg="Token is not valid", code="not_valid")],
    )


@router.delete("/api_layer_currency", response_model=models.CurrencyTokenRead)
async def remove_api_layer_currency_token(
    token: str,
    _=Depends(auth_flows.current_active_superuser),
    session=Depends(db.get_async_session),
):
    return await service.delete_token(session, token)
