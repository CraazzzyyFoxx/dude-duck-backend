from enum import StrEnum

__all__ = ("RouteTag",)


class RouteTag(StrEnum):
    """Tags used to classify API routes"""

    USERS = "🤷🏿‍♀️‍ Users"
    ORDERS = "📒 Orders"
    SHEETS = "📊 Google Sheets"
    RESPONSES = "📩 Responses"
    AUTH = "🤷🏿‍♀️‍ Auth"
    MESSAGES = "✉️ Telegram Messages"
    CHANNELS = "✉️ Telegram Channels"
    ACCOUNTING = "📊 Accounting"
