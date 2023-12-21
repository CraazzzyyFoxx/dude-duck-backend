from fastapi import APIRouter, Body, Depends
from fastapi.responses import ORJSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from pydantic import EmailStr
from starlette import status

from src import models
from src.core import enums, errors
from src.core.db import get_async_session
from src.services.integrations.notifications import \
    flows as notifications_flows
from src.services.integrations.sheets import service as sheets_service
from src.services.tasks import service as tasks_service

from . import flows, service

router = APIRouter(prefix="/auth", tags=[enums.RouteTag.AUTH])


@router.post("/login")
async def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    session=Depends(get_async_session),
):
    user = await service.authenticate(session, credentials)
    if user is None:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[errors.ApiException(msg="LOGIN_BAD_CREDENTIALS", code="LOGIN_BAD_CREDENTIALS")],
        )
    token = await service.create_access_token(session, user)
    notifications_flows.send_logged_notify(models.UserRead.model_validate(user))
    return ORJSONResponse({"access_token": token[0], "refresh_token": token[1], "token_type": "bearer"})


@router.post("/register", response_model=models.UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_create: models.UserCreate, session=Depends(get_async_session)):
    created_user = await service.create(session, user_create, safe=True)
    logger.info(f"User {created_user.id} has registered.")
    user = models.UserRead.model_validate(created_user)
    notifications_flows.send_registered_notify(user)
    parser = await sheets_service.get_default_booster_read(session)
    tasks_service.create_booster.delay(
        parser.model_dump_json(),
        user.model_dump(),
    )
    return user


@router.post("/request-verify-token", status_code=status.HTTP_202_ACCEPTED)
async def request_verify_token(email: EmailStr = Body(..., embed=True), session=Depends(get_async_session)):
    try:
        user = await flows.get_by_email(session, email.lower())
        await service.request_verify_email(session, user)
    except errors.ApiHTTPException:
        pass
    return None


@router.post("/verify", response_model=models.UserRead)
async def verify(token: str = Body(..., embed=True), session=Depends(get_async_session)):
    user = await service.verify_email(session, token)
    return models.UserRead.model_validate(user, from_attributes=True)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(email: EmailStr = Body(..., embed=True), session=Depends(get_async_session)):
    try:
        user = await flows.get_by_email(session, email.lower())
        await service.forgot_password(user)
    except errors.ApiHTTPException:
        pass
    return None


@router.post("/reset-password")
async def reset_password(
    token: str = Body(...),
    password: str = Body(...),
    session=Depends(get_async_session),
):
    await service.reset_password(session, token, password)


@router.post("/refresh-token")
async def refresh_token(token: str = Body(..., embed=True), session=Depends(get_async_session)):
    tokens = await service.refresh_tokens(session, token)
    return ORJSONResponse({"access_token": tokens[0], "refresh_token": tokens[1], "token_type": "bearer"})
