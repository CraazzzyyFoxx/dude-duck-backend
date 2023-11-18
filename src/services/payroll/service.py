import sqlalchemy as sa
from pydantic import BaseModel, EmailStr
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.core import errors, pagination
from src.services.auth import models as auth_models

from . import models

payroll_priority: dict[models.PayrollType, int] = {
    models.PayrollType.binance_id: 1,
    models.PayrollType.binance_email: 2,
    models.PayrollType.trc20: 3,
    models.PayrollType.phone: 4,
    models.PayrollType.card: 5,
}


class PayrollValidator(BaseModel):
    binance_email: EmailStr | None = None
    binance_id: int | None = None
    trc20: str | None = None
    phone: PhoneNumber | None = None
    card: PaymentCardNumber | None = None

    @property
    def value(self) -> str:
        if self.binance_email:
            return self.binance_email
        if self.binance_id:
            return str(self.binance_id)
        if self.trc20:
            return self.trc20
        if self.phone:
            return str(self.phone).replace("tel:", "")
        if self.card:
            return str(self.card)


def validate_payroll(name: models.PayrollType, value: str) -> PayrollValidator:
    if name == models.PayrollType.binance_email:
        return PayrollValidator(binance_email=value)
    if name == models.PayrollType.binance_id:
        if value.isdigit():
            return PayrollValidator(binance_id=int(value))
    if name == models.PayrollType.trc20:
        return PayrollValidator(trc20=value)
    if name == models.PayrollType.phone:
        return PayrollValidator(phone=value)  # type: ignore
    if name == models.PayrollType.card:
        return PayrollValidator(card=value)  # type: ignore
    raise errors.ApiHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=[errors.ApiException(msg=f"Invalid payroll type. [name={name}]", code="bad_request")],
    )


async def get(session: AsyncSession, payroll_id: int) -> models.Payroll | None:
    query = sa.select(models.Payroll).where(models.Payroll.id == payroll_id)
    result = await session.execute(query)
    return result.scalars().first()


async def get_by_user_id(session: AsyncSession, user_id: int) -> list[models.Payroll]:
    query = sa.select(models.Payroll).where(models.Payroll.user_id == user_id)
    result = await session.execute(query)
    return result.scalars().all()  # type: ignore


async def create(session: AsyncSession, user: auth_models.User, payroll_in: models.PayrollCreate) -> models.Payroll:
    query = sa.select(models.Payroll).filter_by(user_id=user.id, type=payroll_in.type)
    result = await session.execute(query)
    if result.scalars().first():
        raise errors.ApiHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                errors.ApiException(
                    msg=f"A payroll with this name already exist. [name={payroll_in.type}]", code="already_exist"
                )
            ],
        )
    payroll = models.Payroll(
        user_id=user.id,
        type=payroll_in.type,
        bank=payroll_in.bank,
        value=validate_payroll(payroll_in.type, payroll_in.value).value,
    )
    session.add(payroll)
    await session.commit()
    return payroll


async def update(session: AsyncSession, payroll_id: int, model: models.PayrollUpdate) -> models.Payroll:
    payroll = await get(session, payroll_id)
    if not payroll:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg=f"A payroll with this id does not exist. [payroll_id={payroll_id}]", code="not_exist"
                )
            ],
        )
    payroll.type = model.type
    payroll.bank = model.bank
    payroll.value = validate_payroll(model.type, model.value).value
    await session.commit()
    return payroll


async def delete(session: AsyncSession, payroll_id: int) -> models.Payroll:
    payroll = await get(session, payroll_id)
    if not payroll:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg=f"A payroll with this id does not exist. [payroll_id={payroll_id}]", code="not_exist"
                )
            ],
        )
    await session.delete(payroll)
    await session.commit()
    return payroll


async def get_by_filter(
    session: AsyncSession, user: auth_models.User, params: pagination.PaginationParams
) -> pagination.Paginated[models.PayrollRead]:
    query = sa.select(models.Payroll).where(models.Payroll.user_id == user.id)
    query = params.apply_pagination(query)
    result = await session.execute(query)
    results = [models.PayrollRead.model_validate(payroll, from_attributes=True) for payroll in result.scalars().all()]
    total = await session.scalars(sa.select(sa.func.count(models.Payroll.id)).where(models.Payroll.user_id == user.id))
    return pagination.Paginated(results=results, total=total.one(), page=params.page, per_page=params.per_page)


async def get_by_priority(session: AsyncSession, user: auth_models.User) -> models.PayrollRead:
    query = sa.select(models.Payroll).where(models.Payroll.user_id == user.id)
    result = await session.execute(query)
    payroll = models.PayrollRead(user_id=user.id, type="Хуй знает", value="Хуй знает", bank="Хуй знает")
    priority = 100
    for row in result.scalars().all():
        if payroll.type == "Хуй знает" or payroll_priority[row.type] < priority:
            payroll.type = row.type.value
            payroll.value = row.value
            payroll.bank = row.bank
            priority = payroll_priority[row.type]
    return payroll
