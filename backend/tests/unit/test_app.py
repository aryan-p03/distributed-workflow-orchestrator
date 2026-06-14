from backend.app import create_app
from backend.infrastructure.config import Settings, get_settings


def test_create_app_stores_settings_on_app_state() -> None:
    get_settings.cache_clear()

    app = create_app()

    assert isinstance(app.state.settings, Settings)
    assert app.state.settings.api_port == 8000
