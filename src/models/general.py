from pydantic import BaseModel


__all__ = ("SheetEntity",)

class SheetEntity(BaseModel):
    spreadsheet: str
    sheet_id: int
    row_id: int