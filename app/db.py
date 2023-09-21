from app.services.accounting.models import UserOrder
from app.services.auth.models import AccessToken, AccessTokenAPI, User
from app.services.currency.models import Currency
from app.services.orders.models import Order
from app.services.preorders.models import PreOrder
from app.services.response.models import Response
from app.services.settings.models import Settings
from app.services.sheets.models import OrderSheetParse


def get_beanie_models() -> list:
    return [
        User,
        AccessToken,
        AccessTokenAPI,
        Order,
        OrderSheetParse,
        UserOrder,
        Response,
        PreOrder,
        Settings,
        Currency,
    ]
