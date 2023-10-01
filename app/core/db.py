import typing
from datetime import datetime

from tortoise import Model, fields
from tortoise.signals import pre_save


class TimeStampMixin(Model):
    id: int = fields.BigIntField(pk=True)
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    updated_at: datetime | None = fields.DatetimeField(null=True)


@pre_save(TimeStampMixin)
async def signal_pre_save(
        sender: typing.Type[TimeStampMixin], instance: TimeStampMixin, using_db, update_fields) -> None:
    sender.updated_at = datetime.utcnow()
