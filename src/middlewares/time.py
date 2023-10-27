import time

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TimeMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
    ) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        # logger.info(f'{request.client.host}:{request.client.port} - "{request.method} {request.url.path} {
        # response.status_code}" [process time: {int(process_time * 1000)} ms]')
        return response
