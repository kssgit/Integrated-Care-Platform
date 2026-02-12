from __future__ import annotations

import json
from typing import Any

from data_pipeline.messaging.broker import MessageBroker
from data_pipeline.messaging.schema import EtlMessage


class KafkaMessageBroker(MessageBroker):
    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer = None

    async def publish(self, topic: str, message: EtlMessage) -> None:
        producer = await self._get_producer()
        payload = json.dumps(
            {
                "trace_id": message.trace_id,
                "provider": message.provider,
                "payload": message.payload,
                "timestamp": message.timestamp.isoformat(),
                "retry_count": message.retry_count,
            }
        ).encode("utf-8")
        await producer.send_and_wait(topic, payload)

    async def _get_producer(self) -> Any:
        if self._producer is not None:
            return self._producer
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError as exc:
            raise RuntimeError("aiokafka is required for kafka broker") from exc
        producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap_servers)
        await producer.start()
        self._producer = producer
        return producer
