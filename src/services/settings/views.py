from fastapi import APIRouter, Depends

from src import models
from src.core import enums
from src.core.db import get_async_session
from src.services.auth import flows as auth_flows

from . import service

router = APIRouter(
    prefix="/settings",
    tags=[enums.RouteTag.SETTINGS],
    dependencies=[Depends(auth_flows.current_active_superuser)],
)


@router.get("", response_model=models.SettingsRead)
async def read_settings(session=Depends(get_async_session)):
    return await service.get(session)


@router.patch("", response_model=models.SettingsRead)
async def update_settings(data: models.SettingsUpdate, session=Depends(get_async_session)):
    return await service.update(session, data)
