from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


from src import schemas

__all__ = (
    "PreOrderPriceUser",
    "PreOrderPriceSystem",
    "PreOrderCreate",
    "PreOrderUpdate",
    "PreOrderReadSystem",
    "PreOrderReadUser",
)

from src.models.general import SheetEntity


class PreOrderPriceMeta(BaseModel):
    booster_dollar_fee: float | None = None
    booster_dollar: float | None = None
    booster_gold: float | None = None


class PreOrderPriceNone(PreOrderPriceMeta):
    dollar: float | None = None


class PreOrderPriceUser(PreOrderPriceMeta):
    booster_rub: float | None = None


class PreOrderPriceSystem(PreOrderPriceNone):
    booster_rub: float | None = None


class PreOrderCreate(SheetEntity):
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    order_id: str

    info: schemas.OrderInfoRead
    price: schemas.OrderPriceNone


class PreOrderUpdate(BaseModel):
    info: schemas.OrderInfoRead | None = None
    price: PreOrderPriceNone | None = None
    has_response: bool | None = None


class PreOrderReadSystem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str
    date: datetime

    info: schemas.OrderInfoRead
    price: PreOrderPriceSystem


class PreOrderReadUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str

    info: schemas.OrderInfoRead
    price: PreOrderPriceUser
