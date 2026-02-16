from devkit.config import load_settings


def test_load_settings_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("REDIS_URL", "redis://example:6379/0")
    settings = load_settings("api")

    assert settings.SERVICE_NAME == "api"
    assert settings.DATABASE_URL == "postgresql://example"
    assert settings.REDIS_URL == "redis://example:6379/0"
