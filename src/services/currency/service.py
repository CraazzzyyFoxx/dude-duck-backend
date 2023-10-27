import datetime

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import errors
from src.services.auth import service as auth_service
from src.services.settings import models as settings_models
from src.services.settings import service as settings_service
from src.services.sheets import service as sheets_service

from . import models

client = httpx.AsyncClient(
    base_url="https://api.apilayer.com",
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
)


async def get(session: AsyncSession, currency_id: int) -> models.Currency | None:
    result = await session.scalars(sa.select(models.Currency).where(models.Currency.id == currency_id))
    return result.first()


async def create(session: AsyncSession, currency_in: models.CurrencyApiLayer) -> models.Currency:
    quotes = currency_in.normalize_quotes()
    settings = await settings_service.get(session)
    if settings.collect_currency_wow_by_sheets:
        creds = await auth_service.get_first_superuser(session)
        if creds.google is not None:
            cell = sheets_service.get_cell(
                creds.google,
                settings.currency_wow_spreadsheet,
                settings.currency_wow_sheet_id,
                settings.currency_wow_cell,
            )
            quotes["WOW"] = float(cell)

        else:
            raise errors.DDHTTPException(
                status_code=404,
                detail=[errors.DDException(msg="Google token missing for first superuser", code="not_exist")],
            )
    else:
        quotes["WOW"] = settings.currency_wow
    currency = models.Currency(date=currency_in.date, timestamp=currency_in.timestamp, quotes=quotes)
    session.add(currency)
    await session.commit()
    return currency


async def delete(session: AsyncSession, currency_id: int) -> None:
    await session.execute(sa.delete(models.Currency).where(models.Currency.id == currency_id))


async def get_by_date(session: AsyncSession, date: datetime.datetime) -> models.Currency | None:
    date = datetime.datetime(year=date.year, month=date.month, day=date.day)
    result = await session.scalars(sa.select(models.Currency).where(models.Currency.date == date).limit(1))
    currency = result.first()
    return currency


async def get_all(session: AsyncSession) -> list[models.Currency]:
    result = await session.scalars(sa.select(models.Currency))
    currencies = result.all()
    return list(currencies)


def normalize_date(date: datetime.datetime) -> str:
    return date.strftime("%Y-%m-%d")


async def get_token(session: AsyncSession) -> settings_models.ApiLayerCurrencyToken:
    settings = await settings_service.get(session)
    token = settings.api_layer_currency[0]
    for t in settings.api_layer_currency:
        if t["uses"] < token["uses"]:
            token = t
    return token


async def used_token(session: AsyncSession, token: settings_models.ApiLayerCurrencyToken) -> None:
    settings = await settings_service.get(session)
    for t in settings.api_layer_currency:
        if t["token"] == token["token"]:
            t["last_uses"] = datetime.datetime.utcnow()
            t["uses"] += 1
    session.add(settings)
    await session.commit()


async def get_currency_historical(session: AsyncSession, date: datetime.datetime) -> models.CurrencyApiLayer:
    date_str = normalize_date(date)
    token = await get_token(session)
    headers = {"apikey": token["token"]}
    try:
        response = await client.request("GET", f"/currency_data/historical?date={date_str}", headers=headers)
    except Exception as e:
        raise errors.DDHTTPException(
            status_code=500, detail=[errors.DDException(msg="Api Layer is not responding", code="internal_error")]
        ) from e
    if response.status_code == 429:
        raise RuntimeError("API Layer currency request limit exceeded.")
    json = response.json()
    if json["success"] is False:
        raise RuntimeError(json)
    await used_token(session, token)
    return models.CurrencyApiLayer.model_validate(json)


async def validate_token(token: str) -> bool:
    date = normalize_date(datetime.datetime.utcnow())
    headers = {"apikey": token}
    response = await client.request("GET", f"/currency_data/historical?date={date}", headers=headers)
    if response.status_code != 200:
        raise errors.DDHTTPException(
            status_code=400, detail=[errors.DDException(msg=response.json(), code="invalid_token")]
        )
    else:
        return True
