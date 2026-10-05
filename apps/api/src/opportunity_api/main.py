"""Application factory."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import health
from .core.config import get_settings
from .core.errors import install_exception_handlers


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

    install_exception_handlers(app)
    app.include_router(health.router)

    return app
