# src/ml_classifier/middleware/logging_middleware.py

"""Logging middleware for FastAPI."""
import time

from fastapi import FastAPI, Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ml_classifier.utils.logging import get_request_id


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and log details."""
        request_id = get_request_id()
        request.state.request_id = request_id
        request.state.start_time = time.time()

        logger.info(
            f"Request [{request_id}]: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        logger.debug(f"Request [{request_id}] headers: {request.headers}")

        try:
            response = await call_next(request)
            process_time = time.time() - request.state.start_time
            response.headers["X-Request-ID"] = request_id
            logger.info(
                f"Response [{request_id}]: {request.method} {request.url.path} "
                f"status_code={response.status_code} processed in {process_time:.4f}s"
            )

            return response

        except Exception as e:
            process_time = time.time() - request.state.start_time
            logger.error(
                f"Error [{request_id}]: {request.method} {request.url.path} "
                f"failed after {process_time:.4f}s - {str(e)}"
            )
            raise


def add_request_logging_middleware(app: FastAPI) -> None:
    """Add the request logging middleware to the FastAPI app."""
    app.add_middleware(RequestLoggingMiddleware)
