from datetime import datetime, date

from . import service


async def get(currency_date: datetime | date):
    currency = await service.get_by_date(currency_date)
    if currency is None:
        data = await service.get_currency_historical(currency_date)
        await service.create(data)
        return await service.get_by_date(currency_date)
    return currency
