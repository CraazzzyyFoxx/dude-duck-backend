import typing

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError
from starlette import status


status_map = {
    status.HTTP_404_NOT_FOUND: "not found",
    status.HTTP_400_BAD_REQUEST: "already exist"
}


class ValidationErrorDetail(BaseModel):
    location: str
    message: str
    error_type: str
    context: dict[str, typing.Any] | None = None


class APIValidationError(BaseModel):
    errors: list[ValidationErrorDetail]

    @classmethod
    def from_pydantic(cls, exc: ValidationError) -> "APIValidationError":
        return cls(
            errors=[
                ValidationErrorDetail(
                    location=" -> ".join(map(str, err["loc"])),
                    message=err["msg"],
                    error_type=err["type"],
                    context=err.get("ctx"),
                )
                for err in exc.errors()
            ],
        )


class BotErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the error",
        examples=["Couldn't communicate with Telegram Bot (HTTP 503 error) : Service Unavailable"],
    )


class InternalServerErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the internal server error",
        examples=[
            (
                "An internal server error occurred during the process."
            )
        ],
    )


class GoogleSheetsParserError(BaseModel):
    model: str
    spreadsheet: str
    sheet_id: int
    row_id: int
    error: APIValidationError

    @classmethod
    def http_exception(
            cls,
            model: typing.Type[BaseModel],
            spreadsheet: str,
            sheet_id: int,
            row_id: int,
            error: ValidationError
    ):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                             detail=cls(model=repr(model),
                                        spreadsheet=spreadsheet,
                                        sheet_id=sheet_id,
                                        row_id=row_id,
                                        error=APIValidationError.from_pydantic(error)).model_dump()
                             )

