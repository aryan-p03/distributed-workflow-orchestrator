from fastapi import APIRouter
from sqlalchemy.orm import sessionmaker

from backend.application.services.health_service import HealthService
from backend.interfaces.http.routers.auth import create_auth_router
from backend.interfaces.http.routers.health import create_health_router


def create_api_router(
    health_service: HealthService,
    session_factory: sessionmaker,  # type: ignore[type-arg]
    jwt_secret: str,
    jwt_expires_seconds: int = 3600,
) -> APIRouter:
    api_router = APIRouter()
    api_router.include_router(create_health_router(health_service))
    api_router.include_router(create_auth_router(session_factory, jwt_secret, jwt_expires_seconds))
    return api_router
