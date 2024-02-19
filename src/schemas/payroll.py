from pydantic import BaseModel, ConfigDict
from src.models.payroll import PayrollType

__all__ = ("PayrollRead", "PayrollCreate", "PayrollUpdate",)


class PayrollRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    bank: str
    type: PayrollType | str
    value: str


class PayrollCreate(BaseModel):
    type: PayrollType
    bank: str
    value: str


class PayrollUpdate(BaseModel):
    type: PayrollType
    bank: str
    value: str
