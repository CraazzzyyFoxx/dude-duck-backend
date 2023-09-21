from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import ORJSONResponse
from loguru import logger
from pydantic import ValidationError
from starlette import status
from starlette.middleware.base import (BaseHTTPMiddleware,
                                       RequestResponseEndpoint)
from starlette.requests import Request
from starlette.responses import Response


class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            response = await call_next(request)
        except RequestValidationError as e:
            response = ORJSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": [{"msg": e.errors(), "code": "unprocessable_entity"}]}
            )
            logger.exception("What!?")
        except ValidationError as e:
            response = ORJSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": [{"msg": e.errors(), "code": "unprocessable_entity"}]}
            )
            logger.exception("What!?")
        except HTTPException as e:
            response = ORJSONResponse({"detail": e.detail}, status_code=e.status_code)
            logger.exception("What!?")
        except Exception:
            logger.exception("What!?")
            response = ORJSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": [{"msg": "Unknown", "code": "Unknown"}]},
            )

        return response
