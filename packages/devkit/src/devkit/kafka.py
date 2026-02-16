from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def create_consumer(topic: str, group_id: str, bootstrap_servers: str):
    async def _create():
        try:
            from aiokafka import AIOKafkaConsumer
        except ImportError as exc:
            raise RuntimeError("aiokafka is required for kafka consumer") from exc

        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=True,
            auto_offset_reset="latest",
            request_timeout_ms=30000,
            retry_backoff_ms=500,
            reconnect_backoff_ms=500,
            reconnect_backoff_max_ms=10000,
            session_timeout_ms=10000,
            heartbeat_interval_ms=3000,
        )
        await consumer.start()
        return consumer

    return await run_with_retry(_create, max_retries=3, base_delay_seconds=0.2)


async def create_producer(bootstrap_servers: str):
    async def _create():
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError as exc:
            raise RuntimeError("aiokafka is required for kafka producer") from exc

        producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            acks="all",
            enable_idempotence=True,
            request_timeout_ms=30000,
            retry_backoff_ms=500,
            reconnect_backoff_ms=500,
            reconnect_backoff_max_ms=10000,
        )
        await producer.start()
        return producer

    return await run_with_retry(_create, max_retries=3, base_delay_seconds=0.2)


async def run_with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    base_delay_seconds: float,
    sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    attempt = 0
    while True:
        try:
            return await fn()
        except Exception:
            attempt += 1
            if attempt >= max_retries:
                raise
            delay = base_delay_seconds * (2 ** (attempt - 1))
            await sleep_fn(delay)


class AsyncKafkaProducerManager:
    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer = None
        self._lock = asyncio.Lock()

    async def get(self):
        async with self._lock:
            if self._producer is None:
                self._producer = await create_producer(self._bootstrap_servers)
            return self._producer

    async def reconnect(self):
        async with self._lock:
            if self._producer is not None:
                await self._producer.stop()
            self._producer = await create_producer(self._bootstrap_servers)
            return self._producer

    async def send_and_wait(self, topic: str, payload: bytes):
        attempt = 0
        while True:
            producer = await self.get()
            try:
                return await producer.send_and_wait(topic, payload)
            except Exception:
                attempt += 1
                if attempt >= 3:
                    raise
                await self.reconnect()
                await asyncio.sleep(0.2 * (2 ** (attempt - 1)))

    async def stop(self) -> None:
        async with self._lock:
            if self._producer is not None:
                await self._producer.stop()
                self._producer = None


class AsyncKafkaConsumerManager:
    def __init__(self, topic: str, group_id: str, bootstrap_servers: str) -> None:
        self._topic = topic
        self._group_id = group_id
        self._bootstrap_servers = bootstrap_servers
        self._consumer = None
        self._lock = asyncio.Lock()

    async def get(self):
        async with self._lock:
            if self._consumer is None:
                self._consumer = await create_consumer(
                    topic=self._topic,
                    group_id=self._group_id,
                    bootstrap_servers=self._bootstrap_servers,
                )
            return self._consumer

    async def reconnect(self):
        async with self._lock:
            if self._consumer is not None:
                await self._consumer.stop()
            self._consumer = await create_consumer(
                topic=self._topic,
                group_id=self._group_id,
                bootstrap_servers=self._bootstrap_servers,
            )
            return self._consumer

    async def stop(self) -> None:
        async with self._lock:
            if self._consumer is not None:
                await self._consumer.stop()
                self._consumer = None
