import pytest

from backend.infrastructure.config import Settings, get_settings


def test_settings_default_api_port() -> None:
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.api_port == 8000


def test_settings_reads_api_port_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", "9000")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.api_port == 9000


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", "9000")
    get_settings.cache_clear()

    first = get_settings()

    monkeypatch.setenv("API_PORT", "9100")
    second = get_settings()

    assert first is second
    assert second.api_port == 9000


def test_settings_type_is_concrete() -> None:
    get_settings.cache_clear()

    settings = get_settings()

    assert isinstance(settings, Settings)


def test_schema_sync_on_startup_defaults_true() -> None:
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.schema_sync_on_startup is True


def test_schema_sync_on_startup_reads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCHEMA_SYNC_ON_STARTUP", "false")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.schema_sync_on_startup is False


def test_celery_log_level_defaults_info() -> None:
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.celery_log_level == "INFO"


def test_celery_log_level_reads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CELERY_LOG_LEVEL", "DEBUG")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.celery_log_level == "DEBUG"
