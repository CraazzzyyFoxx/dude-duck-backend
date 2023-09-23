from app.services.auth import models as auth_models
from app.services.auth import service as auth_service


async def update_user(user_update: auth_models.UserUpdate, user: auth_models.User) -> auth_models.UserRead:
    user = await auth_service.update(user, user_update, safe=True)
    return auth_service.models.UserRead.model_validate(user, from_attributes=True)
