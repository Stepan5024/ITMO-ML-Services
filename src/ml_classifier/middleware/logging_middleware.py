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

        # Log request details
        logger.info(
            f"Request [{request_id}]: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        # Log request headers at debug level
        logger.debug(f"Request [{request_id}] headers: {request.headers}")

        try:
            # Process the request and get the response
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - request.state.start_time

            # Add request_id to response headers
            response.headers["X-Request-ID"] = request_id

            # Log response details
            logger.info(
                f"Response [{request_id}]: {request.method} {request.url.path} "
                f"status_code={response.status_code} processed in {process_time:.4f}s"
            )

            return response

        except Exception as e:
            # Log exceptions
            process_time = time.time() - request.state.start_time
            logger.error(
                f"Error [{request_id}]: {request.method} {request.url.path} "
                f"failed after {process_time:.4f}s - {str(e)}"
            )
            raise


def add_request_logging_middleware(app: FastAPI) -> None:
    """Add the request logging middleware to the FastAPI app."""
    app.add_middleware(RequestLoggingMiddleware)
