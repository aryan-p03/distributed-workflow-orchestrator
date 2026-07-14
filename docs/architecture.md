# Architecture

## Overview

This document describes the current backend and worker architecture.
It shows package boundaries, startup behavior, request/worker execution flow, and runtime components.

## Package Structure

- `interfaces`: FastAPI routers, transport schemas, and HTTP-facing dependencies.
- `application`: use-case orchestration and service-level workflow logic.
- `domain`: state models, transition rules, and pure business constraints.
- `infrastructure`: database models/runtime checks, Redis integration, configuration, and worker runtime.

## Dependency Direction

1. `interfaces -> application`
2. `application -> domain`
3. `application -> infrastructure`
4. `infrastructure -> domain` (data mapping/value usage only)

## Composition Root

The backend composition root is `backend/src/backend/app.py`.

At startup it:

1. Loads typed settings.
2. Configures logging.
3. Runs dependency checks.
4. Optionally runs database schema sync when `SCHEMA_SYNC_ON_STARTUP=true`.
5. Registers API routers.
6. Marks readiness when startup checks complete successfully.

## Runtime Components

- **API runtime**: FastAPI application.
- **Database**: PostgreSQL accessed through SQLAlchemy ORM models.
- **Cache/Broker**: Redis used for runtime connectivity and Celery broker/backend.
- **Worker runtime**: Celery worker process under `backend/src/backend/worker`.

## Persistence Model

Current core tables:

- `users`
- `workflows`
- `tasks`
- `task_logs`

State columns are represented with SQLAlchemy enums for workflow/task lifecycle state.

## API Endpoints

- `GET /health`: service health response.

## Request Flow

1. Request enters router under `interfaces/http/routers`.
2. Router validates/normalizes input and calls an application service.
3. Application service executes use-case logic and applies domain rules.
4. Infrastructure layer persists or loads data from PostgreSQL.
5. Router returns serialized response schema.

## Worker Flow

1. Task is enqueued to Celery.
2. Worker receives task and executes handler logic.
3. Task/workflow state updates are applied through application/domain flow.
4. Task execution events are persisted in `task_logs`.

## Operational Notes

- Startup readiness remains false until dependency checks complete.
- Schema synchronization is idempotent and runs through SQLAlchemy metadata.
- Docker Compose runs `postgres`, `redis`, `api`, `worker`, and `frontend` as the local stack.
