from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import models as auth_models
from src.services.auth import service as auth_service


async def update_user(
    session: AsyncSession, user_update: auth_models.BaseUserUpdate, user: auth_models.User
) -> auth_models.UserRead:
    user = await auth_service.update(session, user, user_update, safe=True, exclude=False, with_sync=False)
    return auth_models.UserRead.model_validate(user, from_attributes=True)
