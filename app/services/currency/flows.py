from datetime import datetime

from app.services.settings import service as settings_service

from . import models, service


async def get(currency_date: datetime) -> models.Currency:
    currency = await service.get_by_date(currency_date)
    if currency is None:
        data = await service.get_currency_historical(currency_date)
        await service.create(data)
        return await service.get_by_date(currency_date)
    return currency


async def usd_to_currency(
        dollars: float,
        date: datetime,
        currency: str = "USD",
        *,
        with_round: bool = False,
        with_fee: bool = False
) -> float:
    settings = await settings_service.get()
    if currency == "USD":
        price = dollars
    else:
        currency_db = await get(date)
        price = dollars * currency_db.quotes[currency]
    if with_fee:
        price *= settings.accounting_fee
    if with_round:
        return round(price, settings.get_precision(currency))
    else:
        return price


async def currency_to_usd(
        wallet: float,
        date: datetime,
        currency: str = "USD",
        *,
        with_round: bool = False,
        with_fee: bool = False
) -> float:
    settings = await settings_service.get()
    if currency == "USD":
        price = wallet
    else:
        currency_db = await get(date)
        price = wallet / currency_db.quotes[currency]
    if with_fee:
        price *= settings.accounting_fee
    if with_round:
        return round(price, settings.get_precision(currency))
    else:
        return price
