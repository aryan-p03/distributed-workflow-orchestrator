import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

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
            engine.dispose()
            logging.getLogger(__name__).info("Application shutdown complete")

    app = FastAPI(lifespan=lifespan)

    allow_origins = [
        origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    health_service = HealthService(database_url=settings.database_url, redis_url=settings.redis_url)
    app.include_router(
        create_api_router(
            health_service,
            session_factory,
            settings.jwt_secret,
            settings.jwt_expires_seconds,
        )
    )

    return app
