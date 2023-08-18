from app.services.auth.service import fastapi_users, auth_backend_db
from app.services.auth.models import UserRead, UserCreate

from fastapi import APIRouter


from app.core.enums import RouteTag


router = APIRouter(prefix="/auth", tags=[RouteTag.AUTH])

router.include_router(fastapi_users.get_auth_router(auth_backend_db))
router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))
router.include_router(fastapi_users.get_reset_password_router())
router.include_router(fastapi_users.get_verify_router(UserRead))
