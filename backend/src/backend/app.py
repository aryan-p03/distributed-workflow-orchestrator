import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.application.services.health_service import HealthService
from backend.infrastructure.config import get_settings
from backend.infrastructure.runtime import (
    check_database_connection,
    check_redis_connection,
    sync_database_schema,
)
from backend.interfaces.http.router import create_api_router


def create_app() -> FastAPI:
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings

        await asyncio.to_thread(check_database_connection, settings.database_url)
        if settings.schema_sync_on_startup:
            await asyncio.to_thread(sync_database_schema, settings.database_url)
        await asyncio.to_thread(check_redis_connection, settings.redis_url)

        try:
            yield
        finally:
            logging.getLogger(__name__).info("Application shutdown complete")

    app = FastAPI(lifespan=lifespan)

    health_service = HealthService(database_url=settings.database_url, redis_url=settings.redis_url)
    app.include_router(create_api_router(health_service))

    return app
