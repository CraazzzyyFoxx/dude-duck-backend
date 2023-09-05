from enum import StrEnum

__all__ = ("RouteTag",)


class RouteTag(StrEnum):
    """Tags used to classify API routes"""

    SETTINGS = "⚙️ Settings"

    USERS = "🤷🏿‍♀️‍ Users"
    ORDERS = "📒 Orders"
    PREORDERS = "📒 Pre Orders"
    SHEETS = "📊 Google Sheets"
    RESPONSES = "📩 Responses"
    AUTH = "🤷🏿‍♀️‍ Auth"
    MESSAGES = "✉️ Telegram Messages"
    CHANNELS = "✉️ Telegram Channels"
    RENDER = "✉️ Telegram Message Render"
    ACCOUNTING = "📊 Accounting"
