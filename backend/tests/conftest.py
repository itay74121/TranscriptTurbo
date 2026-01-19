import pytest


@pytest.fixture()
def app(monkeypatch):
    # Ensure backend root is on sys.path when running via tooling.
    import sys
    from pathlib import Path

    backend_root = str(Path(__file__).resolve().parents[1])
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    # Configure env for tests (base URLs point to respx-mocked hosts).
    monkeypatch.setenv("SPEECHMATICS_API_KEY", "test_speechmatics_key")
    monkeypatch.setenv("SPEECHMATICS_BASE_URL", "http://speechmatics.test")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://openai.test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-nano")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://localhost:5173")

    from app.core import config as config_module

    config_module.get_settings.cache_clear()

    from app.main import create_app

    return create_app()


@pytest.fixture()
def anyio_backend():
    return "asyncio"

