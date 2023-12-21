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
    MESSAGES = "✉️ Messages"
    CHANNELS = "✉️ Channels"
    RENDER = "✉️ Message Render"
    ACCOUNTING = "📊 Accounting"
    ADMIN = "🤷🏿‍♀️‍ Admin"
    CURRENCY = "💰 Currency"
    ORDER_RENDERS = "📒 Order Renders"
    SCREENSHOTS = "📷 Screenshots"

    DISCORD_OAUTH = "🤷🏿‍♀️‍ Discord OAuth"


class Integration(StrEnum):
    discord = "discord"
    telegram = "telegram"
