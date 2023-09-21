from fastapi import APIRouter, Depends

from app.core import enums
from app.services.auth import flows as auth_flows
from app.services.auth import models as auth_models

from . import flows, models, service

router = APIRouter(prefix="/settings", tags=[enums.RouteTag.SETTINGS])


@router.get("/", response_model=models.SettingsRead)
async def read_settings(_: auth_models.User = Depends(auth_flows.current_active_superuser)):
    return await service.get()


@router.patch("/", response_model=models.SettingsRead)
async def update_settings(
    data: models.SettingsUpdate, _: auth_models.User = Depends(auth_flows.current_active_superuser)
):
    return await service.update(data)


@router.post("/api_layer_currency", response_model=models.SettingsRead)
async def add_api_layer_currency_token(token: str, _: auth_models.User = Depends(auth_flows.current_active_superuser)):
    await flows.add_api_layer_currency_token(token)
    return await service.get()


@router.delete("/api_layer_currency", response_model=models.SettingsRead)
async def remove_api_layer_currency_token(
    token: str, _: auth_models.User = Depends(auth_flows.current_active_superuser)
):
    await service.remove_token(token)
    return await service.get()
