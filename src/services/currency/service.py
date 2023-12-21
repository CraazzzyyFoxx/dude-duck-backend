from datetime import UTC, datetime

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src import models
from src.core import errors
from src.services.integrations.sheets import service as sheets_service
from src.services.settings import service as settings_service

_CACHE: dict[int, list[models.CurrencyToken]] = {}


client = httpx.AsyncClient(
    base_url="https://api.apilayer.com",
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
)


async def get_tokens(session: AsyncSession) -> list[models.CurrencyToken]:
    if _CACHE.get(0):
        return _CACHE[0]
    result = await session.scalars(sa.select(models.CurrencyToken))
    tokens = result.all()
    _CACHE[0] = tokens  # type: ignore
    return tokens  # type: ignore


async def create_token(session: AsyncSession, token: str) -> models.CurrencyToken:
    for token_db in await get_tokens(session):
        if token_db.token == token:
            raise errors.ApiHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=[errors.ApiException(msg="This token already exists", code="already_exist")],
            )

    model = models.CurrencyToken(token=token, uses=1, last_use=datetime.now(UTC))
    session.add(model)
    await session.commit()
    _CACHE.clear()
    return model


async def delete_token(session: AsyncSession, token: str) -> models.CurrencyToken:
    x = None
    for token_db in await get_tokens(session):
        if token_db.token == token:
            x = token_db
    if x is None:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.ApiException(msg="Token not found", code="not_exist")],
        )
    await session.delete(x)
    await session.commit()
    _CACHE.clear()
    return x


async def get(session: AsyncSession, currency_id: int) -> models.Currency | None:
    result = await session.scalars(sa.select(models.Currency).where(models.Currency.id == currency_id))
    return result.first()


async def create(session: AsyncSession, currency_in: models.CurrencyApiLayer) -> models.Currency:
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
    currency = models.Currency(date=currency_in.date, timestamp=currency_in.timestamp, quotes=quotes)
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


async def get_token(session: AsyncSession) -> models.CurrencyToken:
    tokens = await get_tokens(session)
    token = tokens[0]
    for t in tokens:
        if t.uses < token.uses:
            token = t
    return token


async def used_token(session: AsyncSession, token: models.CurrencyToken) -> None:
    tokens = await get_tokens(session)
    for t in tokens:
        if t.token == token.token:
            t.last_use = datetime.now(UTC)
            t.uses += 1
            session.add(t)
            break
    await session.commit()


async def get_currency_historical(session: AsyncSession, date: datetime) -> models.CurrencyApiLayer:
    date_str = normalize_date(date)
    token = await get_token(session)
    headers = {"apikey": token.token}
    try:
        response = await client.request("GET", f"/currency_data/historical?date={date_str}", headers=headers)
    except Exception as e:
        raise errors.ApiHTTPException(
            status_code=500,
            detail=[errors.ApiException(msg="Api Layer is not responding", code="internal_error")],
        ) from e
    if response.status_code == 429:
        raise RuntimeError("API Layer currency request limit exceeded.")
    json = response.json()
    if json["success"] is False:
        if json["error"]["code"] == 302:
            raise errors.ApiHTTPException(
                status_code=400,
                detail=[errors.ApiException(msg="Invalid date", code="invalid_date")],
            )
        raise RuntimeError(json)
    await used_token(session, token)
    return models.CurrencyApiLayer.model_validate(json)


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
