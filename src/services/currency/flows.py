from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src import models
from src.services.settings import service as settings_service

from . import service


async def get(session: AsyncSession, currency_date: datetime) -> models.Currency:
    currency = await service.get_by_date(session, currency_date)
    if currency is None:
        data = await service.get_currency_historical(currency_date)
        currency = await service.create(session, data)
    return currency


async def usd_to_currency(
    session: AsyncSession,
    dollars: float,
    date: datetime,
    currency: str = "USD",
    *,
    with_round: bool = False,
    with_fee: bool = False,
) -> float:
    settings = await settings_service.get(session)
    if currency == "USD":
        price = dollars
    else:
        currency_db = await get(session, date)
        price = dollars * currency_db.quotes[currency]
    if with_fee:
        price *= settings.accounting_fee
    if with_round:
        return round(price, settings.get_precision(currency))
    return price


async def usd_to_currency_prefetched(
    session: AsyncSession,
    dollars: float,
    currency_db: models.Currency,
    currency: str = "USD",
    *,
    with_round: bool = False,
    with_fee: bool = False,
) -> float:
    settings = await settings_service.get(session)
    if currency == "USD":
        price = dollars
    else:
        price = dollars * currency_db.quotes[currency]
    if with_fee:
        price *= settings.accounting_fee
    if with_round:
        return round(price, settings.get_precision(currency))
    return price


async def currency_to_usd(
    session: AsyncSession,
    wallet: float,
    date: datetime,
    currency: str = "USD",
    *,
    with_round: bool = False,
    with_fee: bool = False,
) -> float:
    settings = await settings_service.get(session)
    if currency == "USD":
        price = wallet
    else:
        currency_db = await get(session, date)
        price = wallet / currency_db.quotes[currency]
    if with_fee:
        price *= settings.accounting_fee
    if with_round:
        return round(price, settings.get_precision(currency))
    else:
        return price
