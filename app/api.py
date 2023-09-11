from fastapi import APIRouter

from app.services.auth.views import router as auth_router
from app.services.sheets.views import router as sheets_router
from app.services.orders.views import router as orders_router
from app.services.preorders.views import router as preorders_router
from app.services.accounting.views import router as accounting_router
from app.services.response.views import router as response_router
from app.services.users.views import router as users_router
from app.services.telegram.views import router as telegram_router
from app.services.settings.views import router as settings_router


router = APIRouter()
router.include_router(auth_router)

api_router = APIRouter()
api_router.include_router(settings_router)
api_router.include_router(users_router)
api_router.include_router(orders_router)
api_router.include_router(preorders_router)
api_router.include_router(response_router)
api_router.include_router(accounting_router)
api_router.include_router(sheets_router)
api_router.include_router(telegram_router)

router.include_router(api_router)
