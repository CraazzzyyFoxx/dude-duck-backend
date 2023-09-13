from fastapi import APIRouter

from app.core.enums import RouteTag

from . import flows, models, utils

router = APIRouter(prefix="/auth", tags=[RouteTag.AUTH])

router.include_router(flows.fastapi_users.get_auth_router(utils.auth_backend_db))
router.include_router(flows.fastapi_users.get_register_router(models.UserRead, models.UserCreate))
router.include_router(flows.fastapi_users.get_reset_password_router())
router.include_router(flows.fastapi_users.get_verify_router(models.UserRead))
