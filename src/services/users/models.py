from src.services.auth import models as auth_models
from src.services.payroll import models as payroll_models


class UserReadWithPayrolls(auth_models.UserRead):
    payrolls: list[payroll_models.PayrollRead]
