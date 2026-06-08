from fastapi import FastAPI

from backend.application.services.health_service import HealthService
from backend.infrastructure.config import get_settings
from backend.interfaces.http.router import create_api_router


def create_app() -> FastAPI:
    app = FastAPI()
    app.state.settings = get_settings()

    health_service = HealthService()
    app.include_router(create_api_router(health_service))

    return app
