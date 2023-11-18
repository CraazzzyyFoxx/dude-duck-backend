from fastapi import APIRouter, Body, Depends
from fastapi.responses import ORJSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from pydantic import EmailStr
from starlette import status

from src.core import enums, errors
from src.core.db import get_async_session
from src.services.telegram.message import service as message_service

from . import flows, models, service

router = APIRouter(prefix="/auth", tags=[enums.RouteTag.AUTH])


@router.post("/login")
async def login(credentials: OAuth2PasswordRequestForm = Depends(), session=Depends(get_async_session)):
    user = await service.authenticate(session, credentials)
    if user is None:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.ApiException(
                    msg=enums.ErrorCode.LOGIN_BAD_CREDENTIALS, code=enums.ErrorCode.LOGIN_BAD_CREDENTIALS
                )
            ],
        )
    token = await service.write_token(session, user)
    message_service.send_logged_notify(models.UserRead.model_validate(user))
    return ORJSONResponse({"access_token": token, "token_type": "bearer"})


# @router.post("/logout")
# async def logout(user_token: tuple[models.UserRead, str] = Depends(flows.current_user_token)):
#     user, token = user_token
#     return await service.logout(strategy, user, token)


@router.post("/register", response_model=models.UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_create: models.UserCreate, session=Depends(get_async_session)):
    created_user = await service.create(session, user_create, safe=True)
    logger.info(f"User {created_user.id} has registered.")
    user = models.UserRead.model_validate(created_user)
    # message_service.send_registered_notify(user)
    return user


@router.post("/request-verify-token", status_code=status.HTTP_202_ACCEPTED)
async def request_verify_token(email: EmailStr = Body(..., embed=True), session=Depends(get_async_session)):
    try:
        user = await flows.get_by_email(session, email.lower())
        await service.request_verify(user)
    except errors.ApiHTTPException:
        pass
    return None


@router.post("/verify", response_model=models.UserRead)
async def verify(token: str = Body(..., embed=True), session=Depends(get_async_session)):
    user = await service.verify(session, token)
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
async def reset_password(token: str = Body(...), password: str = Body(...), session=Depends(get_async_session)):
    await service.reset_password(session, token, password)
