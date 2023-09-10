from app.services.auth.models import User, AccessToken, AccessTokenAPI
from app.services.sheets.models import OrderSheetParse
from app.services.orders.models import Order
from app.services.accounting.models import UserOrder
from app.services.response.models import Response
from app.services.preorders.models import PreOrder
from app.services.settings.models import Settings
from app.services.currency.models import Currency


def get_beanie_models():
    return [User, AccessToken, AccessTokenAPI, Order,
            OrderSheetParse, UserOrder, Response, PreOrder, Settings, Currency]
