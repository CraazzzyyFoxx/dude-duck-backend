import datetime

import httpx
from beanie import PydanticObjectId
from fastapi import HTTPException

from app.services.settings import models as settings_models
from app.services.settings import service as settings_service

from . import models

client = httpx.AsyncClient(
    base_url='https://api.apilayer.com',
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
)


async def get(currency_id: PydanticObjectId) -> models.Currency | None:
    return await models.Currency.find_one({"_id": currency_id})


async def create(currency_in: models.CurrencyApiLayer):
    quotes = currency_in.normalize_quotes()
    quotes["WOW"] = (await settings_service.get()).currency_wow
    currency = models.Currency(
        date=currency_in.date,
        timestamp=currency_in.timestamp,
        quotes=quotes
    )
    return await currency.create()


async def delete(currency_id: PydanticObjectId):
    currency = await get(currency_id)
    await currency.delete()


async def get_by_date(date: datetime.datetime) -> models.Currency | None:
    date = datetime.datetime(year=date.year, month=date.month, day=date.day)
    return await models.Currency.find_one({"date": date})


async def get_all() -> list[models.Currency]:
    return await models.Currency.find({}).to_list()


def normalize_date(date: datetime):
    return date.strftime("%Y-%m-%d")


async def get_token():
    settings = await settings_service.get()
    token = settings.api_layer_currency[0]
    for t in settings.api_layer_currency:
        if t.uses < token.uses:
            token = t
    return token


async def used_token(token: settings_models.ApiLayerCurrencyToken):
    settings = await settings_service.get()
    for t in settings.api_layer_currency:
        if t.token == token.token:
            t.last_use = datetime.datetime.utcnow()
            t.uses += 1
    await settings.save_changes()


async def get_currency_historical(date: datetime) -> models.CurrencyApiLayer:
    date = normalize_date(date)
    token = await get_token()
    headers = {"apikey": token.token}
    response = await client.request("GET", f'/currency_data/historical?date={date}', headers=headers)
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
    response = await client.request("GET", f'/currency_data/historical?date={date}', headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail=[{"msg": response.json()}])
    else:
        return True
