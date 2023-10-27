from fastapi import APIRouter

from src.services.accounting.views import router as accounting_router
from src.services.admin.views import router as admin_router
from src.services.auth.views import router as auth_router
from src.services.orders.views import router as orders_router
from src.services.preorders.views import router as preorders_router
from src.services.response.views import router as response_router
from src.services.settings.views import router as settings_router
from src.services.sheets.views import router as sheets_router
from src.services.telegram.views import router as telegram_router
from src.services.users.views import router as users_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(settings_router)
router.include_router(admin_router)
router.include_router(users_router)
router.include_router(orders_router)
router.include_router(preorders_router)
router.include_router(response_router)
router.include_router(accounting_router)
router.include_router(sheets_router)
router.include_router(telegram_router)
