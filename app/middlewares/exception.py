from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import ORJSONResponse
from loguru import logger
from pydantic import ValidationError
from starlette import status
from starlette.middleware.base import (BaseHTTPMiddleware,
                                       RequestResponseEndpoint)
from starlette.requests import Request
from starlette.responses import Response
from tortoise.exceptions import IntegrityError

from app.core import config


class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
        except RequestValidationError as e:
            if config.app.debug:
                logger.exception("What!?")
            response = ORJSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": [{"msg": e.errors(), "code": "unprocessable_entity"}]},
            )
        except ValidationError as e:
            logger.exception("What!?")
            response = ORJSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": [{"msg": e.errors(), "code": "unprocessable_entity"}]},
            )
        except HTTPException as e:
            response = ORJSONResponse({"detail": e.detail}, status_code=e.status_code)
        except IntegrityError as e:
            logger.exception("What!?")
            response = ORJSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": [{"msg": str(e), "code": "integrity_error"}]},
            )
        except Exception as e:
            logger.exception(e)
            response = ORJSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": [{"msg": "Unknown", "code": "Unknown"}]},
            )

        return response
