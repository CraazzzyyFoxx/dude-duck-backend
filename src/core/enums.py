from enum import StrEnum


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
    TELEGRAM_CHANNELS = "✉️ Telegram Channels"
    CHANNELS = "✉️ Channels"
    RENDER = "✉️ Telegram Message Render"
    ACCOUNTING = "📊 Accounting"
    ADMIN = "🤷🏿‍♀️‍ Admin"
    CURRENCY = "💰 Currency"
    ORDER_RENDERS = "📒 Order Renders"


class Integration(StrEnum):
    discord = "discord"
    telegram = "telegram"
