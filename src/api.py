from fastapi import APIRouter

from src.services.accounting.views import router as accounting_router
from src.services.admin.views import router as admin_router
from src.services.auth.views import router as auth_router
from src.services.currency.views import router as currency_router
from src.services.integrations.channel.views import router as channel_router
from src.services.integrations.message.views import router as message_router
from src.services.integrations.render.views import router as render_router
from src.services.integrations.sheets.views import router as sheets_router
from src.services.order.views import router as orders_router
from src.services.preorder.views import router as preorders_router
from src.services.response.views import router as response_router
from src.services.screenshot.views import router as screenshot_router
from src.services.settings.views import router as settings_router
from src.services.users.views import router as users_router

router = APIRouter()
router.include_router(settings_router)
router.include_router(currency_router)
router.include_router(auth_router)
router.include_router(orders_router)
router.include_router(preorders_router)
router.include_router(screenshot_router)
router.include_router(accounting_router)
router.include_router(response_router)
router.include_router(admin_router)
router.include_router(users_router)
router.include_router(sheets_router)
router.include_router(render_router)
router.include_router(channel_router)
router.include_router(message_router)
