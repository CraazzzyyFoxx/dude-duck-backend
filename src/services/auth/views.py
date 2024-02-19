from fastapi import APIRouter, Body, Depends
from fastapi.responses import ORJSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src import schemas
from src.utils import get_integration
from src.core import enums, errors
from src.core.db import get_async_session
from src.services.integrations.notifications import flows as notifications_flows
from src.services.integrations.sheets import service as sheets_service
from src.services.tasks import service as tasks_service

from . import flows, service

router = APIRouter(prefix="/auth", tags=[enums.RouteTag.AUTH])


@router.post("/login")
async def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session),
    integration: enums.Integration = Depends(get_integration),
):
    user = await service.authenticate(session, credentials)
    if user is None:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[errors.ApiException(msg="LOGIN_BAD_CREDENTIALS", code="LOGIN_BAD_CREDENTIALS")],
        )
    token = await service.create_access_token(session, user)
    user_read = schemas.UserRead.model_validate(user, from_attributes=True)
    notifications_flows.send_logged_notify(
        await notifications_flows.get_user_accounts(session, user_read),
        integration,
    )
    logger.info(f"User [email={user.email} name={user.name}] has logged in.")
    return ORJSONResponse({"access_token": token[0], "refresh_token": token[1], "token_type": "bearer"})


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: schemas.UserCreate,
    session: AsyncSession = Depends(get_async_session),
    integration: enums.Integration = Depends(get_integration),
):
    created_user = await service.create(session, user_create, safe=True)
    user = schemas.UserRead.model_validate(created_user)
    logger.info(f"User [email={user.email} name={user.name}] has registered.")
    notifications_flows.send_registered_notify(await notifications_flows.get_user_accounts(session, user), integration)
    parser = await sheets_service.get_default_booster_read(session)
    tasks_service.create_user.delay(parser.model_dump(mode="json"), user.model_dump())
    return user


@router.post("/request-verify-token", status_code=status.HTTP_202_ACCEPTED)
async def request_verify_token(email: EmailStr = Body(..., embed=True), session=Depends(get_async_session)):
    try:
        user = await flows.get_by_email(session, email.lower())
        await service.request_verify_email(session, user)
    except errors.ApiHTTPException:
        pass
    return None


@router.post("/verify", response_model=schemas.UserRead)
async def verify(token: str = Body(..., embed=True), session=Depends(get_async_session)):
    user = await service.verify_email(session, token)
    return schemas.UserRead.model_validate(user, from_attributes=True)


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
