from datetime import datetime

from beanie import Document, Replace, after_event
from pydantic import Field


class TimeStampMixin(Document):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    @after_event(Replace)
    def updated_at_on_save(self):
        self.updated_at = datetime.utcnow()
