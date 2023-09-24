from datetime import datetime

from beanie import Document, PydanticObjectId, Replace, after_event
from pydantic import ConfigDict, Field


class TimeStampMixin(Document):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId | None = Field(default=None, description="MongoDB document ObjectID")  # type: ignore
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    @after_event(Replace)
    def updated_at_on_save(self):
        self.updated_at = datetime.utcnow()
