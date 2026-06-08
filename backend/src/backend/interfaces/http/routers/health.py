from fastapi import APIRouter

from backend.application.services.health_service import HealthService
from backend.interfaces.http.schemas.health import HealthResponse


def create_health_router(health_service: HealthService) -> APIRouter:
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def check_health() -> HealthResponse:
        health = await health_service.get_health()
        return HealthResponse.model_validate(health)

    return router
