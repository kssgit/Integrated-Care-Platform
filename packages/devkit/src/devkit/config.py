from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    SERVICE_NAME: str = "service"
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None
    KAFKA_BOOTSTRAP_SERVERS: str | None = None
    JWT_SECRET_KEY: str = "dev-only-secret"
    ENCRYPTION_MASTER_KEY: str = "dev-encryption-key"


def load_settings(service_name: str) -> ServiceSettings:
    return ServiceSettings(SERVICE_NAME=service_name)
