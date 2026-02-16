from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from devkit.timezone import configure_kst_timezone


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    SERVICE_NAME: str = "service"
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None
    KAFKA_BOOTSTRAP_SERVERS: str | None = None
    JWT_SECRET_KEY: str = "dev-only-secret"
    ENCRYPTION_MASTER_KEY: str = "dev-encryption-key"
    INTERNAL_EVENT_HMAC_SECRET: str = ""
    USER_SERVICE_BASE_URL: str | None = None


def load_settings(service_name: str) -> ServiceSettings:
    configure_kst_timezone()
    return ServiceSettings(SERVICE_NAME=service_name)
