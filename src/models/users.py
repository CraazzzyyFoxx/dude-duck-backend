from src.models.auth import UserRead
from src.models.integrations.telegram import TelegramAccountRead
from src.models.payroll import PayrollRead

__all__ = ("UserReadWithAccounts", "UserReadWithPayrolls", "UserReadWithAccountsAndPayrolls")


class UserReadWithAccounts(UserRead):
    telegram: TelegramAccountRead | None = None


class UserReadWithPayrolls(UserRead):
    payrolls: list[PayrollRead]


class UserReadWithAccountsAndPayrolls(UserRead):
    telegram: TelegramAccountRead | None = None
    payrolls: list[PayrollRead]
