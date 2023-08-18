import datetime

from beanie import Document
from pydantic import Field, BaseModel

__all__ = (
    "PreOrderMeta",
    "PreOrder",
)


class PreOrderMeta(BaseModel):
    order_id: str | None = None
    date: datetime.datetime | None = None
    exchange: float | None = None
    boost_type: str | None = None
    character_class: str | None = None
    game: str | None = None
    purchase: str | None = None
    comment: str | None = None

    price_dollar: float | None = None
    price_booster_dollar: float | None = None
    price_booster_dollar_fee: float | None = None
    price_booster_rub: float | None = None
    price_booster_gold: float | None = None

    info: dict = Field(default={})


class PreOrder(Document, PreOrderMeta):
    boost_type: str
    character_class: str | None = None
    game: str
    purchase: str
    comment: str | None = None

    price_dollar: float | None = None
    price_booster_dollar: float | None = None
    price_booster_dollar_fee: float | None = None
    price_booster_rub: float | None = None
    price_booster_gold: float | None = None

    eta: str | None = None

    info: dict = Field(default={})
