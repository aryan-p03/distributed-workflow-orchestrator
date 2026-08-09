# Distributed Workflow Orchestrator

A full stack platform for defining, running, and monitoring multistep workflows. Users create workflows composed of sequenced tasks, dispatch them to a Celery worker pool, and track execution state in real time through a React frontend. The backend enforces a strict state machine for workflow and task lifecycle, with configurable retries and append only execution logs.

## Tech Stack

| Layer | Technology |
| --- | --- |
| API | Python, FastAPI, SQLAlchemy |
| Worker | Celery |
| Frontend | React, TypeScript, Vite |
| Database | PostgreSQL |
| Broker / Cache | Redis |
| Local stack | Docker Compose |
| Python tooling | uv |

## Quick Start

**Prerequisites:**

- [Docker](https://www.docker.com/) (with Docker Compose)

```bash
# 1. Optional: copy the environment template if you want to override defaults
cp .env.example .env

# 2. Boot the full stack
make up-build
```

If the default ports and local credentials work for you, you can skip creating `.env` and run the stack as-is.

**Services:**

| Service | URL |
| --- | --- |
| API | <http://localhost:8000> |
| Frontend | <http://localhost:5173> |
| Postgres | localhost:5432 |
| Redis | localhost:6379 |

## Development Commands

All common tasks are available via [Makefile](Makefile):

| Command | Description |
| --- | --- |
| `make help` | Show available targets |
| `make up` | Boot stack (no rebuild) |
| `make up-build` | Boot stack and rebuild images |
| `make down` | Stop and remove containers |
| `make logs` | Tail all service logs |
| `make logs-api` | Tail API logs only |
| `make logs-frontend` | Tail frontend logs only |
| `make logs-worker` | Tail worker logs only |
| `make ps` | Show service status |
| `make restart` | Restart api, worker, and frontend |
| `make restart-api` | Restart API service only |
| `make restart-frontend` | Restart frontend service only |
| `make restart-worker` | Restart worker service only |
| `make rebuild-api` | Rebuild and restart API service |
| `make rebuild-frontend` | Rebuild and restart frontend service |
| `make clean` | Full teardown including volumes |

## Documentation

Project design and data model references live in [docs](docs):

- [Architecture](docs/architecture.md)
- [State Machine](docs/state-machine.md)
- [Database Schema](docs/schema.md)
- [OpenAPI Spec](backend/openapi/openapi.yaml)

## CI

Both services run automated checks on every pull request:

- [Backend CI](.github/workflows/backend-ci.yml) — jobs: `audit`, `check`, `build`, `test`, `lint-openapi`
- [Frontend CI](.github/workflows/frontend-ci.yml) — jobs: `audit`, `check`, `build`, `test`

## License

This project is licensed under the [MIT License](LICENSE.txt).
