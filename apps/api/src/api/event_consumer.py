from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from api.cache import FacilityCache
from api.dependencies import get_facility_cache


class ApiEventConsumer:
    def __init__(self, cache: FacilityCache) -> None:
        self._cache = cache

    async def handle_payload(self, payload: dict[str, Any]) -> int:
        event_type = str(payload.get("event_type", ""))
        if event_type != "etl_completed":
            return 0
        return await self._cache.invalidate_facilities()

    async def run(self, bootstrap_servers: str, topic: str, group_id: str) -> None:
        consumer = await self._create_consumer(bootstrap_servers, topic, group_id)
        try:
            async for message in consumer:
                payload = self._decode_payload(message.value)
                await self.handle_payload(payload)
        finally:
            await consumer.stop()

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

    def _decode_payload(self, value: bytes) -> dict[str, Any]:
        decoded = json.loads(value.decode("utf-8"))
        if isinstance(decoded, dict) and isinstance(decoded.get("payload"), dict):
            return decoded["payload"]
        if isinstance(decoded, dict):
            return decoded
        return {}


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def main() -> None:
    bootstrap = _required_env("KAFKA_BOOTSTRAP_SERVERS")
    topic = os.getenv("API_EVENT_TOPIC", "api-events")
    group_id = os.getenv("API_EVENT_CONSUMER_GROUP", "api-event-consumer")
    consumer = ApiEventConsumer(cache=get_facility_cache())
    asyncio.run(consumer.run(bootstrap_servers=bootstrap, topic=topic, group_id=group_id))


if __name__ == "__main__":
    main()

