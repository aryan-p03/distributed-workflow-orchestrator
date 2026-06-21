import asyncio

from backend.domain.health import HealthStatus
from backend.infrastructure.runtime import check_database_connection, check_redis_connection


class HealthService:
    def __init__(self, database_url: str, redis_url: str) -> None:
        self._database_url = database_url
        self._redis_url = redis_url

    async def get_health(self) -> HealthStatus:
        details: dict[str, str] = {}

        try:
            await asyncio.to_thread(check_database_connection, self._database_url)
            details["database"] = "ok"
        except RuntimeError:
            details["database"] = "error"

        try:
            await asyncio.to_thread(check_redis_connection, self._redis_url)
            details["redis"] = "ok"
        except RuntimeError:
            details["redis"] = "error"

        overall = "ok" if all(v == "ok" for v in details.values()) else "degraded"
        return HealthStatus(status=overall, details=details)
