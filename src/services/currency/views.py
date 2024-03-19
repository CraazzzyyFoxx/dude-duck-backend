import datetime

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from lxml.builder import E, ElementMaker
from lxml.etree import tostring
from starlette.responses import Response

from src import models, schemas
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
