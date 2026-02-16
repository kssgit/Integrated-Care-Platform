import builtins

import pytest

from devkit import kafka as kafka_mod
from devkit.kafka import AsyncKafkaProducerManager, create_consumer, create_producer, run_with_retry


@pytest.mark.asyncio
async def test_run_with_retry_eventually_succeeds() -> None:
    state = {"count": 0}

    async def flaky() -> int:
        state["count"] += 1
        if state["count"] < 3:
            raise ValueError("boom")
        return 7

    async def no_sleep(_: float) -> None:
        return None

    result = await run_with_retry(flaky, max_retries=3, base_delay_seconds=0.01, sleep_fn=no_sleep)
    assert result == 7


@pytest.mark.asyncio
async def test_kafka_import_error_messages(monkeypatch) -> None:
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "aiokafka":
            raise ImportError("blocked in test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="aiokafka is required for kafka consumer"):
        await create_consumer("t", "g", "localhost:9092")

    with pytest.raises(RuntimeError, match="aiokafka is required for kafka producer"):
        await create_producer("localhost:9092")


@pytest.mark.asyncio
async def test_kafka_producer_manager_reconnects(monkeypatch) -> None:
    class FakeProducer:
        def __init__(self, fail_once: bool) -> None:
            self.fail_once = fail_once

        async def send_and_wait(self, _topic: str, _payload: bytes) -> None:
            if self.fail_once:
                self.fail_once = False
                raise RuntimeError("send failed")

        async def stop(self) -> None:
            return None

    created: list[FakeProducer] = []

    async def fake_create_producer(_bootstrap: str):
        producer = FakeProducer(fail_once=(len(created) == 0))
        created.append(producer)
        return producer

    monkeypatch.setattr(kafka_mod, "create_producer", fake_create_producer)

    manager = AsyncKafkaProducerManager("localhost:9092")
    await manager.send_and_wait("topic-1", b"payload")
    assert len(created) >= 2
