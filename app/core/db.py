from datetime import datetime

from tortoise import Model, fields


class TimeStampMixin(Model):
    id: int = fields.BigIntField(pk=True)
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    updated_at: datetime | None = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True
