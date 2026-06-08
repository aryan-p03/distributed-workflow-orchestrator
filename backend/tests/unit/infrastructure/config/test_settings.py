import pytest

from backend.infrastructure.config import Settings, get_settings


def test_settings_default_server_port() -> None:
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.server_port == 8000


def test_settings_reads_server_port_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVER_PORT", "9000")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.server_port == 9000


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVER_PORT", "9000")
    get_settings.cache_clear()

    first = get_settings()

    monkeypatch.setenv("SERVER_PORT", "9100")
    second = get_settings()

    assert first is second
    assert second.server_port == 9000


def test_settings_type_is_concrete() -> None:
    get_settings.cache_clear()

    settings = get_settings()

    assert isinstance(settings, Settings)
