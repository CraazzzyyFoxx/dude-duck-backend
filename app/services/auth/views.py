from fastapi import APIRouter, Body, Depends
from fastapi.responses import ORJSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from pydantic import EmailStr
from starlette import status

from app.core import enums, errors
from app.services.telegram.message import service as message_service

from . import flows, models, service

router = APIRouter(prefix="/auth", tags=[enums.RouteTag.AUTH])


@router.post("/login")
async def login(credentials: OAuth2PasswordRequestForm = Depends()):
    user = await service.authenticate(credentials)
    token = await service.write_token(user)
    message_service.send_logged_notify(models.UserRead.model_validate(user))
    return ORJSONResponse({"access_token": token, "token_type": "bearer"})


# @router.post("/logout")
# async def logout(user_token: tuple[models.UserRead, str] = Depends(flows.current_user_token)):
#     user, token = user_token
#     return await service.logout(strategy, user, token)


@router.post("/register", response_model=models.UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_create: models.UserCreate):
    created_user = await service.create(user_create, safe=True)
    logger.info(f"User {created_user.id} has registered.")
    user = models.UserRead.model_validate(created_user)
    message_service.send_registered_notify(user)
    return user


@router.post("/request-verify-token", status_code=status.HTTP_202_ACCEPTED)
async def request_verify_token(
    email: EmailStr = Body(..., embed=True),
):
    try:
        user = await flows.get_by_email(email)
        await service.request_verify(user)
    except errors.DudeDuckHTTPException:
        pass
    return None


@router.post("/verify", response_model=models.UserRead)
async def verify(
    token: str = Body(..., embed=True),
):
    user = await service.verify(token)
    return models.UserRead.model_validate(user, from_attributes=True)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(email: EmailStr = Body(..., embed=True)):
    try:
        user = await flows.get_by_email(email)
        await service.forgot_password(user)
    except errors.DudeDuckHTTPException:
        pass
    return None


@router.post("/reset-password")
async def reset_password(token: str = Body(...), password: str = Body(...)):
    await service.reset_password(token, password)
