import datetime

import httpx

from app.core import errors
from app.services.auth import service as auth_service
from app.services.settings import models as settings_models
from app.services.settings import service as settings_service
from app.services.sheets import service as sheets_service

from . import models

client = httpx.AsyncClient(
    base_url="https://api.apilayer.com",
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
)


async def get(currency_id: int) -> models.Currency | None:
    return await models.Currency.filter(id=currency_id).first()


async def create(currency_in: models.CurrencyApiLayer) -> models.Currency:
    quotes = currency_in.normalize_quotes()
    settings = await settings_service.get()
    if settings.collect_currency_wow_by_sheets:
        creds = await auth_service.get_first_superuser()
        if creds.google:
            cell = sheets_service.get_cell(
                creds.google,
                settings.currency_wow_spreadsheet,
                settings.currency_wow_sheet_id,
                settings.currency_wow_cell,
            )
            quotes["WOW"] = float(cell)

        else:
            raise errors.DudeDuckHTTPException(
                status_code=404,
                detail=[errors.DudeDuckException(msg="Google token missing for first superuser", code="not_exist")],
            )
    else:
        quotes["WOW"] = (await settings_service.get()).currency_wow
    return await models.Currency.create(date=currency_in.date, timestamp=currency_in.timestamp, quotes=quotes)


async def delete(currency_id: int) -> None:
    currency = await get(currency_id)
    if currency is not None:
        await currency.delete()


async def get_by_date(date: datetime.datetime) -> models.Currency | None:
    date = datetime.datetime(year=date.year, month=date.month, day=date.day)
    return await models.Currency.filter(date=date).first()


async def get_all() -> list[models.Currency]:
    return await models.Currency.all()


def normalize_date(date: datetime.datetime) -> str:
    return date.strftime("%Y-%m-%d")


async def get_token() -> settings_models.ApiLayerCurrencyToken:
    settings = await settings_service.get()
    token = settings.api_layer_currency[0]
    for t in settings.api_layer_currency:
        if t.uses < token.uses:
            token = t
    return token


async def used_token(token: settings_models.ApiLayerCurrencyToken) -> None:
    settings = await settings_service.get()
    for t in settings.api_layer_currency:
        if t.token == token.token:
            t.last_use = datetime.datetime.utcnow()
            t.uses += 1
    await settings.save()


async def get_currency_historical(date: datetime.datetime) -> models.CurrencyApiLayer:
    date_str = normalize_date(date)
    token = await get_token()
    headers = {"apikey": token.token}
    response = await client.request("GET", f"/currency_data/historical?date={date_str}", headers=headers)
    if response.status_code == 429:
        raise RuntimeError("API Layer currency request limit exceeded.")
    json = response.json()
    if json["success"] is False:
        raise RuntimeError(json)
    await used_token(token)
    return models.CurrencyApiLayer.model_validate(json)


async def validate_token(token: str) -> bool:
    date = normalize_date(datetime.datetime.utcnow())
    headers = {"apikey": token}
    response = await client.request("GET", f"/currency_data/historical?date={date}", headers=headers)
    if response.status_code != 200:
        raise errors.DudeDuckHTTPException(
            status_code=400, detail=[errors.DudeDuckException(msg=response.json(), code="invalid_token")]
        )
    else:
        return True
