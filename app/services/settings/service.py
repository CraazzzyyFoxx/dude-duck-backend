from starlette import status

from app.core import errors

from . import models

CACHE: dict[int, models.Settings] = {}


async def get() -> models.Settings:
    if CACHE.get(0):
        return CACHE[0]
    settings: models.Settings = await models.Settings.find_one({})
    CACHE[0] = settings  # type: ignore
    return settings


async def create() -> models.Settings:
    if await get() is None:
        settings = models.Settings()
        await settings.create()
    CACHE.clear()
    return await get()


async def update(user_order_in: models.SettingsUpdate) -> models.Settings:
    settings = await get()
    settings_data = settings.model_dump()
    update_data = user_order_in.model_dump(exclude_none=True)

    for field in settings_data:
        if field in update_data:
            setattr(settings, field, update_data[field])

    await settings.save_changes()
    CACHE.clear()
    return settings


async def add_token(token: str) -> models.Settings:
    settings = await get()

    for token_db in settings.api_layer_currency:
        if token_db.token == token:
            raise errors.DudeDuckHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=[errors.DudeDuckException(msg="This token already exists", code="already_exist")],
            )

    model = models.ApiLayerCurrencyToken(token=token, uses=1)
    settings.api_layer_currency.append(model)
    CACHE.clear()
    await settings.save_changes()
    return settings


async def remove_token(token: str) -> models.Settings:
    settings = await get()
    x = None
    for token_db in settings.api_layer_currency:
        if token_db.token == token:
            x = token_db
    if x is None:
        raise errors.DudeDuckHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[errors.DudeDuckException(msg="Token not found", code="not_exist")],
        )

    settings.api_layer_currency.remove(x)
    CACHE.clear()
    await settings.save_changes()
    return settings
