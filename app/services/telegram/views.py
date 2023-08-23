from fastapi import APIRouter

from .channel import views as channel_views
from .message import views as message_views

router = APIRouter(prefix="/telegram")

router.include_router(channel_views.router)
router.include_router(message_views.router)