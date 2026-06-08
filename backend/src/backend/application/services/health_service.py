from backend.domain.health import HealthStatus


class HealthService:
    async def get_health(self) -> HealthStatus:
        return HealthStatus(status="ok", details={})
