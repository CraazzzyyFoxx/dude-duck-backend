import enum
import typing

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core import db
from src.services.auth import models as auth_models


class PayrollType(str, enum.Enum):
    binance_email = "Binance Email"
    binance_id = "Binance ID"
    trc20 = "TRC 20"
    phone = "Phone"
    card = "Card"


class Payroll(db.TimeStampMixin):
    __tablename__ = "payroll"
    __table_args__ = (UniqueConstraint("user_id", "bank", "type", name="unique_user_payroll"),)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped[auth_models.User] = relationship()
    bank: Mapped[str] = mapped_column(String())
    type: Mapped[PayrollType] = mapped_column(Enum(PayrollType))
    value: Mapped[str] = mapped_column(String(), nullable=False)


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
