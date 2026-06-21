from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.application.services.health_service import HealthService
from backend.interfaces.http.schemas.health import HealthResponse


def create_health_router(health_service: HealthService) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/health",
        response_model=HealthResponse,
        responses={503: {"model": HealthResponse}},
    )
    async def check_health() -> JSONResponse:
        health = await health_service.get_health()
        body = HealthResponse.model_validate(health)
        status_code = 200 if health.status == "ok" else 503
        return JSONResponse(content=body.model_dump(), status_code=status_code)

    return router
