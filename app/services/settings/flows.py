from app.services.currency import service as currency_service

from . import service


async def add_api_layer_currency_token(token: str) -> None:
    status = await currency_service.validate_token(token)
    if status:
        await service.add_token(token)
