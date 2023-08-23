import contextlib

from beanie import PydanticObjectId
from fastapi_users import FastAPIUsers


from app.services.auth.manager import get_user_manager
from . import models, utils

fastapi_users = FastAPIUsers[models.User, PydanticObjectId](get_user_manager, [utils.auth_backend_api, utils.auth_backend_db])
current_active_user = fastapi_users.current_user(
    active=True,
    get_enabled_backends=utils.get_enabled_backends
)
current_active_superuser = fastapi_users.current_user(
    active=True,
    superuser=True,
    get_enabled_backends=utils.get_enabled_backends
)
current_active_verified = fastapi_users.current_user(
    active=True,
    verified=True,
    get_enabled_backends=utils.get_enabled_backends
)

current_active_superuser_api = fastapi_users.current_user(
    active=True,
    superuser=True,
    get_enabled_backends=utils.get_enabled_backends_api
)

get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)