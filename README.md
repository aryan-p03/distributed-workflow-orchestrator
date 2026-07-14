# Distributed Workflow Orchestrator

A distributed workflow orchestration platform.

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
| `make up` | Boot stack (no rebuild) |
| `make up-build` | Boot stack and rebuild images |
| `make logs` | Tail all service logs |
| `make logs-api` | Tail API logs only |
| `make ps` | Show service status |
| `make clean` | Full teardown including volumes |

## Documentation

Project design and data model references live in [docs](docs):

- [Architecture](docs/architecture.md)
- [State Machine](docs/state-machine.md)
- [Database Schema](docs/schema.md)

## CI

Both services run automated checks on every pull request:

- [Backend CI](.github/workflows/backend-ci.yml) — jobs: `audit`, `check`, `build`, `test`
- [Frontend CI](.github/workflows/frontend-ci.yml) — jobs: `audit`, `check`, `build`, `test`

## License

This project is licensed under the [MIT License](LICENSE.txt).
