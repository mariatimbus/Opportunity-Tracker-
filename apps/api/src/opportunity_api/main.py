"""Application factory."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import applications, auth, health, opportunities, profile
from .core.config import get_settings
from .core.errors import install_exception_handlers
from .core.ratelimit import RateLimitMiddleware


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO)

    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RateLimitMiddleware)

    install_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(profile.router, prefix="/api/v1")
    app.include_router(profile.skills_router, prefix="/api/v1")
    app.include_router(opportunities.router, prefix="/api/v1")
    app.include_router(applications.router, prefix="/api/v1")

    return app


app = create_app()
