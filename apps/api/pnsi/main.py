"""FastAPI application factory. All application routes live under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from pnsi.api.v1 import audit, auth, health, users
from pnsi.errors import install_error_handlers
from pnsi.log import configure_logging, get_logger
from pnsi.settings import Settings, get_settings

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    # Validates the configuration: a wrong core value stops startup here.
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.secret_values())

    app = FastAPI(
        title="PNSI API",
        version="0.1.0",
        description=(
            "Plateforme Nationale de Social Listening Sanitaire et de Gestion de l'Infodémie."
        ),
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs" if settings.is_dev else None,
        redoc_url=None,
    )
    install_error_handlers(app)

    v1 = APIRouter(prefix=API_PREFIX)
    v1.include_router(health.router)
    v1.include_router(auth.router)
    v1.include_router(users.router)
    v1.include_router(audit.router)
    app.include_router(v1)

    get_logger(__name__).info(
        "app_started",
        env=settings.app_env.value,
        ai_mode=settings.ai_mode.value,
        integrations={k: v.value for k, v in settings.integration_status().items()},
    )
    return app


app = create_app()
