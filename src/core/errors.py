import typing

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from starlette import status


class ApiException(BaseModel):
    msg: str
    code: str


class ApiHTTPException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: list[ApiException],
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail=[e.model_dump(mode="json") for e in detail],
            headers=headers,
        )


class ValidationErrorDetail(BaseModel):
    location: str
    message: str
    error_type: str


class APIValidationError(BaseModel):
    errors: list[ValidationErrorDetail]

    @classmethod
    def from_pydantic(cls, exc: ValidationError) -> "APIValidationError":
        return cls(
            errors=[
                ValidationErrorDetail(
                    location=" -> ".join(map(str, err["loc"])),
                    message=str(err["msg"]),
                    error_type=str(err["type"]),
                )
                for err in exc.errors()
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
        error: ValidationError,
    ) -> ApiHTTPException:
        msg = cls(
            model=repr(model),
            spreadsheet=spreadsheet,
            sheet_id=sheet_id,
            row_id=row_id,
            error=APIValidationError.from_pydantic(error),
        )
        return ApiHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[ApiException(msg=msg.model_dump_json(), code="unprocessable_entity")],
        )
