from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self: 'RequestLoggingMiddleware',
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started_at = perf_counter()
        logger.info('http_request_started method=%s path=%s', request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.exception(
                'http_request_failed method=%s path=%s duration_ms=%s',
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            'http_request_completed method=%s path=%s status=%s duration_ms=%s',
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
