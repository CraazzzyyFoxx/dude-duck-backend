from starlette.requests import Request

from src.core import enums


async def get_integration(request: Request) -> enums.Integration:
    user_agent = request.headers.get("User-Agent")
    if user_agent == "DiscordBot":
        integration = enums.Integration.discord
    elif user_agent == "TelegramBot":
        integration = enums.Integration.telegram
    else:
        integration = enums.Integration.web

    return integration
