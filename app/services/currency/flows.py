from datetime import datetime

from . import models, service


async def get(date: datetime):
    currency = await service.get_by_date(date)
    if currency is None:
        data = await service.get_currency_historical(date)
        await service.create(data)
        return await service.get_by_date(date)
    return currency
