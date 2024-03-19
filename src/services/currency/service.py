from datetime import UTC, datetime

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src import models, schemas
from src.core import errors, config
from src.services.integrations.sheets import service as sheets_service
from src.services.settings import service as settings_service

client = httpx.AsyncClient(
    base_url="https://api.currencyapi.com/v3",
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
)


async def create(session: AsyncSession, currency_in: schemas.CurrencyAPI) -> models.Currency:
    quotes = currency_in.normalize_quotes()
    settings = await settings_service.get(session)
    if (
        settings.collect_currency_wow_by_sheets
        and settings.currency_wow_spreadsheet is not None
        and settings.currency_wow_sheet_id is not None
        and settings.currency_wow_cell is not None
    ):
        creds = await sheets_service.get_first_superuser_token(session)
        if creds.token is not None:
            cell = sheets_service.get_cell(
                creds.token,
                settings.currency_wow_spreadsheet,
                settings.currency_wow_sheet_id,
                settings.currency_wow_cell,
            )
            quotes["WOW"] = float(cell)

        else:
            raise errors.ApiHTTPException(
                status_code=404,
                detail=[errors.ApiException(msg="Google token missing for first superuser", code="not_exist")],
            )
    else:
        quotes["WOW"] = settings.currency_wow
    currency = models.Currency(
        date=currency_in.date,
        timestamp=currency_in.meta.last_updated_at.timestamp(),
        quotes=quotes
    )
    session.add(currency)
    await session.commit()
    return currency


async def delete(session: AsyncSession, currency_id: int) -> None:
    await session.execute(sa.delete(models.Currency).where(models.Currency.id == currency_id))


async def get_by_date(session: AsyncSession, date: datetime) -> models.Currency | None:
    date = datetime(year=date.year, month=date.month, day=date.day)
    result = await session.scalars(sa.select(models.Currency).where(models.Currency.date == date).limit(1))
    currency = result.first()
    return currency


async def get_all(session: AsyncSession) -> list[models.Currency]:
    result = await session.scalars(sa.select(models.Currency))
    currencies = result.all()
    return list(currencies)


def normalize_date(date: datetime) -> str:
    return date.strftime("%Y-%m-%d")


async def get_currency_historical(date: datetime) -> schemas.CurrencyAPI:
    date_str = normalize_date(date)
    try:
        response = await client.request(
            "GET",
            f"/historical?apikey={config.app.currency_api_token}&currencies=&date={date_str}"
        )
    except Exception as e:
        raise errors.ApiHTTPException(
            status_code=500,
            detail=[errors.ApiException(msg="Api Layer is not responding", code="internal_error")],
        ) from e
    if response.status_code == 429:
        raise RuntimeError("API Layer currency request limit exceeded.")
    if response.status_code == 422:
        raise errors.ApiHTTPException(
            status_code=400,
            detail=[errors.ApiException(msg="Invalid date", code="invalid_date")],
        )
    json = response.json()
    json["date"] = date
    return schemas.CurrencyAPI.model_validate(json)


async def validate_token(token: str) -> bool:
    date = normalize_date(datetime.now(UTC))
    headers = {"apikey": token}
    response = await client.request("GET", f"/currency_data/historical?date={date}", headers=headers)
    if response.status_code != 200:
        raise errors.ApiHTTPException(
            status_code=400,
            detail=[errors.ApiException(msg=response.json(), code="invalid_token")],
        )
    else:
        return True
