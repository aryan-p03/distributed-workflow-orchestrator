import logging

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from backend.infrastructure.db import Base

logger = logging.getLogger(__name__)


def check_database_connection(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("Database dependency check failed")
        raise RuntimeError(f"Database dependency check failed: {exc.__class__.__name__}") from exc
    finally:
        engine.dispose()


def check_redis_connection(redis_url: str) -> None:
    client = Redis.from_url(redis_url)
    try:
        client.ping()
    except RedisError as exc:
        logger.exception("Redis dependency check failed")
        raise RuntimeError(f"Redis dependency check failed: {exc.__class__.__name__}") from exc
    finally:
        client.close()


def sync_database_schema(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        Base.metadata.create_all(engine, checkfirst=True)
        task_columns = {column["name"] for column in inspect(engine).get_columns("tasks")}
        if "input_payload" not in task_columns:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE tasks ADD COLUMN input_payload JSON NOT NULL DEFAULT '{}'")
                )
    except SQLAlchemyError as exc:
        logger.exception("Database schema sync failed")
        raise RuntimeError(f"Database schema sync failed: {exc.__class__.__name__}") from exc
    finally:
        engine.dispose()
