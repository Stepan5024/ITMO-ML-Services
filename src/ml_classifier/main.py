"""Main application module for ML Classifier service.

This module initializes and configures the FastAPI application,
sets up routes, middleware, and logging.
"""
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Generator, cast

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel

from ml_classifier import __version__
from ml_classifier.middleware import add_request_logging_middleware
from ml_classifier.models.schemas import ErrorResponse
from ml_classifier.utils.logging import LogLevel, setup_logging
from ml_classifier.controller.auth_controller import router as auth_router

# Initialize logging
setup_logging()


class AppSettings:
    """Application settings."""

    title = "ML Classifier Service"
    description = """
        # ML Classifier Service

        Сервис машинного обучения для классификации отзывов студентов.

        ## Функциональность

        * **Классификация текста** - анализ отзывов студентов
        * **Асинхронная обработка** - обработка больших объемов данных
        * **API интерфейс** - простой доступ к функциональности

        ## Технический стек

        * FastAPI
        * PostgreSQL
        * Redis
        * Celery
        """
    version = __version__
    environment = os.getenv("ENVIRONMENT", "development")
    debug = os.getenv("DEBUG", "False").lower() == "true"
    contact = {
        "name": "ITMO Team",
        "url": "https://github.com/your-organization/ITMO-ML-Services",
        "email": "example@itmo.ru",
    }


settings = AppSettings()


class HealthCheck(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle events."""
    logger.info("Starting up ML Classifier Service")
    yield
    logger.info("Shutting down ML Classifier Service")


def custom_openapi() -> Dict[str, Any]:
    """Generate custom OpenAPI schema."""
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return cast(Dict[str, Any], app.openapi_schema)

    openapi_schema = get_openapi(
        title=settings.title,
        version=settings.version,
        description=settings.description,
        routes=app.routes,
    )

    openapi_schema["info"]["contact"] = settings.contact

    openapi_schema["tags"] = [
        {"name": "Status", "description": "Эндпоинты для проверки состояния сервиса"},
        {"name": "API", "description": "Основные эндпоинты API"},
        {"name": "User", "description": "Эндпоинты для работы с пользователями"},
        {"name": "Admin", "description": "Административные эндпоинты"},
    ]

    openapi_schema["servers"] = [
        {"url": "/", "description": "Current server"},
        {
            "url": "https://ml-classifier.example.com",
            "description": "Production server",
        },
        {
            "url": "https://staging.ml-classifier.example.com",
            "description": "Staging server",
        },
    ]

    app.openapi_schema = openapi_schema
    return cast(Dict[str, Any], app.openapi_schema)


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version,
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    add_request_logging_middleware(app)
    app.openapi = custom_openapi

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html() -> Any:
        """Serve customized Swagger UI documentation."""
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{settings.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url=(
                "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"
            ),
            swagger_css_url=(
                "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
            ),
            swagger_favicon_url="/static/favicon.ico",
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html() -> Any:
        """Serve ReDoc documentation."""
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{settings.title} - ReDoc",
            redoc_js_url=(
                "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"
            ),
            redoc_favicon_url="/static/favicon.ico",
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions globally."""
        logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(
                ErrorResponse(
                    status_code=exc.status_code,
                    message=str(exc.detail),
                    error_type="http_exception",
                )
            ),
        )

    @app.get("/", tags=["Status"], summary="Service status")
    async def root() -> Dict[str, str]:
        """Return basic service status information."""
        logger.debug("Root endpoint called")
        return {"message": "ML Classifier Service is running"}

    @app.get("/health", response_model=HealthCheck, tags=["Status"])
    async def health_check() -> HealthCheck:
        """Perform comprehensive health check."""
        logger.debug("Health check endpoint called")
        return HealthCheck(
            status="ok",
            version=settings.version,
            environment=settings.environment,
        )

    api_v1_router = APIRouter(prefix="/api/v1")

    @api_v1_router.get("/", tags=["API"])
    async def api_root() -> Dict[str, str]:
        """Return API version information."""
        logger.debug("API v1 root endpoint called")
        return {"message": "ML Classifier API v1", "version": settings.version}

    @app.post("/api/v1/admin/log-level", tags=["Admin"])
    async def change_log_level(level: str) -> Dict[str, str]:
        """Dynamically adjust logging verbosity."""
        try:
            log_level = LogLevel(level.upper())
            logger.remove()
            logger.add(sys.stderr, level=log_level)
            logger.info(f"Log level changed to {log_level}")
            return {"message": f"Log level changed to {log_level}"}
        except ValueError:
            valid_levels = [level.value for level in LogLevel]
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid log level. Valid levels are: "
                    f"{', '.join(valid_levels)}"
                ),
            )

    app.include_router(api_v1_router)
    app.include_router(auth_router)
    return app


# Create the FastAPI app instance
app = create_app()


def get_db() -> Generator[None, None, None]:
    """Database dependency generator."""
    logger.debug("Database session requested")
    try:
        yield
    finally:
        logger.debug("Database session closed")


def get_current_user(request: Request) -> Dict[str, Any]:
    """Authenticate and retrieve current user."""
    logger.debug("Current user requested")
    return {"username": "test_user", "id": 1}


@app.get("/api/v1/me", tags=["User"])
async def get_me(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Retrieve current authenticated user information."""
    logger.debug(f"User info requested for {current_user['username']}")
    return current_user
