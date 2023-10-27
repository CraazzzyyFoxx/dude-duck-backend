from fastapi import APIRouter, Depends

from src.core import enums
from src.services.auth import flows as auth_flows

from src.core.db import get_async_session
from . import flows, models, service


router = APIRouter(
    prefix="/settings", tags=[enums.RouteTag.SETTINGS], dependencies=[Depends(auth_flows.current_active_superuser)]
)


@router.get("/", response_model=models.SettingsRead)
async def read_settings(session=Depends(get_async_session)):
    return await service.get(session)


@router.patch("/", response_model=models.SettingsRead)
async def update_settings(data: models.SettingsUpdate, session=Depends(get_async_session)):
    return await service.update(session, data)


@router.post("/api_layer_currency", response_model=models.SettingsRead)
async def add_api_layer_currency_token(token: str, session=Depends(get_async_session)):
    await flows.add_api_layer_currency_token(session, token)
    return await service.get(session)


@router.delete("/api_layer_currency", response_model=models.SettingsRead)
async def remove_api_layer_currency_token(token: str, session=Depends(get_async_session)):
    await service.remove_token(session, token)
    return await service.get(session)
