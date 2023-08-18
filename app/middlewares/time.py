import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TimeMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app,
    ):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logger.info(f"{request.url} process time: {int(process_time * 1000)} ms")
        return response
