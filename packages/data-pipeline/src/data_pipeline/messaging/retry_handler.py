from __future__ import annotations

from dataclasses import replace
from typing import Awaitable, Callable

from data_pipeline.messaging.broker import MessageBroker
from data_pipeline.messaging.schema import EtlMessage
from data_pipeline.messaging.topics import ETL_ERRORS_TOPIC, ETL_RAW_EVENTS_TOPIC


class RetryHandler:
    def __init__(
        self,
        broker: MessageBroker,
        max_retries: int = 3,
        retry_delay_seconds: int = 60,
    ) -> None:
        self._broker = broker
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds

    async def handle_failure(
        self,
        message: EtlMessage,
        sleep_fn: Callable[[int], Awaitable[None]],
    ) -> str:
        if message.retry_count >= self._max_retries:
            await self._broker.publish(ETL_ERRORS_TOPIC, message)
            return ETL_ERRORS_TOPIC

        next_message = replace(message, retry_count=message.retry_count + 1)
        await sleep_fn(self._retry_delay_seconds)
        await self._broker.publish(ETL_RAW_EVENTS_TOPIC, next_message)
        return ETL_RAW_EVENTS_TOPIC
