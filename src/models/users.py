from src.models.auth import UserRead
from src.models.integrations.telegram import TelegramAccountRead


__all__ = ("UserReadWithAccounts",)


class UserReadWithAccounts(UserRead):
    telegram: TelegramAccountRead
