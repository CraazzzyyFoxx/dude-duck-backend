from src.schemas.integrations.telegram import TelegramAccountRead

__all__ = ("UserReadWithAccounts", "UserReadWithPayrolls", "UserReadWithAccountsAndPayrolls")

from src.schemas.auth import UserRead
from src.schemas.payroll import PayrollRead


class UserReadWithAccounts(UserRead):
    telegram: TelegramAccountRead | None = None


class UserReadWithPayrolls(UserRead):
    payrolls: list[PayrollRead]


class UserReadWithAccountsAndPayrolls(UserRead):
    telegram: TelegramAccountRead | None = None
    payrolls: list[PayrollRead]
