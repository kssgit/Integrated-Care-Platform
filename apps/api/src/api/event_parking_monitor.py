from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Protocol

import httpx


class AlertNotifier(Protocol):
    async def notify(self, message: str) -> None: ...


class WebhookNotifier:
    def __init__(self, webhook_url: str, timeout_seconds: float = 5.0) -> None:
        self._webhook_url = webhook_url
        self._timeout_seconds = timeout_seconds

    async def notify(self, message: str) -> None:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            await client.post(self._webhook_url, json={"message": message})


@dataclass(frozen=True)
class ParkingAlertConfig:
    threshold: int = 10
    window_seconds: int = 300
    cooldown_seconds: int = 300


class ParkingAlertPolicy:
    def __init__(self, config: ParkingAlertConfig) -> None:
        self._config = config
        self._events: list[float] = []
        self._last_alert_at: float | None = None

    def add_event(self, now_seconds: float) -> bool:
        cutoff = now_seconds - self._config.window_seconds
        self._events = [value for value in self._events if value >= cutoff]
        self._events.append(now_seconds)
        if len(self._events) < self._config.threshold:
            return False
        if self._last_alert_at is None:
            self._last_alert_at = now_seconds
            return True
        if now_seconds - self._last_alert_at < self._config.cooldown_seconds:
            return False
        self._last_alert_at = now_seconds
        return True

    def event_count(self) -> int:
        return len(self._events)


class ApiEventParkingMonitorWorker:
    def __init__(
        self,
        policy: ParkingAlertPolicy,
        notifier: AlertNotifier,
    ) -> None:
        self._policy = policy
        self._notifier = notifier

    async def run(self, bootstrap_servers: str, topic: str, group_id: str) -> None:
        consumer = await self._create_consumer(bootstrap_servers, topic, group_id)
        try:
            async for _message in consumer:
                if self._policy.add_event(time.time()):
                    count = self._policy.event_count()
                    await self._notifier.notify(
                        f"Parking topic alert: {count} events in last window on topic={topic}"
                    )
        finally:
            await consumer.stop()

    async def _create_consumer(self, bootstrap_servers: str, topic: str, group_id: str):
        try:
            from aiokafka import AIOKafkaConsumer
        except ImportError as exc:
            raise RuntimeError("aiokafka is required for parking monitor worker") from exc
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=True,
            auto_offset_reset="latest",
        )
        await consumer.start()
        return consumer


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def main() -> None:
    bootstrap = _required_env("KAFKA_BOOTSTRAP_SERVERS")
    topic = os.getenv("API_EVENT_PARKING_TOPIC", "api-events-parking")
    group_id = os.getenv("API_EVENT_PARKING_MONITOR_GROUP", "api-event-parking-monitor")
    webhook_url = _required_env("PARKING_ALERT_WEBHOOK_URL")
    threshold = int(os.getenv("PARKING_ALERT_THRESHOLD", "10"))
    window_seconds = int(os.getenv("PARKING_ALERT_WINDOW_SECONDS", "300"))
    cooldown_seconds = int(os.getenv("PARKING_ALERT_COOLDOWN_SECONDS", "300"))

    worker = ApiEventParkingMonitorWorker(
        policy=ParkingAlertPolicy(
            config=ParkingAlertConfig(
                threshold=threshold,
                window_seconds=window_seconds,
                cooldown_seconds=cooldown_seconds,
            )
        ),
        notifier=WebhookNotifier(webhook_url=webhook_url),
    )
    asyncio.run(worker.run(bootstrap_servers=bootstrap, topic=topic, group_id=group_id))


if __name__ == "__main__":
    main()
