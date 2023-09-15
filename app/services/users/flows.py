from fastapi import Depends, HTTPException
from fastapi_users import exceptions
from fastapi_users.router import ErrorCode
from starlette import status
from starlette.requests import Request

from app.services.auth import flows as auth_flows
from app.services.auth import manager as auth_manager
from app.services.auth import models as auth_models
from app.services.auth import service as auth_service


async def update_user(
        request: Request,
        user_update: auth_models.schemas.BaseUserUpdate,
        user: auth_models.User,
        user_manager: auth_manager.UserManager = Depends(auth_flows.get_user_manager)
) -> auth_models.UserRead:
    try:
        user = await user_manager.update(
            user_update, user, safe=True, request=request
        )
        return auth_service.models.UserRead.model_validate(user, from_attributes=True)
    except exceptions.InvalidPasswordException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCode.UPDATE_USER_INVALID_PASSWORD,
                "reason": e.reason,
            },
        )
    except exceptions.UserAlreadyExists:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.UPDATE_USER_EMAIL_ALREADY_EXISTS,
        )
