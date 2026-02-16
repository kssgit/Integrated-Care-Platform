from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

from sqlalchemy import MetaData, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine as _create_async_engine
from sqlalchemy.orm import DeclarativeBase

T = TypeVar("T")


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""


def normalize_postgres_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    return dsn


def load_database_url(default: str = "") -> str:
    raw = os.getenv("DATABASE_URL") or default
    return normalize_postgres_dsn(raw)


def create_async_engine(dsn: str):
    return _create_async_engine(
        normalize_postgres_dsn(dsn),
        future=True,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def is_transient_db_error(exc: Exception) -> bool:
    if isinstance(exc, OperationalError):
        return True
    if isinstance(exc, DBAPIError):
        return bool(getattr(exc, "connection_invalidated", False))
    return False


async def create_schema_if_not_exists(engine: AsyncEngine, schema_name: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))


async def create_all_tables(engine: AsyncEngine, metadata: MetaData) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


class AsyncDatabaseManager:
    def __init__(
        self,
        dsn: str,
        *,
        max_retries: int = 3,
        base_delay_seconds: float = 0.2,
    ) -> None:
        self._dsn = normalize_postgres_dsn(dsn)
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("database manager is not connected")
        return self._engine

    async def connect(self) -> None:
        if self._engine is None:
            self._engine = create_async_engine(self._dsn)
            self._session_factory = create_session_factory(self._engine)
        await self._ping()

    async def disconnect(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    async def reconnect(self) -> None:
        await self.disconnect()
        await self.connect()

    async def _ping(self) -> None:
        async with self.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._session_factory is None:
            await self.connect()
        assert self._session_factory is not None
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def run_with_session(
        self,
        fn: Callable[[AsyncSession], Awaitable[T]],
    ) -> T:
        attempt = 0
        while True:
            try:
                async with self.session() as session:
                    return await fn(session)
            except Exception as exc:
                attempt += 1
                if attempt >= self._max_retries or not is_transient_db_error(exc):
                    raise
                await self.reconnect()
                await asyncio.sleep(self._base_delay_seconds * (2 ** (attempt - 1)))
