from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DlqRetryConfig:
    max_attempts: int = 3


class ApiEventDlqRetryWorker:
    def __init__(self, config: DlqRetryConfig) -> None:
        self._config = config

    async def run(
        self,
        bootstrap_servers: str,
        dlq_topic: str,
        target_topic: str,
        parking_topic: str,
        group_id: str,
    ) -> None:
        consumer = await self._create_consumer(bootstrap_servers, dlq_topic, group_id)
        producer = await self._create_producer(bootstrap_servers)
        try:
            async for message in consumer:
                topic, payload = self._handle_dlq_value(message.value, target_topic, parking_topic)
                await producer.send_and_wait(topic, payload)
        finally:
            await consumer.stop()
            await producer.stop()

    def _handle_dlq_value(self, value: bytes, target_topic: str, parking_topic: str) -> tuple[str, bytes]:
        try:
            decoded = json.loads(value.decode("utf-8"))
            raw_value = decoded.get("raw_value")
            if not isinstance(raw_value, str):
                raise ValueError("raw_value is missing")
            original = json.loads(raw_value)
            retry_count = int(original.get("dlq_retry_count", 0))
            if retry_count >= self._config.max_attempts:
                return parking_topic, value
            original["dlq_retry_count"] = retry_count + 1
            return target_topic, json.dumps(original).encode("utf-8")
        except Exception:
            # Keep original DLQ payload for later inspection.
            return parking_topic, value

    async def _create_consumer(self, bootstrap_servers: str, topic: str, group_id: str):
        try:
            from aiokafka import AIOKafkaConsumer
        except ImportError as exc:
            raise RuntimeError("aiokafka is required for dlq retry worker") from exc
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
            raise RuntimeError("aiokafka is required for dlq retry worker") from exc
        producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
        await producer.start()
        return producer


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def main() -> None:
    bootstrap = _required_env("KAFKA_BOOTSTRAP_SERVERS")
    dlq_topic = os.getenv("API_EVENT_DLQ_TOPIC", "api-events-dlq")
    target_topic = os.getenv("API_EVENT_TOPIC", "api-events")
    parking_topic = os.getenv("API_EVENT_PARKING_TOPIC", "api-events-parking")
    group_id = os.getenv("API_EVENT_DLQ_RETRY_GROUP", "api-event-dlq-retry")
    max_attempts = int(os.getenv("API_EVENT_DLQ_RETRY_MAX_ATTEMPTS", "3"))
    worker = ApiEventDlqRetryWorker(config=DlqRetryConfig(max_attempts=max_attempts))
    asyncio.run(
        worker.run(
            bootstrap_servers=bootstrap,
            dlq_topic=dlq_topic,
            target_topic=target_topic,
            parking_topic=parking_topic,
            group_id=group_id,
        )
    )


if __name__ == "__main__":
    main()

