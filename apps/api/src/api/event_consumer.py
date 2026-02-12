from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from api.cache import FacilityCache
from api.dependencies import get_facility_cache
from api.event_dedup import InMemoryProcessedEventStore, ProcessedEventStore, RedisProcessedEventStore


@dataclass(frozen=True)
class EventConsumerConfig:
    max_retries: int = 3
    base_delay_seconds: float = 0.1
    dedup_ttl_seconds: int = 3600


class ApiEventConsumer:
    def __init__(
        self,
        cache: FacilityCache,
        config: EventConsumerConfig,
        dedup_store: ProcessedEventStore,
        sleep_fn=asyncio.sleep,
    ) -> None:
        self._cache = cache
        self._config = config
        self._dedup_store = dedup_store
        self._sleep = sleep_fn

    async def handle_payload(self, payload: dict[str, Any]) -> int:
        event_type = str(payload.get("event_type", ""))
        if event_type != "etl_completed":
            return 0
        return await self._cache.invalidate_facilities()

    async def handle_message(self, message: dict[str, Any]) -> int:
        trace_id = str(message.get("trace_id", ""))
        payload = self._extract_payload(message)
        if not trace_id:
            return await self.handle_payload(payload)
        allowed = await self._dedup_store.mark_once(trace_id, self._config.dedup_ttl_seconds)
        if not allowed:
            return 0
        return await self.handle_payload(payload)

    async def run(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        dlq_topic: str,
    ) -> None:
        consumer = await self._create_consumer(bootstrap_servers, topic, group_id)
        producer = await self._create_producer(bootstrap_servers)
        try:
            async for message in consumer:
                await self._process_with_retry(
                    value=message.value,
                    publish_dlq=lambda value, error: self._publish_dlq(producer, dlq_topic, value, error),
                )
        finally:
            await consumer.stop()
            await producer.stop()

    async def _process_with_retry(self, value: bytes, publish_dlq) -> None:
        attempt = 0
        while attempt < self._config.max_retries:
            try:
                message = self._decode_message(value)
                await self.handle_message(message)
                return
            except Exception as exc:
                attempt += 1
                if attempt >= self._config.max_retries:
                    await publish_dlq(value, str(exc))
                    return
                delay = self._config.base_delay_seconds * (2 ** (attempt - 1))
                await self._sleep(delay)

    async def _create_consumer(self, bootstrap_servers: str, topic: str, group_id: str):
        try:
            from aiokafka import AIOKafkaConsumer
        except ImportError as exc:
            raise RuntimeError("aiokafka is required for api event consumer") from exc
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=True,
            auto_offset_reset="latest",
        )
        await consumer.start()
        return consumer

    async def _create_producer(self, bootstrap_servers: str):
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError as exc:
            raise RuntimeError("aiokafka is required for api event consumer") from exc
        producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
        await producer.start()
        return producer

    async def _publish_dlq(self, producer, topic: str, value: bytes, error: str) -> None:
        payload = json.dumps(
            {
                "error": error,
                "raw_value": value.decode("utf-8", errors="replace"),
            }
        ).encode("utf-8")
        await producer.send_and_wait(topic, payload)

    def _decode_message(self, value: bytes) -> dict[str, Any]:
        decoded = json.loads(value.decode("utf-8"))
        if isinstance(decoded, dict):
            return decoded
        return {}

    def _extract_payload(self, message: dict[str, Any]) -> dict[str, Any]:
        payload = message.get("payload")
        if isinstance(payload, dict):
            return payload
        return message


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def main() -> None:
    bootstrap = _required_env("KAFKA_BOOTSTRAP_SERVERS")
    topic = os.getenv("API_EVENT_TOPIC", "api-events")
    dlq_topic = os.getenv("API_EVENT_DLQ_TOPIC", "api-events-dlq")
    group_id = os.getenv("API_EVENT_CONSUMER_GROUP", "api-event-consumer")
    max_retries = int(os.getenv("API_EVENT_CONSUMER_MAX_RETRIES", "3"))
    base_delay_seconds = float(os.getenv("API_EVENT_CONSUMER_BASE_DELAY_SECONDS", "0.1"))
    dedup_ttl_seconds = int(os.getenv("API_EVENT_DEDUP_TTL_SECONDS", "3600"))
    dedup_store = _build_dedup_store()
    consumer = ApiEventConsumer(
        cache=get_facility_cache(),
        config=EventConsumerConfig(
            max_retries=max_retries,
            base_delay_seconds=base_delay_seconds,
            dedup_ttl_seconds=dedup_ttl_seconds,
        ),
        dedup_store=dedup_store,
    )
    asyncio.run(
        consumer.run(
            bootstrap_servers=bootstrap,
            topic=topic,
            group_id=group_id,
            dlq_topic=dlq_topic,
        )
    )


def _build_dedup_store() -> ProcessedEventStore:
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as redis

            client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
            return RedisProcessedEventStore(client)
        except Exception:
            return InMemoryProcessedEventStore()
    return InMemoryProcessedEventStore()


if __name__ == "__main__":
    main()
