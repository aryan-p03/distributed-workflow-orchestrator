from fastapi import APIRouter

from backend.application.services.health_service import HealthService
from backend.interfaces.http.routers.health import create_health_router


def create_api_router(health_service: HealthService) -> APIRouter:
    api_router = APIRouter()
    api_router.include_router(create_health_router(health_service))
    return api_router
