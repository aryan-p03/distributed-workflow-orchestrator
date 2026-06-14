import uvicorn

from backend.infrastructure.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "backend.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
